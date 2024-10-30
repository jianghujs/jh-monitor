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
    
    host_field = 'id,host_name,ip,os,remark,ssh_port,ssh_user,ssh_pkey,is_jhpanel,is_pve,is_master,backup_host_id,backup_host_name,backup_ip,addtime'
    host_detail_field = 'id,host_id,host_name,host_status,uptime,host_info,cpu_info,mem_info,disk_info,net_info,load_avg,firewall_info,port_info,backup_info,temperature_info,last_update,addtime'

    def listApi(self):
        limit = request.form.get('limit', '10')
        p = request.form.get('p', '1')
        start = (int(p) - 1) * (int(limit))

        hostM = jh.M('host')
        _list = hostM.field(self.host_field).limit(
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

    def addApi(self):
        host_name = request.form.get('host_name', '10')
        ip = request.form.get('ip', '')
        with open('/etc/ansible/hosts', 'a') as f:
            f.write(f"{ip}\n")

        jh.M('host').add("host_name,ip,addtime", (host_name, ip, time.strftime('%Y-%m-%d %H:%M:%S')))
        return jh.returnJson(True, '主机添加成功!')

    def deleteApi(self):
        host_id = request.form.get('id', '')
        jh.M('host').where('id=?', (host_id,)).delete()
        return jh.returnJson(True, '主机删除成功!')

    def detailApi(self):
        host_id = request.form.get('id', '')
        host_detail = jh.M('host_detail').where('id=?', (host_id,)).field(self.host_detail_field).find()
        if host_detail:
            return jh.returnJson(True, 'ok',  host_detail)
        return jh.returnJson(False, '获取为空', {})

    def getHostLoadAverageApi(self):
        host_id = request.form.get('id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostLoadAverageData(host_id, start, end)
        return jh.getJson(data)

    def getHostCpuIoApi(self):
        host_id = request.form.get('id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostCpuIoData(host_id, start, end)
        return jh.getJson(data)

    def getHostDiskIoApi(self):
        host_id = request.form.get('id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostDiskIoData(host_id, start, end)
        return jh.getJson(data)

    def getHostNetworkIoApi(self):
        host_id = request.form.get('id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostNetWorkIoData(host_id, host_id, start, end)
        return jh.getJson(data)

    def getHostNetWorkIoData(self, host_id, start, end):
        # 取指定时间段的网络Io
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,up,down,total_up,total_down,down_packets,up_packets,addtime'
            self.host_detail_field
        ).order('id asc').select()
        
        print("data", data)
        return self.toAddtime(data)

    def getHostDiskIoData(self, host_id, start, end):
        # 取指定时间段的磁盘Io
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,read_count,write_count,read_bytes,write_bytes,read_time,write_time,addtime'
            self.host_detail_field
        ).order('id asc').select()
        return self.toAddtime(data)

    def getHostCpuIoData(self, host_id, start, end):
        # 取指定时间段的CpuIo
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,pro,mem,addtime'
            self.host_detail_field
        ).order('id asc').select()
        return self.toAddtime(data, False)

    def getHostLoadAverageData(self, host_id, start, end):
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", ( host_id, start, end)).field(
            # 'id,pro,one,five,fifteen,addtime'
            self.host_detail_field
        ).order('id asc').select()
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

