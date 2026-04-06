#!/bin/bash

set -e

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

ACTION="${1:-install}"
USERNAME="${REPORT_COLLECTOR_USERNAME:-ansible_user}"
RAW_BASE="${MONITOR_RAW_BASE:-https://raw.githubusercontent.com/jianghujs/jh-monitor/master}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLIENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
SCRIPT_HOME="/home/${USERNAME}/jh-monitor-scripts"
DATA_DIR="${SCRIPT_HOME}/data"
LOG_DIR="/home/${USERNAME}/jh-monitor-logs"
LOG_FILE="${LOG_DIR}/report-collector.log"
CRON_FILE="/etc/cron.d/jh-monitor-report-collector"
LOCK_FILE="/tmp/jh-monitor-report-collector.lock"
FILES_TO_DEPLOY="report_collector.py get_host_usage.py get_host_info.py"

log() {
  echo "[report-collector] $*"
}

fail() {
  echo "[report-collector] ERROR: $*" >&2
  exit 1
}

ensure_python() {
  if [ -z "$PYTHON_BIN" ]; then
    fail "python3 未安装，无法部署 report collector"
  fi
}

ensure_user() {
  if id "$USERNAME" >/dev/null 2>&1; then
    return 0
  fi
  useradd -m -s /bin/bash "$USERNAME"
}

prepare_dirs() {
  mkdir -p "$SCRIPT_HOME" "$DATA_DIR" "$LOG_DIR"
  touch "$LOG_FILE"
  chown -R "$USERNAME:$USERNAME" "$SCRIPT_HOME" "$LOG_DIR"
  chmod 755 "$SCRIPT_HOME" "$DATA_DIR" "$LOG_DIR"
  chmod 644 "$LOG_FILE"
}

fetch_or_copy() {
  local name="$1"
  local local_file="${CLIENT_DIR}/${name}"
  local target_file="${SCRIPT_HOME}/${name}"

  if ! wget -O "$target_file" "${RAW_BASE}/scripts/client/${name}"; then
    if [ -f "$local_file" ]; then
      cp "$local_file" "$target_file"
    else
      fail "下载 ${name} 失败"
    fi
  fi

  chmod 755 "$target_file"
  chown "$USERNAME:$USERNAME" "$target_file"
}

cleanup_legacy() {
  rm -f "$CRON_FILE"

  if crontab -l >/tmp/jh_monitor_root_cron 2>/dev/null; then
    grep -v 'jh-monitor-scripts/report_collector.py' /tmp/jh_monitor_root_cron >/tmp/jh_monitor_root_cron.new || true
    if ! cmp -s /tmp/jh_monitor_root_cron /tmp/jh_monitor_root_cron.new; then
      crontab /tmp/jh_monitor_root_cron.new
      log "已清理 root crontab 中遗留的 report collector 任务"
    fi
    rm -f /tmp/jh_monitor_root_cron /tmp/jh_monitor_root_cron.new
  fi
}

write_cron() {
  local collector_cmd="${PYTHON_BIN} ${SCRIPT_HOME}/report_collector.py --output-dir ${DATA_DIR}"
  if command -v flock >/dev/null 2>&1; then
    collector_cmd="$(command -v flock) -n ${LOCK_FILE} ${collector_cmd}"
  fi

  cat > "$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
*/5 * * * * root ${collector_cmd} >> ${LOG_FILE} 2>&1
CRON

  chmod 644 "$CRON_FILE"
  chown root:root "$CRON_FILE"
}

validate_cron() {
  [ -f "$CRON_FILE" ] || fail "cron 文件不存在: ${CRON_FILE}"
  grep -q 'report_collector.py' "$CRON_FILE" || fail "cron 文件未包含 report_collector.py"
}

run_once() {
  local output_path
  output_path="$(${PYTHON_BIN} ${SCRIPT_HOME}/report_collector.py --output-dir ${DATA_DIR})" || fail "首次执行 report collector 失败"
  [ -n "$output_path" ] || fail "report collector 未输出文件路径"
  [ -f "$output_path" ] || fail "report collector 输出文件不存在: ${output_path}"
  log "首次采集完成: ${output_path}"
}

main() {
  case "$ACTION" in
    install|update)
      ensure_python
      ensure_user
      prepare_dirs
      cleanup_legacy
      for file_name in $FILES_TO_DEPLOY; do
        fetch_or_copy "$file_name"
      done
      write_cron
      validate_cron
      run_once
      ;;
    uninstall)
      rm -f "$CRON_FILE"
      ;;
    *)
      fail "不支持的动作: ${ACTION}"
      ;;
  esac
}

main "$@"
