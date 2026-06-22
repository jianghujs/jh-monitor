#!/bin/bash
# migrate_filebeat_inputs.sh - 将旧版 filebeat 配置迁移到 inputs.d/ 结构
#
# 旧版问题:
#   - filebeat.yml 内联了所有 filebeat.inputs: 段
#   - 监控任务 inputs 放在 jh-monitor-task-inputs.d/ 目录
#   - 主机重装时 mv 覆盖 filebeat.yml 会丢掉任务 inputs 引用
#
# 迁移后:
#   - filebeat.yml 只保留框架配置（name, modules, output, processors...）
#   - filebeat.config.inputs 指向 /etc/filebeat/inputs.d/*.yml
#   - 主机 inputs 拆分为 inputs.d/host-{debian,pve}.yml
#   - 任务 inputs 从 jh-monitor-task-inputs.d/ 移到 inputs.d/
#
# 幂等：已迁移的机器重复执行不会重复操作。
#
# 用法:
#   bash migrate_filebeat_inputs.sh            # 迁移并重启 filebeat
#   bash migrate_filebeat_inputs.sh --no-restart  # 迁移但不重启

set -e

FILEBEAT_MAIN="/etc/filebeat/filebeat.yml"
INPUTS_DIR="/etc/filebeat/inputs.d"
LEGACY_TASK_DIR="/etc/filebeat/jh-monitor-task-inputs.d"

_SEP_LONG='========================================'
_SEP_SHORT='----------------------------------------'

_log()    { echo "[migrate-filebeat-inputs] $*"; }
_log_sep() { _log "$_SEP_LONG"; }
_log_start() { _log "☑️ $*"; }
_log_done()  { _log "☑️ $*"; }
_log_fail()  { _log "❌ $*"; }
_log_step()  { _log "|- $*"; }
_log_detail(){ _log "|--- $*"; }
_log_warn()  { _log "|--- ⚠ $*"; }

# ---------- Step 1: 迁移旧版任务 inputs 目录 ----------

