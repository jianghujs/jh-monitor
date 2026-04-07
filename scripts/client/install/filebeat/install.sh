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

LOCAL_CONFIG_PATH="$(cd "$(dirname "$0")" && pwd)/config/filebeat.${config_type}.yml"
if [ -f "$LOCAL_CONFIG_PATH" ]; then
  cp "$LOCAL_CONFIG_PATH" /tmp/filebeat.yml
else
  wget -O /tmp/filebeat.yml "${RAW_BASE}/scripts/client/install/filebeat/config/filebeat.${config_type}.yml"
fi
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
  sed -i "s/<hostId>/$HOST_ID/g" /etc/filebeat/filebeat.yml
  echo "已写入 filebeat host_id: $HOST_ID"
else
  echo "警告: 未获取到 host_id，filebeat 配置将保留占位符"
fi

validate_filebeat_config() {
  if command -v filebeat >/dev/null 2>&1; then
    filebeat test config -c /etc/filebeat/filebeat.yml >/tmp/filebeat_test.log 2>&1 || {
      cat /tmp/filebeat_test.log
      echo "错误: filebeat 配置校验失败"
      exit 1
    }
  fi
}

validate_filebeat_config

# 暂时不自动执行，因为太久了，手动执行一次就行
# echo "正在配置filebeat..."
# filebeat setup -e > /tmp/filebeat_setup.log 2>&1
# echo "filebeat配置完成✅"

echo "正在启动filebeat..."
service filebeat start
systemctl enable filebeat

echo "filebeat配置完成✅"
