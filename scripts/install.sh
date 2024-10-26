#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

if [ -f /etc/motd ];then
    echo "welcome to jianghu panel (base on jh-monitor)" > /etc/motd
fi

startTime=`date +%s`
netEnvCn="$1"
echo "netEnvCn: ${netEnvCn}"
_os=`uname`
echo "use system: ${_os}"

# 必须以root用户运行
if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi

# 解除系统限制打开文件数
sed -i '/^root soft nofile/d' /etc/security/limits.conf
echo "root soft nofile 500000" >> /etc/security/limits.conf
sed -i '/^root hard nofile/d' /etc/security/limits.conf
echo "root hard nofile 500000" >> /etc/security/limits.conf
ulimit -n 500000

if grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
else
	OSNAME='unknow'
fi


echo "use system version: ${OSNAME}"
if [ "$netEnvCn" == "cn" ]; then
  if [ "$OSNAME" == "debian" ]; then
    wget -O switch_apt_sources.sh https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/switch_apt_sources.sh && bash switch_apt_sources.sh 2
  fi
  wget -O ${OSNAME}_cn.sh https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/install/${OSNAME}_cn.sh && bash ${OSNAME}_cn.sh
else
  if [ "$OSNAME" == "debian" ]; then
    wget -O switch_apt_sources.sh https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/switch_apt_sources.sh && bash switch_apt_sources.sh 1
  fi
  wget -O ${OSNAME}.sh https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/install/${OSNAME}.sh && bash ${OSNAME}.sh
fi

# 启动面板
cd /www/server/jh-monitor && bash cli.sh start
isStart=`ps -ef|grep 'gunicorn -c setting.py app:app' |grep -v grep|awk '{print $2}'`
n=0
while [ ! -f /etc/rc.d/init.d/jhm ];
do
    echo -e ".\c"
    sleep 1
    let n+=1
    if [ $n -gt 20 ];then
    	echo -e "start jh fail"
    	exit 1
    fi
done

# 启动面板
cd /www/server/jh-monitor && bash /etc/rc.d/init.d/jhm stop
cd /www/server/jh-monitor && bash /etc/rc.d/init.d/jhm start
cd /www/server/jh-monitor && bash /etc/rc.d/init.d/jhm default

sleep 2
if [ ! -e /usr/bin/jhm ]; then
	if [ -f /etc/rc.d/init.d/jhm ];then
    # 添加软连接
		ln -s /etc/rc.d/init.d/jhm /usr/bin/jhm
	fi
fi

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"
