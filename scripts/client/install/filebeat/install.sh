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

# wget -O /tmp/filebeat.deb "${RAW_BASE}/scripts/client/install/filebeat/filebeat.deb" && dpkg -i /tmp/filebeat.deb
FILEBEAT_VERSION="8.11.3"
FILEBEAT_DEB="filebeat-${FILEBEAT_VERSION}-amd64.deb"
FILEBEAT_URL="https://artifacts.elastic.co/downloads/beats/filebeat/${FILEBEAT_DEB}"
if [ "$1" == "cn" ]; then
  FILEBEAT_URL="https://mirrors.huaweicloud.com/filebeat/${FILEBEAT_VERSION}/${FILEBEAT_DEB}"
fi

INSTALLED_FILEBEAT_VERSION="$(dpkg-query -W -f='${Version}' filebeat 2>/dev/null || true)"
if echo "$INSTALLED_FILEBEAT_VERSION" | grep -q "^${FILEBEAT_VERSION}"; then
  echo "filebeat ${INSTALLED_FILEBEAT_VERSION} 已安装，跳过重复安装"
else
  wget -O /tmp/filebeat.deb "${FILEBEAT_URL}" && dpkg -i /tmp/filebeat.deb
fi

# 配置filebeat
config_type="debian"
if [ -d /etc/pve ]; then
  config_type="pve"
fi

echo "开始下载最新 filebeat 配置: filebeat.${config_type}.yml"
wget -O /tmp/filebeat.yml "${RAW_BASE}/scripts/client/install/filebeat/config/filebeat.${config_type}.yml"
if [ ! -s /tmp/filebeat.yml ]; then
  echo "错误: 下载 filebeat 配置失败 (${config_type})"
  exit 1
fi
mv /tmp/filebeat.yml /etc/filebeat/filebeat.yml
chmod 644 /etc/filebeat/filebeat.yml


if [ -z "$SERVER_IP" ]; then
  read -p "请输入ELK服务端IP: " SERVER_IP
  if [ -z "$SERVER_IP" ]; then
    echo "错误:未指定ELK服务端IP"
    exit 1
  fi
fi
# 替换文件中的IP为当前服务器的IP
sed -i "s/<serverIp>/$SERVER_IP/g" /etc/filebeat/filebeat.yml

HOST_ID="$(resolve_host_id)"
if [ -n "$HOST_ID" ]; then
  HOST_ID_INDEX="$(normalize_host_id_for_index "$HOST_ID")"
  ESCAPED_HOST_ID="$(escape_sed_replacement "$HOST_ID")"
  ESCAPED_HOST_ID_INDEX="$(escape_sed_replacement "$HOST_ID_INDEX")"
  sed -i "s/<hostId>/$ESCAPED_HOST_ID/g" /etc/filebeat/filebeat.yml
  sed -i "s/<hostIdIndex>/$ESCAPED_HOST_ID_INDEX/g" /etc/filebeat/filebeat.yml
  echo "已写入 filebeat host_id: $HOST_ID"
  echo "已写入 filebeat host_id_index: $HOST_ID_INDEX"
else
  echo "警告: 未获取到 host_id，filebeat 配置将保留占位符"
fi

validate_filebeat_config() {
  echo "开始校验 filebeat 配置: /etc/filebeat/filebeat.yml"
  if command -v filebeat >/dev/null 2>&1; then
    echo "检测到 filebeat 命令，执行: filebeat test config -c /etc/filebeat/filebeat.yml"
    filebeat test config -c /etc/filebeat/filebeat.yml >/tmp/filebeat_test.log 2>&1 || {
      echo "filebeat 配置校验失败，输出如下:"
      cat /tmp/filebeat_test.log
      echo "错误: filebeat 配置校验失败"
      exit 1
    }
    echo "filebeat 配置校验通过"
  else
    echo "警告: 未找到 filebeat 命令，跳过配置校验"
  fi
}

validate_filebeat_config

run_filebeat_setup() {
  local setup_log_file="/tmp/filebeat_setup.log"
  if ! command -v filebeat >/dev/null 2>&1; then
    echo "警告: 未找到 filebeat 命令，跳过 setup"
    return 0
  fi

  echo "开始执行 filebeat setup，日志写入: ${setup_log_file}"
  echo "执行命令: filebeat setup -e"
  : > "${setup_log_file}"
  if ! filebeat setup -e >"${setup_log_file}" 2>&1; then
    echo "filebeat setup 失败，输出如下:"
    cat "${setup_log_file}"
    echo "错误: filebeat setup 失败，请检查日志: ${setup_log_file}"
    return 1
  fi
  echo "filebeat setup完成✅"
}

run_filebeat_setup || exit 1

echo "正在启动filebeat..."
service filebeat restart
systemctl enable filebeat

echo "filebeat配置完成✅"
