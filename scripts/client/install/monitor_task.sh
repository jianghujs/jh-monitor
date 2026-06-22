#!/bin/bash

set -e

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

ACTION="${1:-install}"
shift || true

USERNAME="${MONITOR_TASK_USERNAME:-ansible_user}"
RAW_BASE="${MONITOR_RAW_BASE:-https://raw.githubusercontent.com/jianghujs/jh-monitor/master}"
SCRIPT_HOME="/home/${USERNAME}/jh-monitor-scripts"
TASK_HOME="/home/${USERNAME}/jh-monitor-tasks"
BIN_DIR="${SCRIPT_HOME}/bin"
LIB_DIR="${SCRIPT_HOME}/lib"
TASK_INPUT_DIR="/etc/filebeat/inputs.d"
FILEBEAT_MAIN="/etc/filebeat/filebeat.yml"
# 日志路径由服务器统一管理：每个任务一个子目录
LOG_ROOT="/var/log/jh-monitor/tasks"
SERVER_URL=""
TASK_ID=""
TASK_NAME=""
HOST_ID=""
LOG_PATH=""
RUN_USER=""

# ---- 日志函数 (Jianghu 运维风格) ----
_SEP_LONG='========================================'
_SEP_SHORT='----------------------------------------'

log() {
  echo "[monitor-task] $*" >&2
}

info() {
  echo "[monitor-task] $*"
}

info_sep()    { info "$_SEP_LONG"; }
info_sep_short() { info "$_SEP_SHORT"; }
info_start() { info "☑️ $*"; }
info_done()  { info "☑️ $*"; }
info_fail()  { info "❌ $*"; }
info_step()  { info "|- $*"; }
info_detail(){ info "|--- $*"; }

fail() {
  log "❌ $*"
  report_status "failed" "$*" || true
  exit 1
}

urlencode() {
  local value="$1"
  if command -v python3 >/dev/null 2>&1; then
    python3 -c 'import sys, urllib.parse; print(urllib.parse.quote_plus(sys.argv[1]))' "$value"
  else
    printf '%s' "$value" | sed 's/ /+/g'
  fi
}

json_quote() {
  local value="$1"
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$value"
}

yaml_quote() {
  local value="$1"
  python3 -c 'import json, sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$value"
}

post_form() {
  local url="$1"
  shift
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -X POST "$url" "$@"
  elif command -v wget >/dev/null 2>&1; then
    local body=""
    local arg key val
    for arg in "$@"; do
      case "$arg" in
        --data-urlencode)
          continue
          ;;
        *)
          if [ -z "$body" ]; then
            body="$arg"
          else
            body="${body}&${arg}"
          fi
          ;;
      esac
    done
    wget -qO- --post-data="$body" "$url"
  else
    log "curl/wget not found, skip callback: $url"
  fi
}

report_status() {
  local status="$1"
  local msg="$2"
  [ -n "$SERVER_URL" ] || return 0
  [ -n "$TASK_ID" ] || return 0
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -X POST "${SERVER_URL%/}/pub/update_monitor_task_install_status" \
      --data-urlencode "task_id=${TASK_ID}" \
      --data-urlencode "install_status=${status}" \
      --data-urlencode "install_msg=${msg}" >/dev/null || true
  else
    local body="task_id=$(urlencode "$TASK_ID")&install_status=$(urlencode "$status")&install_msg=$(urlencode "$msg")"
    post_form "${SERVER_URL%/}/pub/update_monitor_task_install_status" "$body" >/dev/null || true
  fi
}

parse_args() {
  while [ $# -gt 0 ]; do
    case "$1" in
      --server-url) SERVER_URL="$2"; shift 2 ;;
      --task-id) TASK_ID="$2"; shift 2 ;;
      --task-name) TASK_NAME="$2"; shift 2 ;;
      --host-id) HOST_ID="$2"; shift 2 ;;
      --run-user) RUN_USER="$2"; shift 2 ;;
      *) fail "unknown argument: $1" ;;
    esac
  done
}

load_host_id() {
  if [ -n "$HOST_ID" ]; then
    return
  fi
  local host_id_file="/home/${USERNAME}/jh-monitor-data/host_id"
  if [ -f "$host_id_file" ]; then
    HOST_ID="$(cat "$host_id_file" | tr -d '[:space:]')"
  fi
}

