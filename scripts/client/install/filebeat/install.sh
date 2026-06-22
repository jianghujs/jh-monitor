# 安装filebeat
DEFAULT_RAW_BASE="https://raw.githubusercontent.com/jianghujs/jh-monitor/master"
CN_RAW_BASE="https://gitee.com/jianghujs/jh-monitor/raw/master"
RAW_BASE="$DEFAULT_RAW_BASE"
if [ "$1" == "cn" ]; then
  RAW_BASE="$CN_RAW_BASE"
fi
USERNAME="${REPORT_COLLECTOR_USERNAME:-ansible_user}"
DATA_DIR="${DATA_DIR:-/home/${USERNAME}/jh-monitor-data}"
HOST_ID_FILE="${JH_MONITOR_HOST_ID_FILE:-${DATA_DIR}/host_id}"

_SEP_LONG='========================================'
_SEP_SHORT='----------------------------------------'
_ICON_OK='☑️'
_ICON_FAIL='❌'

_log() { echo "[filebeat-install] $*"; }
_log_sep() { _log "$_SEP_LONG"; }
_log_sep_short() { _log "$_SEP_SHORT"; }
_log_start() { _log "$_ICON_OK $*"; }
_log_done() { _log "$_ICON_OK $*"; }
_log_fail() { _log "$_ICON_FAIL $*"; }
_log_step() { _log "|- $*"; }
_log_detail() { _log "|--- $*"; }

resolve_host_id() {
  if [ -n "$JH_MONITOR_HOST_ID" ]; then
    printf "%s" "$JH_MONITOR_HOST_ID"
    return 0
  fi

  if [ -s "$HOST_ID_FILE" ]; then
    tr -d '\r\n[:space:]' < "$HOST_ID_FILE"
    return 0
  fi

  if [ -s /etc/machine-id ]; then
    tr -d '\r\n[:space:]' < /etc/machine-id
    return 0
  fi

  hostname
  return 0
}

normalize_host_id_for_index() {
  local raw="$1"
  local normalized
  normalized="$(printf "%s" "$raw" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//; s/-+/-/g')"
  if [ -z "$normalized" ]; then
    normalized="host"
  fi
  printf "%s" "$normalized"
}

escape_sed_replacement() {
  printf "%s" "$1" | sed -e 's/[\/&]/\\&/g'
}

_log_sep
_log_start "开始安装 filebeat" version="8.11.3"

# wget -O /tmp/filebeat.deb "${RAW_BASE}/scripts/client/install/filebeat/filebeat.deb" && dpkg -i /tmp/filebeat.deb
FILEBEAT_VERSION="8.11.3"
FILEBEAT_DEB="filebeat-${FILEBEAT_VERSION}-amd64.deb"
FILEBEAT_URL="https://artifacts.elastic.co/downloads/beats/filebeat/${FILEBEAT_DEB}"
if [ "$1" == "cn" ]; then
  FILEBEAT_URL="https://mirrors.huaweicloud.com/filebeat/${FILEBEAT_VERSION}/${FILEBEAT_DEB}"
fi

INSTALLED_FILEBEAT_VERSION="$(dpkg-query -W -f='${Version}' filebeat 2>/dev/null || true)"
if echo "$INSTALLED_FILEBEAT_VERSION" | grep -q "^${FILEBEAT_VERSION}"; then
  _log_step "filebeat 已安装，跳过" version="$INSTALLED_FILEBEAT_VERSION"
else
  _log_step "下载并安装 filebeat deb" url="$FILEBEAT_URL"
  wget -O /tmp/filebeat.deb "${FILEBEAT_URL}" && dpkg -i /tmp/filebeat.deb
fi

# 配置filebeat
config_type="debian"
if [ -d /etc/pve ]; then
  config_type="pve"
fi

_log_step "下载主配置" type="$config_type" file="filebeat.${config_type}.yml"
wget -O /tmp/filebeat.yml "${RAW_BASE}/scripts/client/install/filebeat/config/filebeat.${config_type}.yml"
if [ ! -s /tmp/filebeat.yml ]; then
  _log_fail "下载主配置失败" type="$config_type"
  exit 1
