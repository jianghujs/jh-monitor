#!/bin/bash
# chkconfig: 2345 55 25
# description: JH Cloud Service

### BEGIN INIT INFO
# Provides:          Jianghu
# Required-Start:    $all
# Required-Stop:     $all
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: starts jh-monitor
# Description:       starts the jh-monitor service
### END INIT INFO


PATH=/usr/local/bin:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export LANG=en_US.UTF-8

jhm_path=/www/server/jh-monitor
PATH=$PATH:$jhm_path/bin


if [ -f $jhm_path/bin/activate ];then
    source $jhm_path/bin/activate
fi

ssl_param=''
if [ -f /www/server/jh-monitor/data/ssl.pl ];then
    ssl_param=' --keyfile /www/server/jh-monitor/ssl/private.pem --certfile /www/server/jh-monitor/ssl/cert.pem '
fi

jh_start_panel()
{
    isStart=`ps -ef|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param ' |grep -v grep|awk '{print $2}'`;
    if [ "$isStart" == '' ];then
        echo -e "starting jh-monitor... \c"
        cd $jhm_path &&  gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param ;
        port=$(cat ${jhm_path}/data/port.pl)
        isStart=""
        while [[ "$isStart" == "" ]];
        do
            echo -e ".\c"
            sleep 0.5
            isStart=$(lsof -n -P -i:$port|grep LISTEN|grep -v grep|awk '{print $2}'|xargs)
            let n+=1
            if [ $n -gt 15 ];then
                break;
            fi
        done
        if [ "$isStart" == '' ];then
            echo -e "\033[31mfailed\033[0m"
            echo '------------------------------------------------------'
            tail -n 20 ${jhm_path}/logs/error.log
            echo '------------------------------------------------------'
            echo -e "\033[31mError: jh-monitor service startup failed.\033[0m"
            return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo "starting jh-monitor... jh(pid $(echo $isStart)) already running"
    fi
}


jh_start_task()
{
    isStart=$(ps aux |grep '/www/server/jh-monitor/task.py'|grep -v grep|awk '{print $2}')
    if [ "$isStart" == '' ];then
        echo -e "starting jh-monitor-tasks... \c"
        cd $jhm_path && python3 /www/server/jh-monitor/task.py >> ${jhm_path}/logs/task.log 2>&1 &
        sleep 0.3
        isStart=$(ps aux |grep '/www/server/jh-monitor/task.py'|grep -v grep|awk '{print $2}')
        if [ "$isStart" == '' ];then
            echo -e "\033[31mfailed\033[0m"
            echo '------------------------------------------------------'
            tail -n 20 $jhm_path/logs/task.log
            echo '------------------------------------------------------'
            echo -e "\033[31mError: jh-monitor-tasks service startup failed.\033[0m"
            return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo "starting jh-monitor-tasks... jh-monitor-tasks (pid $(echo $isStart)) already running"
    fi
}

jh_start()
{
    jh_start_task
	jh_start_panel
}

# /www/server/jh-monitor/tmp/panelTask.pl && service jh restart_task
jh_stop_task()
{
    if [ -f $jhm_path/tmp/panelTask.pl ];then
        echo -e "\033[32mthe task is running and cannot be stopped\033[0m"
        exit 0
    fi

    echo -e "stopping jh-monitor-tasks... \c";
    pids=$(ps aux | grep '/www/server/jh-monitor/task.py'|grep -v grep|awk '{print $2}')
    arr=($pids)
    for p in ${arr[@]}
    do
            kill -9 $p
    done
    echo -e "\033[32mdone\033[0m"
}

jh_stop_panel()
{
    echo -e "stopping jh-monitor... \c";
    arr=`ps aux|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app'|grep -v grep|awk '{print $2}'`;
    for p in ${arr[@]}
    do
        kill -9 $p &>/dev/null
    done
    
    pidfile=${jhm_path}/logs/jh.pid
    if [ -f $pidfile ];then
        rm -f $pidfile
    fi
    echo -e "\033[32mdone\033[0m"
}

jh_stop()
{
    jh_stop_task
    jh_stop_panel
}

jh_status()
{
    isStart=$(ps aux|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}');
    if [ "$isStart" != '' ];then
        echo -e "\033[32mjh (pid $(echo $isStart)) already running\033[0m"
    else
        echo -e "\033[31mjh not running\033[0m"
    fi
    
    isStart=$(ps aux |grep '/www/server/jh-monitor/task.py'|grep -v grep|awk '{print $2}')
    if [ "$isStart" != '' ];then
        echo -e "\033[32mjh-task (pid $isStart) already running\033[0m"
    else
        echo -e "\033[31mjh-task not running\033[0m"
    fi
}


jh_reload()
{
	isStart=$(ps aux|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}');
    
    if [ "$isStart" != '' ];then
    	echo -e "reload jh... \c";
	    arr=`ps aux|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}'`;
		for p in ${arr[@]}
        do
                kill -9 $p
        done
        cd $jhm_path && gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param 
        isStart=`ps aux|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app $ssl_param '|grep -v grep|awk '{print $2}'`;
        if [ "$isStart" == '' ];then
            echo -e "\033[31mfailed\033[0m"
            echo '------------------------------------------------------'
            tail -n 20 $jhm_path/logs/error.log
            echo '------------------------------------------------------'
            echo -e "\033[31mError: jh service startup failed.\033[0m"
            return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo -e "\033[31mjh not running\033[0m"
        jh_start
    fi
}

jh_close(){
    echo 'True' > $jhm_path/data/close.pl
}

jh_open()
{
    if [ -f $jhm_path/data/close.pl ];then
        rm -rf $jhm_path/data/close.pl
    fi
}

jh_unbind_domain()
{
    if [ -f $jhm_path/data/bind_domain.pl ];then
        rm -rf $jhm_path/data/bind_domain.pl
    fi
}

