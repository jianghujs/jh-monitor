#!/bin/bash
PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sbin:~/bin
DIR=$(cd "$(dirname "$0")"; pwd)
MDIR=$(dirname "$DIR")


PATH=$PATH:$DIR/bin
if [ -f bin/activate ];then
	source bin/activate
fi

export LC_ALL="en_US.UTF-8"


jh_start_task()
{
    isStart=$(ps aux |grep 'task.py'|grep -v grep|awk '{print $2}')
    if [ "$isStart" == '' ];then
        echo -e "Starting jh-monitor-tasks... \c"
        cd $DIR && python3 task.py >> ${DIR}/logs/task.log 2>&1 &
        sleep 0.3
        isStart=$(ps aux |grep 'task.py'|grep -v grep|awk '{print $2}')
        if [ "$isStart" == '' ];then
                echo -e "\033[31mfailed\033[0m"
                echo '------------------------------------------------------'
                tail -n 20 $DIR/logs/task.log
                echo '------------------------------------------------------'
                echo -e "\033[31mError: jh-monitor-tasks service startup failed.\033[0m"
                return;
        fi
        echo -e "\033[32mdone\033[0m"
    else
        echo "Starting jh-monitor-tasks... jh-monitor-tasks (pid $(echo $isStart)) already running"
    fi
}

jh_start(){
	gunicorn -c setting.py app:app
	#安全启动
	jh_start_task
}


jh_start_debug(){
	python3 task.py >> $DIR/logs/task.log 2>&1 &
	gunicorn -b :7200 -k gevent -w 1 app:app
}

jh_start_debug2(){
	python3 task.py >> $DIR/logs/task.log 2>&1 &
	gunicorn -b :7200 -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1  app:app
}


jh_stop()
{
	PLIST=`ps -ef|grep app:app |grep -v grep|awk '{print $2}'`
	for i in $PLIST
	do
	    kill -9 $i
	done

	pids=`ps -ef|grep task.py | grep -v grep |awk '{print $2}'`
	arr=($pids)
    for p in ${arr[@]}
    do
    	kill -9 $p
    done
}

case "$1" in
    'start') jh_start;;
    'stop') jh_stop;;
    'restart') 
		jh_stop 
		jh_start
		;;
	'debug') 
		jh_stop 
		jh_start_debug
		;;
	'debug2') 
		jh_stop 
		jh_start_debug2
		;;
esac