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

class host_api:
    def listHostApi():
        limit = request.form.get('limit', '10')
        p = request.form.get('p', '1')
        start = (int(p) - 1) * (int(limit))

        hostM = jh.M('host')
        _list = hostM.field('id, host_name, ip, os, remark').limit(
            (str(start)) + ',' + limit).order('id desc').select()
        
        _ret = {}
        _ret['data'] = _list

        count = hostM.count()
        _page = {}
        _page['count'] = count
        _page['tojs'] = 'getWeb'
        _page['p'] = p
        _page['row'] = limit

        _ret['page'] = jh.getPage(_page)
        return jh.getJson(_ret)

    def addHostApi():
        host_name = request.form.get('host_name', '10')
        ip = request.form.get('ip', '')
        with open('/etc/ansible/hosts', 'a') as f:
            f.write(f"{ip}\n")

        jh.M('host').add("host_name, ip, addtime", (host_name, ip, time.strftime('%Y-%m-%d %H:%M:%S')))
        return jh.returnJson(True, '主机添加成功!')

    def deleteHostApi():
        host_id = request.form.get('id', '')
        jh.M('host').where('id=?', (host_id,)).delete()
        return jh.returnJson(True, '主机删除成功!')

    def getHostDetail(host_id):
        host_detail = jh.M('host_detail').where('host_id=?', (host_id,)).order('id desc').limit(1).select()
        if host_detail:
            return jh.returnJson(True, 'ok',  host_detail)
        return jh.returnJson(False, '获取为空', {})

    
    def getHostLoadAverageApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getLoadAverageData(start, end)
        return jh.getJson(data)

    def getHostCpuIoApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getCpuIoData(start, end)
        return jh.getJson(data)

    def getHostDiskIoApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getDiskIoData(start, end)
        return jh.getJson(data)

    def getHostNetworkIoApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getNetWorkIoData(start, end)
        return jh.getJson(data)

    def getHostNetWorkIoData(self, host_id, start, end):
        # 取指定时间段的网络Io
        data = jh.M('host_detail').dbfile('system').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            'id,up,down,total_up,total_down,down_packets,up_packets,addtime').order('id asc').select()
        return self.toAddtime(data)

    def getHostDiskIoData(self, host_id, start, end):
        # 取指定时间段的磁盘Io
        data = jh.M('host_detail').dbfile('system').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            'id,read_count,write_count,read_bytes,write_bytes,read_time,write_time,addtime').order('id asc').select()
        return self.toAddtime(data)

    def getHostCpuIoData(self, host_id, start, end):
        # 取指定时间段的CpuIo
        data = jh.M('host_detail').dbfile('system').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            'id,pro,mem,addtime').order('id asc').select()
        return self.toAddtime(data, True)

    def getHostLoadAverageData(self, host_id, start, end):
        data = jh.M('host_detail').dbfile('system').where("host_id=? AND addtime>=? AND addtime<=?", ( host_id, start, end)).field(
            'id,pro,one,five,fifteen,addtime').order('id asc').select()
        return self.toAddtime(data)

    # 格式化addtime列
    def toAddtime(self, data, tomem=False):
        import time
        if tomem:
            import psutil
            mPre = (psutil.virtual_memory().total / 1024 / 1024) / 100
        length = len(data)
        he = 1
        if length > 100:
            he = 1
        if length > 1000:
            he = 3
        if length > 10000:
            he = 15
        if he == 1:
            for i in range(length):
                data[i]['addtime'] = time.strftime(
                    '%m/%d %H:%M', time.localtime(float(data[i]['addtime'])))
                if tomem and data[i]['mem'] > 100:
                    data[i]['mem'] = data[i]['mem'] / mPre

            return data
        else:
            count = 0
            tmp = []
            for value in data:
                if count < he:
                    count += 1
                    continue
                value['addtime'] = time.strftime(
                    '%m/%d %H:%M', time.localtime(float(value['addtime'])))
                if tomem and value['mem'] > 100:
                    value['mem'] = value['mem'] / mPre
                tmp.append(value)
                count = 0
            return tmp

