# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 主机管理
# ---------------------------------------------------------------------------------

import time
import os
import sys
from urllib.parse import urlparse
import jh
import re
import json
import shutil
import psutil


from flask import request


from flask import Flask, request, jsonify
import jh
import time

app = Flask(__name__)

class pub_api:
    
    def getPubKeyApi(self):
        if os.path.exists('/root/.ssh/id_rsa.pub'):
            return jh.returnJson(True, 'ok', jh.readFile('/root/.ssh/id_rsa.pub'))
        return jh.returnJson(True, 'ok', '')
    
    
    def addHostApi(self):
        host_name = request.form.get('host_name', '10')
        ip = request.form.get('ip', '')
        port = request.form.get('port', '10022')
        host_id = 'H_' + host_name + '_' + jh.getRandomString(4)
        host_group_id = 'default'
        host_group_name = ''

        exist_host = jh.M('host').where('ip=?', (ip,)).field('ip').find()
        if len(exist_host) > 0:
            return jh.returnJson(False, '主机已经存在!')
        
        # 添加主机
        jh.M('host').add("host_id,host_name,host_group_id,host_group_name,ip,ssh_port,addtime", (host_id,host_name,host_group_id,host_group_name,ip,port,time.strftime('%Y-%m-%d %H:%M:%S')))
        # 添加到host文件
        with open('/etc/ansible/hosts', 'r+') as f:
            lines = f.readlines()
            existing_ips = set(line.strip() for line in lines)
            ip_conf = f"{ip} ansible_ssh_user=ansible_user ansible_ssh_port={port}"
            if ip_conf not in existing_ips:
                f.write(f"{ip_conf}\n")

        return jh.returnJson(True, '主机添加成功!')