validate_args() {
  [ -n "$SERVER_URL" ] || fail "--server-url is required"
  [ -n "$TASK_ID" ] || fail "--task-id is required"
  [ -n "$TASK_NAME" ] || fail "--task-name is required"
  load_host_id
  [ -n "$HOST_ID" ] || fail "--host-id is required or host_id file is missing"
  # 日志路径由 task_id 派生，统一管理在 LOG_ROOT 下的任务子目录
  LOG_PATH="${LOG_ROOT%/}/${TASK_ID}/task.json.log"
  info_step "参数确认" server="${SERVER_URL}" taskId="${TASK_ID}" taskName="${TASK_NAME}" hostId="${HOST_ID}"
  info_detail "任务日志路径" logPath="${LOG_PATH}"
}

register_task() {
  info_step "向云监控注册任务" taskId="${TASK_ID}" taskName="${TASK_NAME}"
  if command -v curl >/dev/null 2>&1; then
    curl -fsS -X POST "${SERVER_URL%/}/pub/register_monitor_task" \
      --data-urlencode "task_id=${TASK_ID}" \
      --data-urlencode "task_name=${TASK_NAME}" \
      --data-urlencode "host_id=${HOST_ID}" >/tmp/jh_monitor_task_register.json || fail "register task failed"
  else
    fail "curl is required for task registration"
  fi
  if ! grep -q '"status": true\|"status":true' /tmp/jh_monitor_task_register.json; then
    cat /tmp/jh_monitor_task_register.json >&2 || true
    fail "monitor server rejected task registration"
  fi
  info_detail "注册成功"
}

ensure_paths() {
  local log_dir
  log_dir="$(dirname "$LOG_PATH")"
  info_step "创建目录" dirs="${log_dir} ${BIN_DIR} ${LIB_DIR} ${TASK_HOME} ${TASK_INPUT_DIR}"
  mkdir -p "$log_dir" "$BIN_DIR" "$LIB_DIR" "$TASK_HOME" "$TASK_INPUT_DIR"
  info_detail "创建任务日志文件" path="${LOG_PATH}"
  touch "$LOG_PATH"
  if [ -n "$RUN_USER" ] && id "$RUN_USER" >/dev/null 2>&1; then
    chown -R "$RUN_USER:$RUN_USER" "$log_dir" || true
  info_detail "已授权日志目录" user="${RUN_USER}"
  fi
  if id "$USERNAME" >/dev/null 2>&1; then
    chown -R "$USERNAME:$USERNAME" "$SCRIPT_HOME" "$TASK_HOME" || true
  fi
}

write_task_config() {
  info_step "写入本地任务配置" path="${TASK_HOME}/${TASK_ID}.json"
  cat > "${TASK_HOME}/${TASK_ID}.json" <<JSON
{
  "task_id": $(json_quote "$TASK_ID"),
  "task_name": $(json_quote "$TASK_NAME"),
  "host_id": $(json_quote "$HOST_ID"),
  "log_path": $(json_quote "$LOG_PATH")
}
JSON
}

