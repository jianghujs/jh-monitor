#!/bin/bash

PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

USERNAME="ansible"
SSH_DIR="/home/$USERNAME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"

is64bit=$(getconf LONG_BIT)
if [ "${is64bit}" != '64' ];then
    echo -e "\033[31m 抱歉, 堡塔云监控系统不支持32位系统, 请使用64位系统! \033[0m"
    exit 1
fi

S390X_CHECK=$(uname -a|grep s390x)
if [ "${S390X_CHECK}" ];then
    echo -e "\033[31m 抱歉, 堡塔云监控系统不支持s390x架构进行安装，请使用x86_64服务器架构 \033[0m"
    exit 1
fi

is_aarch64=$(uname -a|grep aarch64)
if [ "${is_aarch64}" != "" ];then
    echo -e "\033[31m 抱歉, 堡塔云监控系统暂不支持aarch64架构进行安装，请使用x86_64服务器架构 \033[0m"
    exit 1
fi

Command_Exists() {
    command -v "$@" >/dev/null 2>&1
}

Get_Pack_Manager(){
	if [ -f "/usr/bin/yum" ] && [ -d "/etc/yum.repos.d" ]; then
		PM="yum"
	elif [ -f "/usr/bin/apt-get" ] && [ -f "/usr/bin/dpkg" ]; then
		PM="apt-get"		
	fi
}

# 下载BT_Monitor_Agent
# 云端文件名格式：
# version变量定义版本信息
# file_name变量定义文件名称
# 例子：btmonitoragent-1.0.0.zip
Download_Agent(){
    version="1.0"
    file_name="btmonitoragent"
    agent_src="btmonitoragent.zip"

    if [ -d "$target_dir" ]; then
        rm -rf $target_dir
    fi
    cd /tmp
    #wget -O $agent_src $download_Url/install/src/$file_name-$version.zip -t 5 -T 10
    #wget -O $agent_src $download_Url/install/src/update.zip -t 5 -T 10

	if [ ! -z "$offline" ]; then
		# 例如：bash offline_btmonitoragent.sh 主控地址 /root/agent.zip
		if [[ "$offline" =~ ".zip" ]]; then
			#"指定版本"
            if [[ ! -f "$offline" ]]; then
                echo "$offline 文件不存在请使用完整路径。例:/root/agent.zip"
                exit 1
            fi

            \cp $offline $agent_src

		else
			wget -O $agent_src $download_Url/install/src/update.zip -t 5 -T 10
		fi
	else
    	wget -O $agent_src $download_Url/install/src/update.zip -t 5 -T 10
	fi

    
    tmp_size=$(du -b $agent_src|awk '{print $1}')
    if [ $tmp_size -lt 10703460 ];then
        rm -f $agent_src
        #echo -e "\033[31mERROR: 下载云监控被控端失败，请尝试重新安装！\033[0m"
        echo -e "\033[31mERROR: 下载云监控被控端失败，请尝试以下解决方法：\033[0m"
        echo "1、请尝试重新安装！"
        echo "2、如无法连接到下载节点，请参考此教程指定节点：https://www.bt.cn/bbs/thread-87257-1-1.html"
        exit 1
    fi

    echo "正在解压云监控被控端..."
    if [ ! -f "/usr/bin/unzip" ];then
        echo -e "\033[31mERROR: /usr/bin/unzip 命令不存在，尝试以下解决方法：\033[0m"
        echo -e "1、使用命令重新安装unzip。 \n   Debian/Ubuntu 系列: apt reinstall unzip \n   RedHat/CentOS 系列：yum reinstall unzip "
        echo -e "2、检查系统源是否可用？尝试更换可用的源参考教程：https://www.bt.cn/bbs/thread-58005-1-1.html "
        exit 1
    fi

    #unzip -d /usr/local/ $agent_src > /dev/null 2>&1
    unzip -d /usr/local/btmonitoragent $agent_src > /dev/null 2>&1
    mkdir $target_dir/{config,logs}

    rm -rf $agent_src

    if [ ! -f "$target_dir/BT-MonitorAgent" ];then
        rm -rf $target_dir
        echo -e "\033[31mERROR: 解压云监控被控端失败，请尝试重新安装！\033[0m"
        exit 1
    else
        chmod -R 755 $target_dir
        chown -R root.root $target_dir
        chmod +x $target_dir/BT-MonitorAgent
        chmod -R +x $target_dir/plugin
    fi
}

Add_Ansible_User(){
    # 检查用户是否存在
    if id "$USERNAME" &>/dev/null; then
        echo "用户 $USERNAME 已经存在。"
    else
        # 创建用户并设置 home 目录及默认 shell
        useradd -m -s /bin/bash "$USERNAME"
        echo "用户 $USERNAME 创建成功。"
    fi
}

Setup_SSH_Config(){
    # 创建 .ssh 目录（如果不存在）
    if [ ! -d "$SSH_DIR" ]; then
        mkdir -p "$SSH_DIR"
        echo ".ssh 目录创建成功。"
    fi

    # 设置 .ssh 目录权限
    chown "$USERNAME:$USERNAME" "$SSH_DIR"
    chmod 700 "$SSH_DIR"

    # curl 获取公钥 PUBLIC_KEY
    PUBLIC_KEY=$(curl -s $monitor_url/host/get_pub_key)

    # 添加公钥到 authorized_keys 文件
    if [ ! -f "$AUTHORIZED_KEYS" ] || ! grep -q "$PUBLIC_KEY" "$AUTHORIZED_KEYS"; then
        echo "$PUBLIC_KEY" >> "$AUTHORIZED_KEYS"
        echo "公钥添加成功。"
    fi
}

