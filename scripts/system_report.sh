#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
export PATH

export LANG=en_US.UTF-8
MW_PATH=/www/server/jh-monitor/bin/activate
if [ -f $MW_PATH ];then
    source $MW_PATH
fi

pushd /www/server/jh-monitor/ > /dev/null 
python3 /www/server/jh-monitor/scripts/report.py send
popd > /dev/null
echo "----------------------------------------------------------------------------"
endDate=`date +"%Y-%m-%d %H:%M:%S"`
echo "★[$endDate] Successful"
echo "----------------------------------------------------------------------------"
