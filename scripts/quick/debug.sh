#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

echo "welcome to jh-monitor panel"

startTime=`date +%s`

if [ ! -d /www/server/jh-monitor ];then
	echo "jh-monitor not exist!"
	exit 1
fi

# openresty
if [ ! -d /www/server/openresty ];then
	cd /www/server/jh-monitor/plugins/openresty && bash install.sh install 1.21.4.1
fi


# php
# if [ ! -d /www/server/php/71 ];then
# 	cd /www/server/jh-monitor/plugins/php && bash install.sh install 71
# fi



PHP_VER_LIST=(53 54 55 56 70 71 72 73 74 80 81)
# PHP_VER_LIST=(81)
for PHP_VER in ${PHP_VER_LIST[@]}; do
	echo "php${PHP_VER} -- start"
	if [ ! -d  /www/server/php/${PHP_VER} ];then
		cd /www/server/jh-monitor/plugins/php && bash install.sh install ${PHP_VER}
	fi
	echo "php${PHP_VER} -- end"
done


# cd /www/server/jh-monitor/plugins/php-yum && bash install.sh install 74


# mysql
if [ ! -d /www/server/mysql ];then
	# cd /www/server/jh-monitor/plugins/mysql && bash install.sh install 5.7


	cd /www/server/jh-monitor/plugins/mysql && bash install.sh install 5.6
	# cd /www/server/jh-monitor/plugins/mysql && bash install.sh install 8.0
fi

endTime=`date +%s`
((outTime=(${endTime}-${startTime})/60))
echo -e "Time consumed:\033[32m $outTime \033[0mMinute!"

