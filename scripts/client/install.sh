#!/bin/bash

# 安装脚本：bash /www/server/jh-monitor/scripts/client/install.sh install http://192.168.7.73:10844 [cn]

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

USERNAME="ansible_user"
SSH_DIR="/home/$USERNAME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"
DEFAULT_RAW_BASE="https://raw.githubusercontent.com/jianghujs/jh-monitor/master"
CN_RAW_BASE="https://gitee.com/jianghujs/jh-monitor/raw/master"

prompt()
{
  tip=$1
  local _resultvar=$2
  local default_choice=$3
  echo -ne "\033[1;32m?\033[0m \033[1m${tip}\033[0m"
  read choice
  choice=${choice:-$default_choice}
  eval $_resultvar="'$choice'"
}

show_error()
{
  tip=$1
  echo -e "\033[1;31m× ${tip}\033[0m"
}

check_command_exist() {
    command -v "$@" >/dev/null 2>&1
}

add_ansible_user(){
    if id "$USERNAME" &>/dev/null; then
        echo "用户 $USERNAME 已经存在。"
    else
        useradd -m -s /bin/bash "$USERNAME"
        echo "用户 $USERNAME 创建成功。"
    fi
}

config_ansible_user() {
    if ! command -v sudo >/dev/null 2>&1; then
        if command -v apt >/dev/null 2>&1; then
            echo "未检测到 sudo，开始安装..."
            apt update && apt install sudo -y
            echo "已安装 sudo"
        else
            echo "未检测到 sudo，且无 apt，跳过安装"
        fi
    fi
    echo "开始配置 $USERNAME 权限..."
    # 创建脚本执行目录
    mkdir -p /home/${USERNAME}/jh-monitor-scripts/
    chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/jh-monitor-scripts/
    echo "已配置脚本目录权限: /home/${USERNAME}/jh-monitor-scripts/"
    # 默认日志输出目录（避免写系统目录）
    mkdir -p /home/${USERNAME}/jh-monitor-logs/
    chown -R ${USERNAME}:${USERNAME} /home/${USERNAME}/jh-monitor-logs/
    echo "已配置日志目录权限: /home/${USERNAME}/jh-monitor-logs/"
    
    # 日志目录读写权限
    mkdir -p /www/server/log
    if command -v setfacl >/dev/null 2>&1; then
        setfacl -m u:${USERNAME}:rwX /www/server/log
        setfacl -d -m u:${USERNAME}:rwX /www/server/log
        echo "已设置 /www/server/log ACL 读写权限"
    else
        chown -R ${USERNAME}:${USERNAME} /www/server/log
        echo "已设置 /www/server/log 目录归属为 $USERNAME"
    fi

    # 面板目录读取权限
    if [ -d /www/server/jh-panel ]; then
        if command -v setfacl >/dev/null 2>&1; then
            setfacl -m u:${USERNAME}:rx /www/server/jh-panel
            setfacl -R -m u:${USERNAME}:rX /www/server/jh-panel/class /www/server/jh-panel/data /www/server/jh-panel/logs 2>/dev/null
            setfacl -d -m u:${USERNAME}:rX /www/server/jh-panel/data /www/server/jh-panel/logs 2>/dev/null
            echo "已设置 /www/server/jh-panel 相关目录 ACL 读取权限"
        else
            echo "未找到 setfacl，跳过 /www/server/jh-panel ACL 配置"
        fi
    else
        echo "未找到 /www/server/jh-panel，跳过面板目录权限配置"
    fi

    # jh 命令执行权限
    if [ -f /www/server/jh-panel/jh ]; then
        if command -v setfacl >/dev/null 2>&1; then
            setfacl -m u:${USERNAME}:rx /www/server/jh-panel/jh
        else
            chmod a+rx /www/server/jh-panel/jh
        fi
        echo "已设置 /www/server/jh-panel/jh 执行权限"
    fi
    if [ -f /usr/bin/jh ]; then
        if command -v setfacl >/dev/null 2>&1; then
            setfacl -m u:${USERNAME}:rx /usr/bin/jh
        else
            chmod a+rx /usr/bin/jh
        fi
        echo "已设置 /usr/bin/jh 执行权限"
    fi

    # 报告日志写入权限
    touch /var/log/jhpanel_report.log
    if command -v setfacl >/dev/null 2>&1; then
        setfacl -m u:${USERNAME}:rw /var/log/jhpanel_report.log
        echo "已设置 /var/log/jhpanel_report.log ACL 读写权限"
    else
        chown ${USERNAME}:${USERNAME} /var/log/jhpanel_report.log
        echo "已设置 /var/log/jhpanel_report.log 归属为 $USERNAME"
    fi

    # 只读命令 sudo 权限
    mkdir -p /etc/sudoers.d/
    rm -f /etc/sudoers.d/ansible_user
    cat > /etc/sudoers.d/ansible_user <<EOF
Cmnd_Alias JH_MONITOR_READ = /sbin/iptables -L, /sbin/iptables -L *, /usr/sbin/iptables -L, /usr/sbin/iptables -L *, /usr/sbin/smartctl --scan, /usr/sbin/smartctl -a /dev/*, /usr/bin/smartctl --scan, /usr/bin/smartctl -a /dev/*, /usr/bin/sensors, /usr/bin/sensors *, /usr/bin/ipmitool sensor, /usr/bin/ipmitool chassis status
${USERNAME} ALL=(ALL) NOPASSWD: JH_MONITOR_READ
EOF
    chmod 0440 /etc/sudoers.d/ansible_user
    if command -v visudo >/dev/null 2>&1; then
        if ! visudo -cf /etc/sudoers.d/ansible_user >/dev/null 2>&1; then
            rm -f /etc/sudoers.d/ansible_user
            show_error "sudoers 校验失败，已移除 /etc/sudoers.d/ansible_user"
            exit 1
        fi
    fi
    echo "已配置只读命令 sudo 权限"
    
}

config_run_env() {
    local script_dir
    script_dir="$(cd "$(dirname "$0")" && pwd)"
    local local_script="${script_dir}/install/ensure_run_env.sh"
    if [ -f "$local_script" ]; then
        if ! bash "$local_script" "$net_env_cn"; then
            show_error "Python 环境初始化失败"
            exit 1
        fi
        return
    fi

    if ! wget -O /tmp/install_ensure_run_env.sh "${RAW_BASE}/scripts/client/install/ensure_run_env.sh"; then
        show_error "下载 Python 环境初始化脚本失败"
        exit 1
    fi
    if ! bash /tmp/install_ensure_run_env.sh "$net_env_cn"; then
        show_error "Python 环境初始化失败"
        exit 1
    fi
}

add_server_ssh_cert(){
    if [ ! -d "$SSH_DIR" ]; then
        mkdir -p "$SSH_DIR"
        echo ".ssh 目录创建成功。"
    fi

    chown "$USERNAME:$USERNAME" "$SSH_DIR"
    chmod 700 "$SSH_DIR"

    echo "正在从服务端 $monitor_url/pub/get_pub_key 获取公钥..."

    PUBLIC_KEY_DATA=$(curl -s "$monitor_url/pub/get_pub_key")
    echo $PUBLIC_KEY_DATA

    PUBLIC_KEY_DATA_STATUS=$(echo $PUBLIC_KEY_DATA | awk -F 'status":' '{print $2}' | awk -F ',' '{print $1}'  | sed 's/ //g')
    if [ "$PUBLIC_KEY_DATA_STATUS" == "true" ]; then
        PUBLIC_KEY=$(echo $PUBLIC_KEY_DATA | awk -F 'data":' '{print $2}' | awk -F '"' '{print $2}')
        
        if ! grep -Fxq "$PUBLIC_KEY" $AUTHORIZED_KEYS; then
          echo $PUBLIC_KEY >> $AUTHORIZED_KEYS
          chown "$USERNAME:$USERNAME" "$AUTHORIZED_KEYS"
          chmod 600 "$AUTHORIZED_KEYS"
          echo "公钥添加成功。"
        fi

    else
        echo "获取公钥失败"
        exit 1
    fi
}

config_filebeat() {
    if check_command_exist filebeat && [ -f /etc/filebeat/filebeat.yml ]; then
        echo "已安装 filebeat 且存在配置文件，跳过安装。"
        return 0
    fi
    # 安装filebeat
    wget -O /tmp/install_filebeat.sh "${RAW_BASE}/scripts/client/install/filebeat/install.sh" && bash /tmp/install_filebeat.sh "$net_env_cn"
}

notify_server_add_host(){
    
    default_client_ip=$(hostname -I | awk '{print $1}')
    prompt "请输入服务端连接到当前机器的IP（默认为：${default_client_ip}）：" client_ip $default_client_ip
    if [ -z "$client_ip" ]; then
      show_error "错误:未指定本地IP地址"
      exit 1
    fi

    sys_default_ssh_port=22
    default_client_ssh_port=$(grep -E "^Port [0-9]+" /etc/ssh/sshd_config | awk '{print $2}')
    if [ -z "$default_client_ssh_port" ]; then
        default_client_ssh_port=$sys_default_ssh_port
    fi
    prompt "请输入服务端连接到当前机器的SSH端口（默认为：${default_client_ssh_port}）：" client_ssh_port $default_client_ssh_port
    if [ -z "$client_ssh_port" ]; then
      show_error "错误:未指定本地SSH端口"
      exit 1
    fi

    # 获取客户端名称
    default_client_name=$(hostname -s)
    prompt "请输入客户端名称（默认为：${default_client_name}）：" client_name $default_client_name
    if [ -z "$client_name" ]; then
      show_error "错误:未指定客户端名称"
      exit 1
    fi

    add_res=$(curl -s -X POST "$monitor_url/pub/add_host" -d "host_name=$client_name" -d "ip=$client_ip" -d "port=$client_ssh_port")
    echo $add_res
    # 判断返回的json中status是否为true
    if [[ "$add_res" =~ "true" ]]; then
        echo "添加主机成功"
    else
        add_res_msg=$(echo $add_res | awk -F 'msg": "' '{print $2}' | awk -F '"' '{print $1}')
        echo -e "添加主机失败，$add_res_msg"
        exit 1
    fi
}

action="${1}"
monitor_url="${2}"
net_env_cn="${3}"
RAW_BASE="$DEFAULT_RAW_BASE"
if [ "$net_env_cn" == "cn" ]; then
  RAW_BASE="$CN_RAW_BASE"
fi

if [ "$action" == "uninstall" ]; then
    echo "卸载逻辑待实现"
elif [ "$action" == "install" ]; then
    SERVER_IP=$(echo "${monitor_url}" | cut -d'/' -f3 | cut -d':' -f1)
    SERVER_PORT=$(echo "${monitor_url}" | awk -F ":" '{print $3}')

    export SERVER_IP
    export SERVER_PORT

    # 添加ansible用户
    add_ansible_user

    # 配置ansible用户权限
    config_ansible_user

    # 配置客户端python环境
    config_run_env

    # 配置服务端访问权限
    add_server_ssh_cert

    # 配置filebeat
    config_filebeat

    # 通知服务端添加主机
    notify_server_add_host
elif [ "$action" == "set_user_permission" ]; then
    # 仅初始化ansible_user权限相关设置
    add_ansible_user
    config_ansible_user
fi
