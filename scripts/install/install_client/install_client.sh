#!/bin/bash

# 安装脚本：bash /www/server/jh-monitor/scripts/install/install_client/install_client.sh  install  http://192.168.7.73:10844

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

USERNAME="ansible_user"
SSH_DIR="/home/$USERNAME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"

# 确保 target_dir 和 download_Url 被定义
target_dir="/usr/local/btmonitoragent"
download_Url="http://example.com"  # 请替换为实际的下载地址

Command_Exists() {
    command -v "$@" >/dev/null 2>&1
}

Get_Pack_Manager(){
    if [ -f "/usr/bin/yum" ] && [ -d "/etc/yum.repos.d" ]; then
        PM="yum"
    elif [ -f "/usr/bin/apt-get" ] && [ -f "/usr/bin/dpkg" ]; then
        PM="apt-get"        
    else
        echo "不支持的包管理器"
        exit 1
    fi
}

Download_Agent(){
    version="1.0"
    file_name="btmonitoragent"
    agent_src="/tmp/btmonitoragent.zip"

    if [ -d "$target_dir" ]; then
        rm -rf "$target_dir"
    fi
    cd /tmp || exit

    if [ -n "$offline" ]; then
        if [[ "$offline" =~ ".zip" ]]; then
            if [[ ! -f "$offline" ]]; then
                echo "$offline 文件不存在请使用完整路径。例:/root/agent.zip"
                exit 1
            fi
            \cp "$offline" "$agent_src"
        else
            wget -O "$agent_src" "$download_Url/install/src/update.zip" -t 5 -T 10
        fi
    else
        wget -O "$agent_src" "$download_Url/install/src/update.zip" -t 5 -T 10
    fi

    tmp_size=$(du -b "$agent_src" | awk '{print $1}')
    if [ "$tmp_size" -lt 10703460 ]; then
        rm -f "$agent_src"
        echo -e "\033[31mERROR: 下载云监控被控端失败，请尝试以下解决方法：\033[0m"
        echo "1、请尝试重新安装！"
        echo "2、如无法连接到下载节点，请参考此教程指定节点：https://www.bt.cn/bbs/thread-87257-1-1.html"
        exit 1
    fi

    echo "正在解压云监控被控端..."
    if ! Command_Exists unzip; then
        echo -e "\033[31mERROR: unzip 命令不存在，尝试以下解决方法：\033[0m"
        echo -e "1、使用命令重新安装unzip。 \n   Debian/Ubuntu 系列: apt reinstall unzip \n   RedHat/CentOS 系列：yum reinstall unzip "
        echo -e "2、检查系统源是否可用？尝试更换可用的源参考教程：https://www.bt.cn/bbs/thread-58005-1-1.html "
        exit 1
    fi

    unzip -d "$target_dir" "$agent_src" > /dev/null 2>&1
    mkdir -p "$target_dir/config" "$target_dir/logs"

    rm -rf "$agent_src"

    if [ ! -f "$target_dir/BT-MonitorAgent" ]; then
        rm -rf "$target_dir"
        echo -e "\033[31mERROR: 解压云监控被控端失败，请尝试重新安装！\033[0m"
        exit 1
    else
        chmod -R 755 "$target_dir"
        chown -R root:root "$target_dir"
        chmod +x "$target_dir/BT-MonitorAgent"
        chmod -R +x "$target_dir/plugin"
    fi
}

Timezones_Check(){
    if [[ "$action" =~ "127.0.0.1" ]]; then
        echo "检测到地址是127.0.0.1,本机安装,跳过时区检测"
        return
    fi

    bind_conf=$(curl -s -k "$action/api/bind" | awk -F '/' '{print $6}' | awk -F '"' '{print $1}')
    list_timectl=$(timedatectl list-timezones | grep "$bind_conf")
    local_timectl=$(timedatectl | grep 'Time zone' | grep "$bind_conf")

    if [ -z "$bind_conf" ]; then 
        echo -e "\033[31m错误：无法获取主监控服务器的时区，请检查与主监控服务器连接是否正常！\033[0m"
        exit 1
    fi
    if [ -z "$local_timectl" ]; then
        echo ""
        echo "被控服务器时区与主监控服务器时区不一致，将自动设置成与主监控服务器一致的时区！"
        sleep 1
        timedatectl set-timezone "$list_timectl"
        if [ "$?" != "0" ]; then
            echo -e "\033[31m错误：时区设置错误，请手动将当前服务器时区设置与主监控服务器时区一致！\033[0m"
            echo -e "\033[31m错误：主监控服务器时区是$list_timectl \033[0m"
            exit 1
        fi
        echo "已将当前服务器时区设置为：$list_timectl"
        echo ""
    fi
}

