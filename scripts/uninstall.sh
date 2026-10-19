#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
export LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

if [ -f /etc/motd ];then
    echo "" > /etc/motd
fi

startTime=`date +%s`

_os=`uname`
echo "use system: ${_os}"

if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi

UNINSTALL_JHM()
{
    echo -e "----------------------------------------------------"
    echo -e "检查已有jh-monitor环境，确定要删除并清空云监控面板数据吗？"
    echo -e "----------------------------------------------------"
    read -p "输入yes强制卸载面板: " yes;
    if [ "$yes" != "yes" ];then
        echo -e "------------"
        echo "取消卸载面板"
    else
        jhm 2 -y
        rm -rf /usr/bin/jhm
        rm -rf /etc/init.d/jhm
        systemctl daemon-reload
        rm -rf /www/server/jh-monitor
        echo "卸载面板成功"
    fi
}

UNINSTALL_JHM

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"
