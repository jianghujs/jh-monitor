# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 公共操作
# ---------------------------------------------------------------------------------

import os
import sys
import time
import string
import json
import hashlib
import shlex
import datetime
import subprocess
import re
import hashlib
from random import Random

import jh
import db

from flask import redirect


def init():
    initDB()
    initUserInfo()
    initInitD()
    initInitTask()


def local():
    result = checkClose()
    if result:
        return result


# 检查面板是否关闭
def checkClose():
    if os.path.exists('data/close.pl'):
        return redirect('/close')


def initDB():
    try:
        sql = db.Sql().dbfile('default')
        csql = jh.readFile('data/sql/default.sql')
        csql_list = csql.split(';')
        for index in range(len(csql_list)):
            sql.execute(csql_list[index], ())

    except Exception as ex:
        print(str(ex))


def doContentReplace(src, dst):
    content = jh.readFile(src)
    content = content.replace("{$SERVER_PATH}", jh.getRunDir())
    jh.writeFile(dst, content)


def initInitD():

    # systemctl
    # sysCfgDir = jh.systemdCfgDir()
    # if os.path.exists(sysCfgDir) and jh.getOsName() == 'centos' and jh.getOsID() == '9':
    #     systemd_jh = sysCfgDir + '/jh.service'
    #     systemd_jh_task = sysCfgDir + '/jh-task.service'

    #     systemd_jh_tpl = jh.getRunDir() + '/scripts/init.d/jhm.service.tpl'
    #     systemd_jh_task_tpl = jh.getRunDir() + '/scripts/init.d/jhm-task.service.tpl'

    #     if os.path.exists(systemd_jh):
    #         os.remove(systemd_jh)
    #     if os.path.exists(systemd_jh_task):
    #         os.remove(systemd_jh_task)

    #     doContentReplace(systemd_jh_tpl, systemd_jh)
    #     doContentReplace(systemd_jh_task_tpl, systemd_jh_task)

    #     jh.execShell('systemctl enable jh')
    #     jh.execShell('systemctl enable jh-task')
    #     jh.execShell('systemctl daemon-reload')

    script = jh.getRunDir() + '/scripts/init.d/jhm.tpl'
    script_bin = jh.getRunDir() + '/scripts/init.d/jhm'
    doContentReplace(script, script_bin)
    jh.execShell('chmod +x ' + script_bin)

    # 在linux系统中,确保/etc/init.d存在
    if not jh.isAppleSystem() and not os.path.exists("/etc/rc.d/init.d"):
        jh.execShell('mkdir -p /etc/rc.d/init.d')

    if not jh.isAppleSystem() and not os.path.exists("/etc/init.d"):
        jh.execShell('mkdir -p /etc/init.d')

    # initd
    if os.path.exists('/etc/rc.d/init.d'):
        initd_bin = '/etc/rc.d/init.d/jhm'
        # if not os.path.exists(initd_bin):
        import shutil
        shutil.copyfile(script_bin, initd_bin)
        jh.execShell('chmod +x ' + initd_bin)
        # 加入自启动
        jh.execShell('which chkconfig && chkconfig --add jhm')

    if os.path.exists('/etc/init.d'):
        initd_bin = '/etc/init.d/jhm'
        import shutil
        shutil.copyfile(script_bin, initd_bin)
        jh.execShell('chmod +x ' + initd_bin)
        # 加入自启动
        jh.execShell('which update-rc.d && update-rc.d -f jhm defaults')

    # 获取系统IPV4
    # jh.setHostAddr(jh.getLocalIp())
    jh.initPanelIp()


def initInitTask():
    # 创建证书同步命令
    import cert_api
    api = cert_api.cert_api()
    api.createCertCron()


def initUserInfo():

    data = jh.M('users').where('id=?', (1,)).getField('password')
    if data == '21232f297a57a5a743894a0e4a801fc3':
        pwd = jh.getRandomString(8).lower()
        file_pw = jh.getRunDir() + '/data/default.pl'
        jh.writeFile(file_pw, pwd)
        jh.M('users').where('id=?', (1,)).setField(
            'password', jh.md5(pwd))