error_logs()
{
	tail -n 100 $jhm_path/logs/error.log
}

jh_update()
{
    cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
    if [ ! -z "$cn" ];then
        curl -fsSL https://cdn.jsdelivr.net/gh/jianghujs/jh-monitor@latest/scripts/update.sh | bash
    else
        curl -fsSL https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/update.sh | bash
    fi
}

jh_update_dev()
{
    cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
    if [ ! -z "$cn" ];then
        curl -fsSL https://gitee.com/jianghujs/jh-monitor/raw/dev/scripts/update_dev.sh | bash
    else
        curl -fsSL https://raw.githubusercontent.com/jianghujs/jh-monitor/dev/scripts/update_dev.sh | bash
    fi
    cd /www/server/jh-monitor
}

jh_install_app()
{
    bash $jhm_path/scripts/quick/app.sh
}

jh_close_admin_path(){
    if [ -f $jhm_path/data/admin_path.pl ]; then
        rm -rf $jhm_path/data/admin_path.pl
    fi
}

jh_force_kill()
{
    PLIST=`ps -ef|grep 'gunicorn -c /www/server/jh-monitor/setting.py app:app' |grep -v grep|awk '{print $2}'`
    for i in $PLIST
    do
        kill -9 $i
    done

    pids=`ps -ef|grep /www/server/jh-monitor/task.py | grep -v grep |awk '{print $2}'`
    arr=($pids)
    for p in ${arr[@]}
    do
        kill -9 $p
    done
}

jh_debug(){
    jh_stop
    jh_force_kill

    port=7200    
    if [ -f $jhm_path/data/port.pl ];then
        port=$(cat $jhm_path/data/port.pl)
    fi

    if [ -d /www/server/jh-monitor ];then
        cd /www/server/jh-monitor
    fi
    gunicorn -b :$port -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1  app:app $ssl_param --log-level "debug"  --capture-output;
}


jh_os_tool(){
  bash /www/server/jh-monitor/scripts/os_tool/index.sh vm "" "true"
}

# 获取运行命令的目录
export RUN_DIR=$(pwd)

case "$1" in
    'start') jh_start;;
    'stop') jh_stop;;
    'reload') jh_reload;;
    'restart') 
        jh_stop
        jh_force_kill
        jh_start;;
    'restart_panel')
        jh_stop_panel
        jh_start_panel;;
    'restart_task')
        jh_stop_task
        jh_start_task;;
    'status') jh_status;;
    'logs') error_logs;;
    'close') jh_close;;
    'open') jh_open;;
    'update') jh_update;;
    'update_dev') jh_update_dev;;
    'install_app') jh_install_app;;
    'close_admin_path') jh_close_admin_path;;
    'unbind_domain') jh_unbind_domain;;
    'debug') jh_debug;;
    'os_tool') jh_os_tool;;
    'default')
        cd $jhm_path
        port=7200
        
        if [ -f $jhm_path/data/port.pl ];then
            port=$(cat $jhm_path/data/port.pl)
        fi

        if [ ! -f $jhm_path/data/default.pl ];then
            echo -e "\033[33mInstall Failed\033[0m"
            exit 1
        fi

        password=$(cat $jhm_path/data/default.pl)
        if [ -f $jhm_path/data/domain.conf ];then
            address=$(cat $jhm_path/data/domain.conf)
        fi
        if [ -f $jhm_path/data/admin_path.pl ];then
            auth_path=$(cat $jhm_path/data/admin_path.pl)
        fi

        protocol="http"
        if [ -f $jhm_path/data/ssl.pl ];then
            protocol="https"
        fi
	    
        if [ "$address" = "" ];then
            v4=$(python3 $jhm_path/tools.py getServerIp 4)
            v4_local=$(python3 $jhm_path/tools.py getLocalIp 4)
            v6=$(python3 $jhm_path/tools.py getServerIp 6)

            if [ "$v4" != "" ] && [ "$v6" != "" ]; then
                address="jh-monitor-Url-Ipv4: $protocol://$v4:$port$auth_path \njh-monitor-Url-Ipv4(LAN):$protocol://$v4_local:$port$auth_path \njh-monitor-Url-Ipv6:$protocol://[$v6]:$port$auth_path"
            elif [ "$v4" != "" ]; then
                address="jh-monitor-Url: $protocol://$v4:$port$auth_path \njh-monitor-Url(LAN):$protocol://$v4_local:$port$auth_path"
            elif [ "$v6" != "" ]; then

                if [ ! -f $jhm_path/data/ipv6.pl ];then
                    #  Need to restart ipv6 to take effect
                    echo 'True' > $jhm_path/data/ipv6.pl
                    jh_stop
                    jh_start
                fi
                address="jh-monitor-Url: $protocol://[$v6]:$port$auth_path"
            else
                address="jh-monitor-Url: $protocol://you-network-ip:$port$auth_path"
            fi
        else
            address="jh-monitor-Url: $protocol://$address:$port$auth_path"
        fi

        show_panel_ip="$port|"
        echo -e "=================================================================="
        echo -e "\033[32mjh-monitor default info!\033[0m"
        echo -e "=================================================================="
        echo -e "$address"
        echo -e `python3 $jhm_path/tools.py username`
        echo -e `python3 $jhm_path/tools.py password`
        # echo -e "password: $password"
        echo -e "\033[33mWarning:\033[0m"
        echo -e "\033[33mIf you cannot access the panel. \033[0m"
        echo -e "\033[33mrelease the following port (${show_panel_ip}) in the security group.\033[0m"
        echo -e "=================================================================="
        ;;
    *)
        cd $jhm_path && python3 $jhm_path/tools.py cli $1 $2
        ;;
esac
