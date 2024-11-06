# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云控
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
        with open('/etc/ansible/hosts', 'a') as f:
            f.write(f"{ip}\n")

        jh.M('host').add("host_name,ip,addtime", (host_name, ip, time.strftime('%Y-%m-%d %H:%M:%S')))
        return jh.returnJson(True, '主机添加成功!')