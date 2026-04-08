#!/bin/bash

set -e

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

ACTION="${1:-update}"
USERNAME="${REPORT_COLLECTOR_USERNAME:-ansible_user}"
PYTHON_BIN="${PYTHON_BIN:-$(command -v python3 || true)}"
SCRIPT_HOME="${SCRIPT_HOME:-/home/${USERNAME}/jh-monitor-scripts}"
DATA_HOME="${DATA_HOME:-/home/${USERNAME}/jh-monitor-data}"
LOG_DIR="${LOG_DIR:-/home/${USERNAME}/jh-monitor-logs}"
DATA_DIR="${DATA_DIR:-${DATA_HOME}}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/report-collector.log}"
CRON_FILE="${CRON_FILE:-/etc/cron.d/jh-monitor-report-collector}"
LOCK_FILE="${LOCK_FILE:-/tmp/jh-monitor-report-collector.lock}"

log() {
  echo "[report-collector-cron] $*" >&2
}

fail() {
  echo "[report-collector-cron] ERROR: $*" >&2
  exit 1
}

build_collector_command() {
  local collector_exec="${PYTHON_BIN} ${SCRIPT_HOME}/report_collector.py --output-dir ${DATA_DIR}"
  log "build collector command, python=${PYTHON_BIN} script_home=${SCRIPT_HOME} data_dir=${DATA_DIR}"
  if command -v flock >/dev/null 2>&1; then
    collector_exec="$(command -v flock) -n ${LOCK_FILE} ${collector_exec}"
    log "flock enabled, lock_file=${LOCK_FILE}"
  else
    log "flock not found, run without lock"
  fi
  log "collector command ready: ${collector_exec}"
  printf '%s\n' "${collector_exec}"
}

cleanup_legacy() {
  log "cleanup legacy cron config: ${CRON_FILE}"
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
  local collector_cmd
  collector_cmd="$(build_collector_command)"
  log "write cron file: ${CRON_FILE}"
  mkdir -p "$LOG_DIR"
  touch "$LOG_FILE"
  log "log file ready: ${LOG_FILE}"

  cat > "$CRON_FILE" <<CRON
SHELL=/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin
*/5 * * * * root ${collector_cmd} >> ${LOG_FILE} 2>&1
CRON

  chmod 644 "$CRON_FILE"
  chown root:root "$CRON_FILE"
  log "cron file written successfully"
}

validate_cron() {
  log "validate cron config"
  [ -n "$PYTHON_BIN" ] || fail "python3 未安装，无法生成 report collector 定时任务"
  [ -f "$CRON_FILE" ] || fail "cron 文件不存在: ${CRON_FILE}"
  grep -q 'report_collector.py' "$CRON_FILE" || fail "cron 文件未包含 report_collector.py"
  log "cron validation passed"
}

run_once() {
  local output_path
  log "run collector once for validation"
  output_path="$(build_collector_command)" || fail "生成 report collector 执行命令失败"
  log "execute command: ${output_path}"
  output_path="$(eval "$output_path")" || fail "首次执行 report collector 失败"
  [ -n "$output_path" ] || fail "report collector 未输出文件路径"
  [ -f "$output_path" ] || fail "report collector 输出文件不存在: ${output_path}"
  log "首次采集完成: ${output_path}"
}

main() {
  log "start action=${ACTION} user=${USERNAME} script_home=${SCRIPT_HOME} data_dir=${DATA_DIR} log_dir=${LOG_DIR}"
  case "$ACTION" in
    install|update)
      cleanup_legacy
      write_cron
      validate_cron
      run_once
      ;;
    uninstall)
      cleanup_legacy
      ;;
    *)
      fail "不支持的动作: ${ACTION}"
      ;;
  esac
}

main "$@"