fi
mv /tmp/filebeat.yml /etc/filebeat/filebeat.yml
chmod 644 /etc/filebeat/filebeat.yml
_log_detail "主配置已写入" path="/etc/filebeat/filebeat.yml"

if [ -z "$SERVER_IP" ]; then
  read -p "请输入ELK服务端IP: " SERVER_IP
  if [ -z "$SERVER_IP" ]; then
    _log_fail "未指定ELK服务端IP"
    exit 1
  fi
fi
_log_step "替换配置占位符" serverIp="$SERVER_IP"
sed -i "s/<serverIp>/$SERVER_IP/g" /etc/filebeat/filebeat.yml

HOST_ID="$(resolve_host_id)"
if [ -n "$HOST_ID" ]; then
  HOST_ID_INDEX="$(normalize_host_id_for_index "$HOST_ID")"
  ESCAPED_HOST_ID="$(escape_sed_replacement "$HOST_ID")"
  ESCAPED_HOST_ID_INDEX="$(escape_sed_replacement "$HOST_ID_INDEX")"
  sed -i "s/<hostId>/$ESCAPED_HOST_ID/g" /etc/filebeat/filebeat.yml
  sed -i "s/<hostIdIndex>/$ESCAPED_HOST_ID_INDEX/g" /etc/filebeat/filebeat.yml
  _log_detail "已写入 host_id" hostId="$HOST_ID" hostIdIndex="$HOST_ID_INDEX"
else
  _log_detail "未获取到 host_id，配置将保留占位符"
fi


# 下载主机 inputs 配置到 /etc/filebeat/inputs.d/
INPUTS_DIR="/etc/filebeat/inputs.d"
mkdir -p "$INPUTS_DIR"
HOST_INPUT_FILE="${INPUTS_DIR}/host-${config_type}.yml"
_log_step "下载主机 inputs 配置" type="$config_type" file="host-${config_type}.yml"
wget -O /tmp/host-inputs.yml "${RAW_BASE}/scripts/client/install/filebeat/config/inputs.d/host-${config_type}.yml"
if [ ! -s /tmp/host-inputs.yml ]; then
  _log_fail "下载主机 inputs 配置失败" type="$config_type"
  exit 1
fi
mv /tmp/host-inputs.yml "$HOST_INPUT_FILE"
chmod 644 "$HOST_INPUT_FILE"
if [ -n "$HOST_ID" ]; then
  sed -i "s/<hostId>/$ESCAPED_HOST_ID/g" "$HOST_INPUT_FILE"
  _log_detail "已写入 host inputs host_id" hostId="$HOST_ID"
fi
_log_detail "主机 inputs 配置完成" path="$HOST_INPUT_FILE"

validate_filebeat_config() {
  _log_step "校验 filebeat 配置"
  if command -v filebeat >/dev/null 2>&1; then
    _log_detail "执行 filebeat test config"
    filebeat test config -c /etc/filebeat/filebeat.yml >/tmp/filebeat_test.log 2>&1 || {
      cat /tmp/filebeat_test.log
      _log_fail "filebeat 配置校验失败"
      exit 1
    }
    _log_detail "配置校验通过"
  else
    _log_detail "未找到 filebeat 命令，跳过校验"
  fi
}

validate_filebeat_config

run_filebeat_setup() {
  local setup_log_file="/tmp/filebeat_setup.log"
  if ! command -v filebeat >/dev/null 2>&1; then
    _log_step "未找到 filebeat 命令，跳过 setup"
    return 0
  fi

  _log_step "执行 filebeat setup" log="$setup_log_file"
  : > "${setup_log_file}"
  if ! filebeat setup -e >"${setup_log_file}" 2>&1; then
    cat "${setup_log_file}"
    _log_fail "filebeat setup 失败" log="$setup_log_file"
    return 1
  fi
  _log_detail "filebeat setup 完成"
}

run_filebeat_setup || exit 1

_log_step "启动 filebeat 服务"
service filebeat restart
systemctl enable filebeat

_log_done "filebeat 配置完成"
_log_sep