Install_RPM_Pack(){
    yumPacks="wget curl unzip crontabs"
    yum install -y ${yumPacks}

    for yumPack in ${yumPacks}; do
        rpmPack=$(rpm -q ${yumPack})
        packCheck=$(echo "${rpmPack}" | grep not)
        if [ "${packCheck}" ]; then
            yum install ${yumPack} -y
        fi
    done
}

Install_Deb_Pack(){
    debPacks="wget curl unzip cron"
    apt-get install -y $debPacks

    for debPack in ${debPacks}; do
        dpkg -l ${debPack} 2>/dev/null | grep -q '^ii' || apt-get install -y ${debPack}
    done
}

Connent_Test(){
    # todo: 实现 Connexion Test
    exit 1
}

Set_Crontab(){
    crond_text='*/1 * * * * /bin/bash /usr/local/btmonitoragent/crontab_tasks/btm_agent_runfix.sh >> /usr/local/btmonitoragent/crontab_tasks/btm_agent_runfix.log 2>&1'

    if [ ! -f "${target_dir}/crontab_tasks/btm_agent_runfix.sh" ]; then
        mkdir -p "$target_dir/crontab_tasks"
        wget -O "$target_dir/crontab_tasks/btm_agent_runfix.sh" "${download_Url}/tools/btm_agent_runfix.sh" -t 5 -T 10
    fi

    echo -e "正在添加被控端守护任务...\c"
    if [ "$PM" = "yum" ]; then
        sed -i "/btm_agent_runfix/d" /var/spool/cron/root
        echo "$crond_text" >> "/var/spool/cron/root"
        systemctl restart crond
    else
        sed -i "/btm_agent_runfix/d" /var/spool/cron/crontabs/root
        echo "$crond_text" >> "/var/spool/cron/crontabs/root"
        systemctl restart cron
    fi
    echo -e "   \033[32mdone\033[0m"
}

Add_Ansible_User(){
    if id "$USERNAME" &>/dev/null; then
        echo "用户 $USERNAME 已经存在。"
    else
        useradd -m -s /bin/bash "$USERNAME"
        echo "用户 $USERNAME 创建成功。"
    fi
}

Setup_SSH_Config(){
    if [ ! -d "$SSH_DIR" ]; then
        mkdir -p "$SSH_DIR"
        echo ".ssh 目录创建成功。"
    fi

    chown "$USERNAME:$USERNAME" "$SSH_DIR"
    chmod 700 "$SSH_DIR"

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
    CLIENT_IP=$(hostname -I | awk '{print $1}')
    add_res=$(curl -s -X POST "$monitor_url/pub/add_host" -d "host_name=$CLIENT_IP" -d "ip=$CLIENT_IP")
    echo $add_res
    # 判断返回的json中status是否为true
    if [[ "$add_res" =~ "true" ]]; then
        echo "添加主机成功"
    else
        echo "添加主机失败"
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

    Get_Pack_Manager
    # if [ $PM = "yum" ]; then
    #     Install_RPM_Pack
    # else
    #     Install_Deb_Pack
    # fi

    # 安装客户端
    # Install_Monitor_Agent
    
    # 添加ansible用户
    Add_Ansible_User

    # 配置服务端访问权限
    Setup_SSH_Config

    # 通知服务端添加主机
    Add_Host_To_Monitor
    # Download_Agent
    # Set_Crontab
    # Timezones_Check
fi
