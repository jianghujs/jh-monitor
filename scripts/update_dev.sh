#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH
# LANG=en_US.UTF-8
is64bit=`getconf LONG_BIT`

startTime=`date +%s`

_os=`uname`
echo "use system: ${_os}"

if [ "$EUID" -ne 0 ]
  then echo "Please run as root!"
  exit
fi


if [ ${_os} == "Darwin" ]; then
	OSNAME='macos'
elif grep -Eq "openSUSE" /etc/*-release; then
	OSNAME='opensuse'
	zypper refresh
elif grep -Eq "FreeBSD" /etc/*-release; then
	OSNAME='freebsd'
elif grep -Eqi "CentOS" /etc/issue || grep -Eq "CentOS" /etc/*-release; then
	OSNAME='centos'
	yum install -y wget zip unzip
elif grep -Eqi "Fedora" /etc/issue || grep -Eq "Fedora" /etc/*-release; then
	OSNAME='fedora'
	yum install -y wget zip unzip
elif grep -Eqi "Rocky" /etc/issue || grep -Eq "Rocky" /etc/*-release; then
	OSNAME='rocky'
	yum install -y wget zip unzip
elif grep -Eqi "AlmaLinux" /etc/issue || grep -Eq "AlmaLinux" /etc/*-release; then
	OSNAME='alma'
	yum install -y wget zip unzip
elif grep -Eqi "Amazon Linux" /etc/issue || grep -Eq "Amazon Linux" /etc/*-release; then
	OSNAME='amazon'
	yum install -y wget zip unzip
elif grep -Eqi "Debian" /etc/issue || grep -Eq "Debian" /etc/*-release; then
	OSNAME='debian'
	apt install -y wget zip unzip
elif grep -Eqi "Ubuntu" /etc/issue || grep -Eq "Ubuntu" /etc/*-release; then
	OSNAME='ubuntu'
	apt install -y wget zip unzip
elif grep -Eqi "Raspbian" /etc/issue || grep -Eq "Raspbian" /etc/*-release; then
	OSNAME='raspbian'
else
	OSNAME='unknow'
fi

cn=$(curl -fsSL -m 10 http://ipinfo.io/json | grep "\"country\": \"CN\"")
if [ ! -z "$cn" ];then
	curl -sSLo /tmp/dev.zip https://gitee.com/jianghujs/jh-monitor/repository/archive/dev.zip
else
	curl -sSLo /tmp/dev.zip https://github.com/jianghujs/jh-monitor/archive/refs/heads/dev.zip
fi

# wget -O /tmp/dev.zip https://github.com/jianghujs/jh-monitor/archive/refs/heads/dev.zip
cd /tmp && unzip /tmp/dev.zip
cp -rf /tmp/jh-monitor-dev/* /www/server/jh-monitor
rm -rf /tmp/dev.zip
rm -rf /tmp/jh-monitor-dev

if [ -f /etc/rc.d/init.d/jhm ];then
    sh /etc/rc.d/init.d/jhm stop && rm -rf /www/server/jh-monitor/scripts/init.d/jhm && rm -rf /etc/rc.d/init.d/jhm
fi

#pip uninstall public
echo "use system version: ${OSNAME}"
cd /www/server/jh-monitor && bash scripts/update/${OSNAME}.sh

bash /etc/rc.d/init.d/jhm restart
bash /etc/rc.d/init.d/jhm default

if [ -f /usr/bin/jhm ];then
	rm -rf /usr/bin/jhm
fi

if [ ! -e /usr/bin/jhm ]; then
	if [ ! -f /usr/bin/jhm ];then
		ln -s /etc/rc.d/init.d/jhm /usr/bin/jhm
	fi
fi

endTime=`date +%s`
((outTime=($endTime-$startTime)/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"