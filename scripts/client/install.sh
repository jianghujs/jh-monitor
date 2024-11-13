#!/bin/bash

# 安装脚本：bash /www/server/jh-monitor/scripts/client/install.sh  install  http://192.168.7.73:10844

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

USERNAME="ansible_user"
SSH_DIR="/home/$USERNAME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"

# 确保 target_dir 和 download_Url 被定义
target_dir="/usr/local/btmonitoragent"
download_Url="http://example.com"  # 请替换为实际的下载地址


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

Command_Exists() {
    command -v "$@" >/dev/null 2>&1
}

Add_Ansible_User(){
    if id "$USERNAME" &>/dev/null; then
        echo "用户 $USERNAME 已经存在。"
    else
        useradd -m -s /bin/bash "$USERNAME"
        echo "用户 $USERNAME 创建成功。"
    fi
}

Config_Ansible_User() {
    # 创建脚本执行目录
    mkdir -p /home/ansible_user/jh-monitor-scripts/
    chown -R ansible_user:ansible_user /home/ansible_user/jh-monitor-scripts/
    
    # 防火墙读取权限
    mkdir -p /etc/sudoers.d/
    echo "ansible_user ALL=(ALL) NOPASSWD: /sbin/iptables -L" >> /etc/sudoers.d/ansible_user
    chmod 0440 /etc/sudoers.d/ansible_user
    
}

Setup_SSH_Config(){
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

Add_Host_To_Monitor(){
    
    default_client_ip=$(hostname -I | awk '{print $1}')
    prompt "请输入服务端连接到当前机器的IP（默认为：${default_client_ip}）：" client_ip $default_client_ip
    if [ -z "$client_ip" ]; then
      show_error "错误:未指定本地IP地址"
      exit 1
    fi

    default_client_ssh_port=port=$(grep -E "^#?Port\s+[0-9]+" "$file" | sed -E 's/#?Port\s+([0-9]+)/\1/' | head -n 1)
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

    add_res=$(curl -s -X POST "$monitor_url/pub/add_host" -d "host_name=$client_name" -d "ip=$client_ip")
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

if [ "$action" == "uninstall" ]; then
    echo "卸载逻辑待实现"
elif [ "$action" == "install" ]; then
    SERVER_IP=$(echo "${monitor_url}" | cut -d'/' -f3 | cut -d':' -f1)
    SERVER_PORT=$(echo "${monitor_url}" | awk -F ":" '{print $3}')

    # 添加ansible用户
    Add_Ansible_User

    # 配置ansible用户权限
    Config_Ansible_User

    # 配置服务端访问权限
    Setup_SSH_Config

    # 通知服务端添加主机
    Add_Host_To_Monitor
fi