migrate_legacy_task_dir() {
  [ -d "$LEGACY_TASK_DIR" ] || return 0

  _log_step "迁移旧版任务 inputs 目录" from="$LEGACY_TASK_DIR"
  local moved=0
  for f in "$LEGACY_TASK_DIR"/*.yml; do
    [ -f "$f" ] || continue
    local bname
    bname="$(basename "$f")"
    if [ -f "${INPUTS_DIR}/${bname}" ]; then
      _log_detail "跳过（目标已存在）" file="$bname"
    else
      mv "$f" "${INPUTS_DIR}/${bname}"
      _log_detail "已迁移" file="$bname"
      moved=$((moved + 1))
    fi
  done

  # 清理空旧目录
  if [ -z "$(ls -A "$LEGACY_TASK_DIR" 2>/dev/null)" ]; then
    rmdir "$LEGACY_TASK_DIR"
    _log_detail "已移除旧目录" path="$LEGACY_TASK_DIR"
  fi

  [ "$moved" -gt 0 ] && _log_detail "任务 inputs 迁移完成" count="$moved"

  # 修正旧 filebeat.yml 中追加段的路径
  if [ -f "$FILEBEAT_MAIN" ] && grep -q 'jh-monitor-task-inputs.d' "$FILEBEAT_MAIN"; then
    sed -i 's|/etc/filebeat/jh-monitor-task-inputs\.d/\*\.yml|/etc/filebeat/inputs.d/*.yml|g' "$FILEBEAT_MAIN"
    _log_detail "已修正 filebeat.yml 中 inputs 路径" old="jh-monitor-task-inputs.d" new="inputs.d"
  fi
}

# ---------- Step 2: 提取内联 filebeat.inputs 到 inputs.d/host-*.yml ----------
#
# 处理两种旧版场景:
#   A) 仅有 filebeat.inputs: （从未装过监控任务的主机）
#   B) 同时有 filebeat.inputs: 和 filebeat.config.inputs: （装过监控任务的主机，
#      旧版 monitor_task.sh 在末尾追加了 filebeat.config.inputs 段）
#
# 两种情况都需要提取内联 inputs 并从主配置中删除。
# 区别在于: 场景 B 已经有 filebeat.config.inputs 段，不需要再插入新的。

extract_inline_inputs() {
  [ -f "$FILEBEAT_MAIN" ] || return 0
  grep -q '^filebeat\.inputs:' "$FILEBEAT_MAIN" || return 0

  local host_type="debian"
  if [ -d /etc/pve ]; then
    host_type="pve"
  fi
  local host_input_file="${INPUTS_DIR}/host-${host_type}.yml"

  _log_step "提取内联 filebeat.inputs" type="$host_type"

  if [ -f "$host_input_file" ]; then
    _log_detail "inputs 文件已存在，跳过提取" file="host-${host_type}.yml"
  else
    python3 - "$FILEBEAT_MAIN" "$host_input_file" <<'PY_EXTRACT'
import sys

src_path, dst_path = sys.argv[1], sys.argv[2]
with open(src_path, "r") as f:
    lines = f.readlines()

start = None
for i, line in enumerate(lines):
    if line.rstrip() == "filebeat.inputs:":
        start = i
        break

if start is None:
    sys.exit(0)

end = len(lines)
for i in range(start + 1, len(lines)):
    line = lines[i]
    stripped = line.rstrip()
    if stripped == "":
        continue
    if not line.startswith((" ", "\t", "-", "#")) and ":" in line:
        end = i
        break

inputs_lines = lines[start + 1:end]
content = "".join(inputs_lines).rstrip() + "\n"
with open(dst_path, "w") as f:
    f.write(content)
PY_EXTRACT
    chmod 644 "$host_input_file"
    _log_detail "已提取到独立文件" file="host-${host_type}.yml"
  fi

  # 备份旧配置
  local backup="${FILEBEAT_MAIN}.legacy.$(date +%Y%m%d%H%M%S)"
  cp "$FILEBEAT_MAIN" "$backup"
  _log_detail "旧配置已备份" path="$backup"

  # 从主配置中删除 filebeat.inputs: 段
  _log_step "清理 filebeat.yml 内联 inputs 段"
  python3 - "$FILEBEAT_MAIN" <<'PY_CLEANUP'
import sys

path = sys.argv[1]
with open(path, "r") as f:
    lines = f.readlines()

start = None
for i, line in enumerate(lines):
    if line.rstrip() == "filebeat.inputs:":
        start = i
        break

if start is None:
    sys.exit(0)

end = len(lines)
for i in range(start + 1, len(lines)):
    line = lines[i]
    stripped = line.rstrip()
    if stripped == "":
        continue
    if not line.startswith((" ", "\t", "-", "#")) and ":" in line:
        end = i
        break

comment_start = start
while comment_start > 0:
    prev = lines[comment_start - 1].strip()
    if prev.startswith("#") or prev == "":
        comment_start -= 1
    else:
        break

tail = end
while tail < len(lines) and lines[tail].strip() == "":
    tail += 1

has_config_inputs = any(
    line.rstrip() == "filebeat.config.inputs:"
    for line in lines
)

if has_config_inputs:
    new_lines = lines[:comment_start] + lines[tail:]
else:
    config_inputs_block = (
        "\n"
        "# ============================== Filebeat inputs ===============================\n"
        "# All inputs are loaded from /etc/filebeat/inputs.d/*.yml, including:\n"
        "#   - host-{debian,pve}.yml  (host log inputs)\n"
        "#   - jh-monitor-task-*.yml  (monitor task inputs)\n"
        "\n"
        "filebeat.config.inputs:\n"
        "  enabled: true\n"
        "  path: /etc/filebeat/inputs.d/*.yml\n"
        "  reload.enabled: true\n"
        "  reload.period: 10s\n"
        "\n"
    )
    new_lines = lines[:comment_start] + [config_inputs_block] + lines[tail:]

with open(path, "w") as f:
    f.writelines(new_lines)
PY_CLEANUP

  if grep -q '^filebeat\.config\.inputs:' "$FILEBEAT_MAIN"; then
    _log_detail "内联 inputs 已删除" note="filebeat.config.inputs 已存在，保留"
  else
    _log_detail "内联 inputs 已删除，并添加 filebeat.config.inputs 引用"
  fi
}

# ---------- Step 3: 确保 filebeat.config.inputs 存在 ----------

ensure_config_inputs() {
  [ -f "$FILEBEAT_MAIN" ] || return 0
  grep -q 'inputs.d/\*\.yml' "$FILEBEAT_MAIN" && return 0

  _log_step "追加 filebeat.config.inputs 段"
  cat >> "$FILEBEAT_MAIN" <<'YAML'

# All inputs are loaded from /etc/filebeat/inputs.d/*.yml.
filebeat.config.inputs:
  enabled: true
  path: /etc/filebeat/inputs.d/*.yml
  reload.enabled: true
  reload.period: 10s
YAML
  _log_detail "已追加 filebeat.config.inputs 到 filebeat.yml"
}

# ---------- Step 4: 校验并重载 ----------

validate_and_reload() {
  if command -v filebeat >/dev/null 2>&1; then
    _log_step "校验 filebeat 配置"
    filebeat test config -c "$FILEBEAT_MAIN" >/dev/null 2>&1 || {
      _log_fail "filebeat 配置校验失败，请手动检查" path="$FILEBEAT_MAIN"
      return 1
    }
    _log_detail "配置校验通过"
  fi

  if [ "$NO_RESTART" = "1" ]; then
    _log_detail "跳过 filebeat 重载（--no-restart）"
    return 0
  fi

  _log_step "重载 filebeat"
  if command -v systemctl >/dev/null 2>&1; then
    systemctl reload filebeat >/dev/null 2>&1 || systemctl restart filebeat >/dev/null 2>&1 || true
  elif command -v service >/dev/null 2>&1; then
    service filebeat reload >/dev/null 2>&1 || service filebeat restart >/dev/null 2>&1 || true
  fi
  _log_detail "filebeat 已重载"
}

# ---------- Main ----------

NO_RESTART=0
if [ "${1:-}" = "--no-restart" ]; then
  NO_RESTART=1
fi

_log_sep
_log_start "开始 filebeat inputs 迁移"

# 前置检查
if [ ! -f "$FILEBEAT_MAIN" ]; then
  _log_warn "filebeat 主配置不存在，跳过迁移" path="$FILEBEAT_MAIN"
  exit 0
fi

mkdir -p "$INPUTS_DIR"

migrate_legacy_task_dir
extract_inline_inputs
ensure_config_inputs
validate_and_reload

_log_done "迁移完成"
_log_sep
_log "inputs.d/ 目录内容:"
ls -1 "$INPUTS_DIR"/*.yml 2>/dev/null | while read f; do _log "|--- $(basename "$f")"; done || true
