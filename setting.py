# coding:utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 配置文件
# ---------------------------------------------------------------------------------


import time
import sys
import random
import os

pwd = os.getcwd()
sys.path.append(pwd + '/class/core')

import jh

# cmd = 'ls /usr/local/lib/ | grep python  | cut -d \\  -f 1 | awk \'END {print}\''
# info = jh.execShell(cmd)
# p = "/usr/local/lib/" + info[0].strip() + "/site-packages"
# p_debain = "/usr/local/lib/" + info[0].strip() + "/dist-packages"

# sys.path.append(p)
# sys.path.append(p_debain)

import system_api
cpu_info = system_api.system_api().getCpuInfo()
workers = cpu_info[1]


log_dir = os.getcwd() + '/logs'
if not os.path.exists(log_dir):
    os.mkdir(log_dir)

# default port
jh_port = "7200"
if os.path.exists("data/port.pl"):
    jh_port = jh.readFile('data/port.pl')
    jh_port.strip()
else:
    import firewall_api
    import common
    common.initDB()
    # jh_port = str(random.randint(10000, 65530))
    jh_port = "10844"
    firewall_api.firewall_api().addAcceptPortArgs(jh_port, 'tcp', 'WEB面板', 'port')
    jh.writeFile('data/port.pl', jh_port)

bind = []
if os.path.exists('data/ipv6.pl'):
    bind.append('[0:0:0:0:0:0:0:0]:%s' % jh_port)
else:
    bind.append('0.0.0.0:%s' % jh_port)


# 初始安装时,自动生成安全路径
if not os.path.exists('data/admin_path.pl'):
    admin_path = jh.getRandomString(8)
    jh.writeFile('data/admin_path.pl', '/' + admin_path.lower())

workers = 1
threads = workers * 1
backlog = 512
reload = False
daemon = True
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'
timeout = 7200
keepalive = 60
preload_app = True
capture_output = True
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'
loglevel = 'info'
errorlog = log_dir + '/error.log'
accesslog = log_dir + '/access.log'
pidfile = log_dir + '/jh.pid'
