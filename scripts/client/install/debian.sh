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
DATA_HOME="/home/${USERNAME}/jh-monitor-data"
LOG_DIR="/home/${USERNAME}/jh-monitor-logs"
DATA_DIR="${DATA_HOME}"
LOG_FILE="${LOG_DIR}/report-collector.log"
CRON_FILE="/etc/cron.d/jh-monitor-report-collector"
LOCK_FILE="/tmp/jh-monitor-report-collector.lock"
FILES_TO_DEPLOY="report_collector.py get_debian_system_status.py get_pve_system_status.py get_host_usage.py get_host_info.py get_pve_hardware_report.py"
CRON_HELPER_NAME="report_collector_cron.sh"

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
  mkdir -p "$SCRIPT_HOME" "$DATA_HOME" "$LOG_DIR"
  touch "$LOG_FILE"
  chown -R "$USERNAME:$USERNAME" "$SCRIPT_HOME" "$DATA_HOME" "$LOG_DIR"
  chmod 755 "$SCRIPT_HOME" "$DATA_HOME" "$LOG_DIR"
  chmod 644 "$LOG_FILE"
}

fetch_or_copy() {
  local name="$1"
  local local_file="${CLIENT_DIR}/${name}"
  local target_file="${SCRIPT_HOME}/${name}"

  if [ -f "$local_file" ]; then
    cp "$local_file" "$target_file"
  elif ! wget -O "$target_file" "${RAW_BASE}/scripts/client/${name}"; then
    fail "下载 ${name} 失败"
  fi

  chmod 755 "$target_file"
  chown "$USERNAME:$USERNAME" "$target_file"
}

run_cron_installer() {
  local cron_action="${1:-update}"
  local cron_script="/tmp/${CRON_HELPER_NAME}"
  local local_script="${SCRIPT_DIR}/${CRON_HELPER_NAME}"

  if [ -f "$local_script" ]; then
    cron_script="$local_script"
  elif ! wget -O "$cron_script" "${RAW_BASE}/scripts/client/install/${CRON_HELPER_NAME}"; then
    fail "下载 ${CRON_HELPER_NAME} 失败"
  fi

  REPORT_COLLECTOR_USERNAME="$USERNAME" \
  REPORT_COLLECTOR_OUTPUT_DIR="$DATA_DIR" \
  PYTHON_BIN="$PYTHON_BIN" \
  SCRIPT_HOME="$SCRIPT_HOME" \
  DATA_DIR="$DATA_DIR" \
  LOG_DIR="$LOG_DIR" \
  LOG_FILE="$LOG_FILE" \
  CRON_FILE="$CRON_FILE" \
  LOCK_FILE="$LOCK_FILE" \
  bash "$cron_script" "$cron_action"
}

main() {
  case "$ACTION" in
    install|update)
      ensure_python
      ensure_user
      prepare_dirs
      for file_name in $FILES_TO_DEPLOY; do
        fetch_or_copy "$file_name"
      done
      run_cron_installer update
      ;;
    uninstall)
      run_cron_installer uninstall
      ;;
    *)
      fail "不支持的动作: ${ACTION}"
      ;;
  esac
}

main "$@"
