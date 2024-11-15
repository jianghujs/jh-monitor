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

class host_api:
    
    host_field = 'id,host_id,host_name,host_group_id,host_group_name,ip,os,remark,ssh_port,ssh_user,ssh_pkey,is_jhpanel,is_pve,is_master,backup_host_id,backup_host_name,backup_ip,addtime,host_status,host_info,cpu_info,mem_info,disk_info,net_info,load_avg,firewall_info,port_info,backup_info,temperature_info,ssh_user_list,detail_addtime'
    host_detail_field = 'id,host_id,host_name,host_status,uptime,host_info,cpu_info,mem_info,disk_info,net_info,load_avg,firewall_info,port_info,backup_info,temperature_info,ssh_user_list,last_update,addtime'
    host_alarm_field = "id,host_id,host_name,alarm_type,alarm_level,alarm_content,addtime"

    def listApi(self):
        limit = request.form.get('limit', '10')
        p = request.form.get('p', '1')
        host_group_id = request.form.get('host_group_id', '')
        start = (int(p) - 1) * (int(limit))
        try:
            hostM = jh.M('view01_host')
            
            if host_group_id != '' and host_group_id != '-1':
                hostM.where('host_group_id=?', (host_group_id,))

            _list = hostM.field(self.host_field).limit(
                (str(start)) + ',' + limit).order('id desc').select()

            if type(_list) == str:
                return jh.returnJson(False, '获取失败!' + _list)

            # 循环转换详情数据
            for i in range(len(_list)):
                _list[i] = self.parseDetailJSONValue(_list[i])
            
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
        except Exception as e:
            return jh.returnJson(False, '获取失败!' + str(e))

    
    def getHostGroupListApi(self):
        data = jh.M("host_group").field("id,host_group_id,host_group_name").order("id asc").select()
        data.insert(0, {"id": 0, "host_group_id": "default", "host_group_name": "默认分组"})
        return jh.getJson(data)

    
    def addHostGroupApi(self):
        host_group_name = request.form.get('host_group_name', '').strip()
        if not host_group_name:
            return jh.returnJson(False, "分组名称不能为空")
        if len(host_group_name) > 18:
            return jh.returnJson(False, "分组名称长度不能超过6个汉字或18位字母")
        if jh.M('host_group').where('host_group_name=?', (host_group_name,)).count() > 0:
            return jh.returnJson(False, "指定分组名称已存在!")
        host_group_id = 'HG' + '_' + jh.getRandomString(4)
        jh.M('host_group').add("host_group_id,host_group_name", (host_group_id,host_group_name,))
        return jh.returnJson(True, '添加成功!')

    def removeHostGroupApi(self):
        id = request.form.get('id', '')
        if jh.M('host_group').where('id=?', (id,)).count() == 0:
            return jh.returnJson(False, "指定分组不存在!")
        # 查询host_group_id
        host_group_id = jh.M('host_group').where('id=?', (id,)).getField('host_group_id')
        jh.M('host_group').where('id=?', (id,)).delete()
        jh.M("host").where("host_group_id=?", (host_group_id,)).save("host_group_id", ('default',))
        return jh.returnJson(True, "分组已删除!")

    def modifyHostGroupNameApi(self):
        # 修改主机分组名称
        host_group_name = request.form.get('host_group_name', '').strip()
        mid = request.form.get('id', '')
        if not host_group_name:
            return jh.returnJson(False, "分组名称不能为空")
        if len(host_group_name) > 18:
            return jh.returnJson(False, "分组名称长度不能超过6个汉字或18位字母")
        if jh.M('host_group').where('id=?', (mid,)).count() == 0:
            return jh.returnJson(False, "指定分组不存在!")
        jh.M('host_group').where('id=?', (mid,)).setField('host_group_name', host_group_name)
        return jh.returnJson(True, "修改成功!")

    def addApi(self):
        host_name = request.form.get('host_name', '10')
        ip = request.form.get('ip', '')
        with open('/etc/ansible/hosts', 'a') as f:
            f.write(f"{ip}\n")

        jh.M('host').add("host_name,ip,addtime", (host_name, ip, time.strftime('%Y-%m-%d %H:%M:%S')))
        return jh.returnJson(True, '主机添加成功!')

    def updateHostNameApi(self):
        host_id = request.form.get('host_id', '')
        host_name = request.form.get('host_name', '')
        
        jh.M('host').where('host_id=?', (host_id,)).setField('host_name', host_name)
        return jh.returnJson(True, '主机名称修改成功!')

    def changeHostGroupApi(self):
        host_id = request.form.get('host_id', '')
        host_group_id = request.form.get('host_group_id', '')

        if host_group_id == 'default':
            host_group_name = ''
        else:
            host_group_name = jh.M('host_group').where('host_group_id=?', (host_group_id,)).getField('host_group_name')
            if not host_group_name:
                return jh.returnJson(False, '指定分组不存在!')
        
        jh.M('host').where('host_id=?', (host_id,)).setField('host_group_id', host_group_id)
        jh.M('host').where('host_id=?', (host_id,)).setField('host_group_name', host_group_name)
        return jh.returnJson(True, '主机分组修改成功!')

    def deleteApi(self):
        host_id = request.form.get('host_id', '')
        jh.M('host').where('host_id=?', (host_id,)).delete()
        return jh.returnJson(True, '主机删除成功!')

    def detailApi(self):
        host_id = request.form.get('host_id', '')
        host_detail = jh.M('view01_host').where('host_id=?', (host_id,)).field(self.host_field).find()
        if host_detail:
            host_detail = self.parseDetailJSONValue(host_detail)
            return jh.returnJson(True, 'ok',  host_detail)
        return jh.returnJson(False, '获取为空', {})
    
    def getClientInstallShellLanApi(self):
        client_install_shell = f"curl -sSO https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/client/install.sh && bash install.sh install http://{jh.getHostAddr()}:10844"
        server_ip = jh.getHostAddr()
        github_script_url = "https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/client/install.sh"
        gitee_script_url = "https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/client/install.sh"
        command_template = "wget -O /tmp/install.sh %s && bash /tmp/install.sh install http://%s:10844"
        return jh.returnJson(True, 'ok', {
            'github': command_template % (github_script_url, server_ip),
            'gitee': command_template % (gitee_script_url, server_ip)
        })

    def alarmApi(self):
        host_id = request.form.get('host_id', '')
        host_alarm = jh.M('host_alarm').where('host_id=?', (host_id,)).field(self.host_alarm_field).select()
        if host_alarm:
            return jh.returnJson(True, 'ok',  host_alarm)
        return jh.returnJson(False, '获取为空', {})

    def parseDetailJSONValue(self, host_detail):
        # 转成json
        host_detail['host_info'] = json.loads(host_detail['host_info']) if host_detail.get('host_info') is not None else {}
        host_detail['cpu_info'] = json.loads(host_detail['cpu_info']) if host_detail.get('cpu_info') is not None else {}
        host_detail['mem_info'] = json.loads(host_detail['mem_info']) if host_detail.get('mem_info') is not None else {}
        host_detail['disk_info'] = json.loads(host_detail['disk_info']) if host_detail.get('disk_info') is not None else []
        host_detail['net_info'] = json.loads(host_detail['net_info']) if host_detail.get('net_info') is not None else []
        host_detail['load_avg'] = json.loads(host_detail['load_avg']) if host_detail.get('load_avg') is not None else {}
        host_detail['firewall_info'] = json.loads(host_detail['firewall_info']) if host_detail.get('firewall_info') is not None else {}
        host_detail['port_info'] = json.loads(host_detail['port_info']) if host_detail.get('port_info') is not None else {}
        host_detail['backup_info'] = json.loads(host_detail['backup_info']) if host_detail.get('backup_info') is not None else {}
        host_detail['temperature_info'] = json.loads(host_detail['temperature_info']) if host_detail.get('temperature_info') is not None else {}

        return host_detail

    def getAllHostChartApi(self):
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        print(start, end)
        data = self.getAllHostChartData(start, end)
        
        return jh.getJson(self.lessenData(data))

    def getHostLoadAverageApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostLoadAverageData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostCpuIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostCpuIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostMemIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostMemIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostDiskIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostDiskIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostNetworkIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostNetWorkIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))
    
    def getAllHostChartData(self, start, end):
        # 取所有主机的数据
        data = jh.M('host_detail').where("addtime>=? AND addtime<=?", (start, end)).field(
            'id,host_id,host_name,cpu_info,mem_info,disk_info,net_info,load_avg,addtime'
        ).order('addtime asc').select()
        for i in range(len(data)):
            data[i]['addtime'] = time.strftime(
                '%m/%d %H:%M', time.localtime(float(data[i]['addtime'])))
        
        # 按host_id分组
        host_data = {}
        for value in data:
            if value['host_id'] not in host_data:
                host_data[value['host_id']] = []
            host_data[value['host_id']].append(value)
        # 防止线过于密集，每个host_id最多只取平均分布的100条
        for key in host_data:
            host_data[key] = self.lessenData(host_data[key])
        
        return host_data


    def getHostNetWorkIoData(self, host_id, start, end):
        # 取指定时间段的网络Io
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,up,down,total_up,total_down,down_packets,up_packets,addtime'
            'id,net_info,addtime'
        ).order('addtime asc').select()
        
        return self.toAddtime(data)

    def getHostDiskIoData(self, host_id, start, end):
        # 取指定时间段的磁盘Io
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,read_count,write_count,read_bytes,write_bytes,read_time,write_time,addtime'
            'id,disk_info,addtime'
        ).order('id asc').select()
        return self.toAddtime(data)

    def getHostCpuIoData(self, host_id, start, end):
        # 取指定时间段的CpuIo
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,pro,mem,addtime'
            'id,cpu_info,mem_info,addtime'
        ).order('id asc').select()
        return self.toAddtime(data, False)

    def getHostMemIoData(self, host_id, start, end):
        # 取指定时间段的内存Io
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", (host_id, start, end)).field(
            # 'id,pro,mem,addtime'
            'id,mem_info,addtime'
        ).order('id asc').select()
        return self.toAddtime(data, True)

    def getHostLoadAverageData(self, host_id, start, end):
        data = jh.M('host_detail').where("host_id=? AND addtime>=? AND addtime<=?", ( host_id, start, end)).field(
            # 'id,pro,one,five,fifteen,addtime'
            'id,load_avg,cpu_info,addtime'
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

    # 防止线过于密集，每个host_id最多只取平均分布的100条
    def lessenData(self, data, count = 100):
        length = len(data)
        if length > count:
            step = int(length / count)
            data = data[::step]
        return data