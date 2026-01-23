# 安装filebeat
DEFAULT_RAW_BASE="https://raw.githubusercontent.com/jianghujs/jh-monitor/master"
CN_RAW_BASE="https://gitee.com/jianghujs/jh-monitor/raw/master"
RAW_BASE="$DEFAULT_RAW_BASE"
if [ "$1" == "cn" ]; then
  RAW_BASE="$CN_RAW_BASE"
fi

# wget -O /tmp/filebeat.deb "${RAW_BASE}/scripts/client/install/filebeat/filebeat.deb" && dpkg -i /tmp/filebeat.deb
FILEBEAT_VERSION="8.11.3"
FILEBEAT_DEB="filebeat-${FILEBEAT_VERSION}-amd64.deb"
FILEBEAT_URL="https://artifacts.elastic.co/downloads/beats/filebeat/${FILEBEAT_DEB}"
if [ "$1" == "cn" ]; then
  FILEBEAT_URL="https://mirrors.huaweicloud.com/filebeat/${FILEBEAT_VERSION}/${FILEBEAT_DEB}"
fi

wget -O /tmp/filebeat.deb "${FILEBEAT_URL}" && dpkg -i /tmp/filebeat.deb

# 配置filebeat
config_type="debian"
if [ -d /etc/pve ]; then
  config_type="pve"
fi

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

echo "正在配置filebeat..."
filebeat setup -e > /tmp/filebeat_setup.log 2>&1
echo "filebeat配置完成✅"

echo "正在启动filebeat..."
service filebeat start
systemctl enable filebeat

echo "filebeat配置完成✅"