Add_Host_To_Monitor(){
    # todo 现在拿到的只有本机ip
    CLIENT_IP=$(hostname -I | awk '{print $1}')
    add_res=$(curl -s -X POST $monitor_url/host/add -d "host_name=$CLIENT_IP" -d "ip=$CLIENT_IP")
    if [[ "$add_res" =~ "success" ]];then
        echo "添加主机成功"
    else
        echo "添加主机失败"
        exit 1
    fi
}


Timezones_Check(){
    if [[ "$action" =~ "127.0.0.1" ]];then
        echo "检测到地址是127.0.0.1,本机安装,跳过时区检测"
        return
    fi
    # bind_conf="curl -s -k https://192.168.99.100:806/api/bind|grep -E -o '\+[0-9]{4}'"
    bind_conf=`curl -s -k $action/api/bind|awk -F '/' '{print $6}'|awk -F '\"' '{print $1}'`
    list_timectl=`timedatectl list-timezones | grep $bind_conf`
    local_timectl=`timedatectl | grep 'Time zone' | grep $bind_conf`
    if [ -z "$bind_conf" ]; then 
        echo -e "\033[31m错误：无法获取主监控服务器的时区，请检查与主监控服务器连接是否正常！\033[0m"
        exit 1
    fi
    if [ -z "$local_timectl" ]; then
        echo ""
        echo "被控服务器时区与主监控服务器时区不一致，将自动设置成与主监控服务器一致的时区！"
        sleep 1
        timedatectl set-timezone $list_timectl
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

	for yumPack in ${yumPacks}
	do
		rpmPack=$(rpm -q ${yumPack})
		packCheck=$(echo ${rpmPack}|grep not)
		if [ "${packCheck}" ]; then
			yum install ${yumPack} -y
		fi
	done
}

Install_Deb_Pack(){
    debPacks="wget curl unzip cron";
	apt-get install -y $debPacks --force-yes

	for debPack in ${debPacks}
	do
		packCheck=$(dpkg -l ${debPack})
		if [ "$?" -ne "0" ] ;then
			apt-get install -y $debPack
		fi
	done
}

Connent_Test(){
    # todo
    # for ((i=1; i<=10; i++));
    # do
    #     http_code=$(curl --connect-time 10 --retry 5 -s -o /dev/null -k -w %{http_code} ${action})
    #     if [ "$http_code" == "000" ]; then
    #         echo "本机连接云监控主控端的状态码是: ${http_code}"
    #         echo "---------------------------------------------------"
    #         echo -e "\033[31mError-错误: 本机与云监控主控端通信失败!\033[0m"
    #         echo ""
    #         # echo "请检查本机与云监控服务端的${panelPort}端口是否正常通信!"
    #         # echo "---------------------------------------------------"
    #         echo "尝试以下解决方法："
    #         echo "1、检查主控服务是否正常启动，检查命令：btm status"
    #         # if [[ ${panelPort} == "" ]]; then
    #         #     echo "2、检查主控端口 ${panelPort} 防火墙/安全组是否是否已经放行"
    #         # else
    #         #     port1=`echo ${action}|awk -F ":" '{print $3}'`
    #         #     echo "2、检查主控端口 ${port1} 防火墙/安全组是否是否已经放行"
    #         # fi
    #         echo "2、检查主控端口 ${SERVER_PORT} 防火墙/安全组是否是否已经放行"
    #         echo "3、检查主控端地址是否正确：${action}"
    #         echo "4、尝试执行命令检是否可以连接到主控端：curl -kv ${action}"
    #         echo "---------------------------------------------------"
    #         exit 1
    #     fi
    # done
}


Set_Crontab(){
    crond_text='*/1 * * * * /bin/bash /usr/local/btmonitoragent/crontab_tasks/btm_agent_runfix.sh >> /usr/local/btmonitoragent/crontab_tasks/btm_agent_runfix.log 2>&1'
    #[ ! -d "$target_dir/crontab_tasks" ] && mkdir -p $target_dir/crontab_tasks
    #wget -O $target_dir/crontab_tasks/btm_agent_runfix.sh ${download_Url}/tools/btm_agent_runfix.sh -t 5 -T 10

    if [ ! -f "${target_dir}/crontab_tasks/btm_agent_runfix.sh" ] ; then
        mkdir -p $target_dir/crontab_tasks
        wget -O $target_dir/crontab_tasks/btm_agent_runfix.sh ${download_Url}/tools/btm_agent_runfix.sh -t 5 -T 10
    fi

    echo -e "正在添加被控端守护任务...\c"
    if [ $PM = "yum" ]; then
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


action="${1}"
monitor_url="${2}"
if [ "$action" == "uninstall" ];then
    # todo
elif [[ "$action" == "install" ]];then
    SERVER_IP=$( echo ${monitor_url}| cut -d'/' -f3 | cut -d':' -f1)
    SERVER_PORT=$(echo ${monitor_url}|awk -F ":" '{print $3}')
    
    # 连通性测试
    Connent_Test
    Get_Pack_Manager
    # if [ $PM = "yum" ]; then
    #     Install_RPM_Pack
    # else
    #     Install_Deb_Pack
    # fi
    Install_Monitor_Agent
    Add_Ansible_User
    Setup_SSH_Config
    Add_Host_To_Monitor
fi