write_logger() {
  info_step "安装日志写入命令" cmd="jh-monitor-task-log"
  info_detail "脚本路径" path="${LIB_DIR}/jh_monitor_task.py"
  info_detail "命令路径" path="${BIN_DIR}/jh-monitor-task-log"
  cat > "${LIB_DIR}/jh_monitor_task.py" <<'PY'
#!/usr/bin/env python3
# coding: utf-8

import argparse
import datetime
import json
import os
import sys

TASK_HOME = os.environ.get('JH_MONITOR_TASK_HOME', '/home/ansible_user/jh-monitor-tasks')
DEFAULT_MSG = {
    'success': '成功',
    'warning': '告警',
    'error': '异常',
}


def load_task(task_id):
    path = os.path.join(TASK_HOME, task_id + '.json')
    with open(path, 'r') as fp:
        return json.load(fp)


def main():
    parser = argparse.ArgumentParser(description='Write jh-monitor task log event')
    parser.add_argument('--task-id', required=True)
    parser.add_argument('--status', default='success', choices=['success', 'warning', 'error'])
    parser.add_argument('--msg', default='')
    parser.add_argument('--run-at', default='')
    args = parser.parse_args()

    task = load_task(args.task_id)
    log_path = task.get('log_path')
    if not log_path:
        raise SystemExit('log_path missing in task config')
    run_at = args.run_at or datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    event = {
        'task_id': args.task_id,
        'status': args.status,
        'msg': args.msg or DEFAULT_MSG.get(args.status, args.status),
        'run_at': run_at,
        'collector_source': 'jh-monitor-task-log',
    }
    parent = os.path.dirname(log_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent)
    with open(log_path, 'a') as fp:
        fp.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')


if __name__ == '__main__':
    main()
PY
  chmod 755 "${LIB_DIR}/jh_monitor_task.py"

  cat > "${BIN_DIR}/jh-monitor-task-log" <<'SH'
#!/bin/bash
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
if [ -z "$PYTHON_BIN" ]; then
  echo "python3 not found" >&2
  exit 1
fi
SCRIPT_HOME="${JH_MONITOR_SCRIPT_HOME:-/home/ansible_user/jh-monitor-scripts}"
exec "$PYTHON_BIN" "${SCRIPT_HOME}/lib/jh_monitor_task.py" "$@"
SH
  chmod 755 "${BIN_DIR}/jh-monitor-task-log"
  ln -sf "${BIN_DIR}/jh-monitor-task-log" /usr/local/bin/jh-monitor-task-log
  info_detail "已创建软链" link="/usr/local/bin/jh-monitor-task-log" target="${BIN_DIR}/jh-monitor-task-log"
}

