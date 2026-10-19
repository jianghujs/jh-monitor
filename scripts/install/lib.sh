#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin

curPath=`pwd`
rootPath=$(dirname "$curPath")
serverPath=$(dirname "$rootPath")
sourcePath=$serverPath/source/lib
libPath=$serverPath/lib

mkdir -p $sourcePath
mkdir -p $libPath
rm -rf ${libPath}/lib.pl


#面板需要的库
which pip && pip install --upgrade pip
pip3 install --upgrade setuptools
cd /www/server/jh-monitor && pip3 install -r /www/server/jh-monitor/requirements.txt

# pip3 install flask-caching==1.10.1
# pip3 install mysqlclient


if [ ! -f /www/server/jh-monitor/bin/activate ];then
    cd /www/server/jh-monitor && python3 -m venv .
    cd /www/server/jh-monitor && source /www/server/jh-monitor/bin/activate
else
    cd /www/server/jh-monitor && source /www/server/jh-monitor/bin/activate
fi

pip install --upgrade pip
pip3 install --upgrade setuptools
cd /www/server/jh-monitor && pip3 install -r /www/server/jh-monitor/requirements.txt

echo "lib is ok!"
# pip3 install flask-caching==1.10.1
# pip3 install mysqlclient