ensure_filebeat_include() {
  [ -f "$FILEBEAT_MAIN" ] || fail "filebeat main config not found: ${FILEBEAT_MAIN}"
  mkdir -p "$TASK_INPUT_DIR"

  # 调用独立迁移脚本处理旧版配置（幂等，已迁移时自动跳过）
  local migrate_script
  migrate_script="$(dirname "$0")/migrate_filebeat_inputs.sh"
  if [ ! -x "$migrate_script" ]; then
    local tmp_migrate_script="/tmp/migrate_filebeat_inputs.sh"
    info_step "下载 filebeat 迁移脚本" script="migrate_filebeat_inputs.sh"
    if wget -O "$tmp_migrate_script" "${RAW_BASE}/scripts/client/install/migrate_filebeat_inputs.sh"; then
      chmod 755 "$tmp_migrate_script"
      migrate_script="$tmp_migrate_script"
    else
      rm -f "$tmp_migrate_script"
      info "⚠ 下载迁移脚本失败，将使用兜底逻辑" url="${RAW_BASE}/scripts/client/install/migrate_filebeat_inputs.sh"
    fi
  fi
  if [ -x "$migrate_script" ]; then
    bash "$migrate_script" --no-restart
  else
    # 兜底：如果迁移脚本不存在，只做最基本的检查
    if grep -q 'inputs.d/\*.yml' "$FILEBEAT_MAIN"; then
      info_detail "filebeat 已启用 inputs.d，无需重复添加"
      return
    fi
    info "⚠ 迁移脚本不存在，正在补丁式追加 include 配置" path="${FILEBEAT_MAIN}"
    cat >> "$FILEBEAT_MAIN" <<'YAML'

# All inputs are loaded from /etc/filebeat/inputs.d/*.yml.
filebeat.config.inputs:
  enabled: true
  path: /etc/filebeat/inputs.d/*.yml
  reload.enabled: true
  reload.period: 10s
YAML
  fi
}

ensure_filebeat_task_output() {
  [ -f "$FILEBEAT_MAIN" ] || fail "filebeat main config not found: ${FILEBEAT_MAIN}"
  if grep -q 'host-monitor-task-event' "$FILEBEAT_MAIN"; then
    info_detail "filebeat 已包含任务日志索引路由" index="host-monitor-task-event"
    return 0
  fi

  info_step "修补 filebeat 任务日志索引路由" index="host-monitor-task-event"
  local backup="${FILEBEAT_MAIN}.task-event.$(date +%Y%m%d%H%M%S)"
  cp "$FILEBEAT_MAIN" "$backup"
  python3 - "$FILEBEAT_MAIN" <<'PY_PATCH_OUTPUT'
import sys

path = sys.argv[1]
with open(path, 'r') as fp:
    lines = fp.readlines()

route = [
    '    - index: "host-monitor-task-event"\n',
    '      when.equals:\n',
    '        log_index: "host-monitor-task-event"\n',
]

output_idx = None
for i, line in enumerate(lines):
    if line.rstrip() == 'output.elasticsearch:':
        output_idx = i
        break

if output_idx is None:
    raise SystemExit('output.elasticsearch not found')

indices_idx = None
for i in range(output_idx + 1, len(lines)):
    line = lines[i]
    if line.strip() == '':
        continue
    if not line.startswith((' ', '\t')) and ':' in line:
        break
    if line.strip() == 'indices:':
        indices_idx = i
        break

if indices_idx is not None:
    insert_at = indices_idx + 1
    lines[insert_at:insert_at] = route
else:
    insert_at = output_idx + 1
    lines[insert_at:insert_at] = ['  indices:\n'] + route

with open(path, 'w') as fp:
    fp.writelines(lines)
PY_PATCH_OUTPUT
  info_detail "已备份旧 filebeat 配置" path="$backup"
}

write_filebeat_input() {
  command -v filebeat >/dev/null 2>&1 || fail "filebeat command not found"
  mkdir -p "$TASK_INPUT_DIR"
  local input_file="${TASK_INPUT_DIR}/jh-monitor-task-${TASK_ID}.yml"
  info_step "写入 filebeat 采集配置" path="${input_file}"
  info_detail "采集日志" logPath="${LOG_PATH}"
  info_detail "目标索引" index="host-monitor-task-event"
  local log_path_yaml task_id_yaml task_name_yaml host_id_yaml
  log_path_yaml="$(yaml_quote "$LOG_PATH")"
  task_id_yaml="$(yaml_quote "$TASK_ID")"
  task_name_yaml="$(yaml_quote "$TASK_NAME")"
  host_id_yaml="$(yaml_quote "$HOST_ID")"
  cat > "$input_file" <<YAML
- type: log
  enabled: true
  paths:
    - ${log_path_yaml}
  json.keys_under_root: true
  json.add_error_key: true
  json.overwrite_keys: true
  fields:
    log_index: "host-monitor-task-event"
    task_id: ${task_id_yaml}
    task_name: ${task_name_yaml}
    host_id: ${host_id_yaml}
    log_path: ${log_path_yaml}
  fields_under_root: true
YAML
  chmod 644 "$input_file"
  ensure_filebeat_include
  ensure_filebeat_task_output
}

validate_and_reload_filebeat() {
  info_step "校验 filebeat 配置"
  filebeat test config -c "$FILEBEAT_MAIN" >/tmp/jh_monitor_task_filebeat_test.log 2>&1 || {
    cat /tmp/jh_monitor_task_filebeat_test.log >&2 || true
    fail "filebeat config validation failed"
  }
  info_detail "配置校验通过"
  info_step "重载 filebeat"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl reload filebeat >/dev/null 2>&1 || systemctl restart filebeat >/dev/null 2>&1 || true
  else
    service filebeat reload >/dev/null 2>&1 || service filebeat restart >/dev/null 2>&1 || true
  fi
  info_detail "filebeat 已重载"
}

install_task() {
  info_sep
  info_start "开始安装监控任务" taskId="${TASK_ID}" taskName="${TASK_NAME}" hostId="${HOST_ID}"
  echo ""
  validate_args
  echo ""
  register_task
  echo ""
  ensure_paths
  echo ""
  write_task_config
  echo ""
  write_logger
  echo ""
  write_filebeat_input
  echo ""
  validate_and_reload_filebeat
  echo ""
  report_status "installed" "安装成功"
  info_done "安装完成" taskId="${TASK_ID}" taskName="${TASK_NAME}" logPath="${LOG_PATH}"
  info ""
  info "在你的业务脚本中，执行完成后调用以下命令写入任务结果："
  info "  jh-monitor-task-log --task-id \"${TASK_ID}\" --status success --msg \"执行成功\""
  info "状态可选: success(成功) / warning(告警) / error(异常)"
  info_sep
}

case "$ACTION" in
  install|update)
    parse_args "$@"
    install_task
    ;;
  *)
    fail "unsupported action: ${ACTION}"
    ;;
esac
