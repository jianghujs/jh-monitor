# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 系统信息操作
# ---------------------------------------------------------------------------------


import psutil
import time
import os
import re
import math
import sys
import json

from flask import Flask, session
from flask import request

import db
import jh

import config_api
import crontab_api
import requests

from threading import Thread
from time import sleep
import datetime

crontabApi = crontab_api.crontab_api()


def jh_async(f):
    def wrapper(*args, **kwargs):
        thr = Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


class system_api:
    setupPath = None
    pids = None

    def __init__(self):
        self.setupPath = jh.getServerDir()

    ##### ----- start ----- ###
    def networkApi(self):
        data = self.getNetWork()
        return jh.getJson(data)

    def updateServerApi(self):
        stype = request.args.get('type', 'check')
        version = request.args.get('version', '')
        return self.updateServer(stype, version)

    def updateServerCodeApi(self):
        jh.execShell("cd /www/server/jh-monitor && pip3 install -r /www/server/jh-monitor/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
        return jh.returnJson(True, '更新成功, 请手动重启面板!')

    def systemTotalApi(self):
        data = self.getSystemTotal()
        return jh.getJson(data)

    def diskInfoApi(self):
        diskInfo = self.getDiskInfo()
        return jh.getJson(diskInfo)

    def setControlApi(self):
        stype = request.form.get('type', '')
        day = request.form.get('day', '')
        data = self.setControl(stype, day)
        return data

    def getLoadAverageApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getLoadAverageData(start, end)
        return jh.getJson(data)

    def getCpuIoApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getCpuIoData(start, end)
        return jh.getJson(data)

    def getDiskIoApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getDiskIoData(start, end)
        return jh.getJson(data)

    def getNetworkIoApi(self):
        start = request.args.get('start', '')
        end = request.args.get('end', '')
        data = self.getNetWorkIoData(start, end)
        return jh.getJson(data)

    def rememoryApi(self):
        os.system('sync')
        scriptFile = jh.getRunDir() + '/script/rememory.sh'
        jh.execShell("/bin/bash " + scriptFile)
        data = self.getMemInfo()
        return jh.getJson(data)

    # 重启面板
    def restartApi(self):
        self.restartMw(True)
        return jh.returnJson(True, '面板已重启!')

    def restartStatusApi(self):
        restartTip = 'data/restart.pl'
        return jh.returnJson(True, os.path.exists(restartTip))

    def restartServerApi(self):
        if jh.isAppleSystem():
            return jh.returnJson(False, "开发环境不可重起")
        self.restartServer()
        return jh.returnJson(True, '正在重启服务器!')
    ##### ----- end ----- ###

    def restartTask(self):
        initd = jh.getRunDir() + '/scripts/init.d/jhm'
        if os.path.exists(initd):
            os.system(initd + ' ' + 'restart_task')
        return True

    def restartMw(self, restartAll=False):
        pl = 'restart.pl' if restartAll else 'restart_panel.pl'
        jh.writeFile('data/' + pl, 'True')
        return True

    @jh_async
    def restartServer(self):
        if not jh.isRestart():
            return jh.returnJson(False, '请等待所有安装任务完成再执行!')
        jh.execShell("sync && init 6 &")
        return jh.returnJson(True, '命令发送成功!')

        # 名取PID
    def getPid(self, pname):
        try:
            if not self.pids:
                self.pids = psutil.pids()
            for pid in self.pids:
                if psutil.Process(pid).name() == pname:
                    return True
            return False
        except:
            return False

    # 检查端口是否占用
    def isOpen(self, port):
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.connect(('127.0.0.1', int(port)))
            s.shutdown(2)
            return True
        except:
            return False

    # 检测指定进程是否存活
    def checkProcess(self, pid):
        try:
            if not self.pids:
                self.pids = psutil.pids()
            if int(pid) in self.pids:
                return True
            return False
        except:
            return False

    def getPanelInfo(self, get=None):
        # 取面板配置
        address = jh.GetLocalIp()
        try:
            try:
                port = web.ctx.host.split(':')[1]
            except:
                port = jh.readFile('data/port.pl')
        except:
            port = '7200'
        domain = ''
        if os.path.exists('data/domain.conf'):
            domain = jh.readFile('data/domain.conf')

        autoUpdate = ''
        if os.path.exists('data/autoUpdate.pl'):
            autoUpdate = 'checked'
        limitip = ''
        if os.path.exists('data/limitip.conf'):
            limitip = jh.readFile('data/limitip.conf')

        templates = []
        for template in os.listdir('templates/'):
            if os.path.isdir('templates/' + template):
                templates.append(template)
        template = jh.readFile('data/templates.pl')

        check502 = ''
        if os.path.exists('data/502Task.pl'):
            check502 = 'checked'
        return {'port': port, 'address': address, 'domain': domain, 'auto': autoUpdate, '502': check502, 'limitip': limitip, 'templates': templates, 'template': template}

    def getSystemTotal(self, interval=1):
        # 取系统统计信息
        data = self.getMemInfo()
        cpu = self.getCpuInfo(interval)
        data['cpuNum'] = cpu[1]
        data['cpuRealUsed'] = cpu[0]
        data['time'] = self.getBootTime()
        data['system'] = self.getSystemVersion()
        data['isuser'] = jh.M('users').where(
            'username=?', ('admin',)).count()
        data['version'] = '0.0.1'
        return data

    def getLoadAverage(self):
        c = os.getloadavg()
        data = {}
        data['one'] = round(float(c[0]), 2)
        data['five'] = round(float(c[1]), 2)
        data['fifteen'] = round(float(c[2]), 2)
        data['max'] = psutil.cpu_count() * 2
        data['limit'] = data['max']
        data['safe'] = data['max'] * 0.75
        return data

    def getAllInfo(self, get):
        data = {}
        data['load_average'] = self.GetLoadAverage(get)
        data['title'] = self.GetTitle()
        data['network'] = self.GetNetWorkApi(get)
        data['panel_status'] = not os.path.exists(
            '/www/server/jh-monitor/data/close.pl')
        import firewalls
        ssh_info = firewalls.firewalls().GetSshInfo(None)
        data['enable_ssh_status'] = ssh_info['status']
        data['disable_ping_status'] = not ssh_info['ping']
        data['time'] = self.GetBootTime()
        # data['system'] = self.GetSystemVersion();
        # data['mem'] = self.GetMemInfo();
        data['version'] = web.ctx.session.version
        return data

    def getTitle(self):
        titlePl = 'data/title.pl'
        title = '江湖云监控'
        if os.path.exists(titlePl):
            title = jh.readFile(titlePl).strip()
        return title

    def getSystemVersion(self):
        # 取操作系统版本
        if jh.getOs() == 'darwin':
            data = jh.execShell('sw_vers')[0]
            data_list = data.strip().split("\n")
            mac_version = ''
            for x in data_list:
                mac_version += x.split("\t")[1] + ' '
            return mac_version

        redhat_series = '/etc/redhat-release'
        if os.path.exists(redhat_series):
            version = jh.readFile('/etc/redhat-release')
            version = version.replace('release ', '').strip()
            return version

        os_series = '/etc/os-release'
        if os.path.exists(os_series):
            version = jh.execShell(
                "cat /etc/*-release | grep PRETTY_NAME | awk -F = '{print $2}' | awk -F '\"' '{print $2}'")
            return version[0].strip()

        return '未识别系统信息'

    def getBootTime(self):
        # 取系统启动时间
        uptime = jh.readFile('/proc/uptime')
        if uptime == False:
            start_time = psutil.boot_time()
            run_time = time.time() - start_time
        else:
            run_time = uptime.split()[0]
        tStr = float(run_time)
        min = tStr / 60
        hours = min / 60
        days = math.floor(hours / 24)
        hours = math.floor(hours - (days * 24))
        min = math.floor(min - (days * 60 * 24) - (hours * 60))
        return jh.getInfo('已不间断运行: {1}天{2}小时{3}分钟', (str(int(days)), str(int(hours)), str(int(min))))

    def getCpuInfo(self, interval=1):
        # 取CPU信息
        cpuCount = psutil.cpu_count()
        cpuLogicalNum = psutil.cpu_count(logical=False)
        used = psutil.cpu_percent(interval=interval)

        if os.path.exists('/proc/cpuinfo'):
            c_tmp = jh.readFile('/proc/cpuinfo')
            d_tmp = re.findall("physical id.+", c_tmp)
            cpuLogicalNum = len(set(d_tmp))

        used_all = psutil.cpu_percent(percpu=True)
        cpu_name = jh.getCpuType() + " * {}".format(cpuLogicalNum)
        return used, cpuCount, used_all, cpu_name, cpuCount, cpuLogicalNum

    def getMemInfo(self):
        # 取内存信息
        mem = psutil.virtual_memory()
        if jh.getOs() == 'darwin':
            memInfo = {
                'memTotal': mem.total / 1024 / 1024
            }
            memInfo['memRealUsed'] = memInfo['memTotal'] * (mem.percent / 100)
        else:
            memInfo = {
                'memTotal': mem.total / 1024 / 1024,
                'memFree': mem.free / 1024 / 1024,
                'memBuffers': mem.buffers / 1024 / 1024,
                'memCached': mem.cached / 1024 / 1024
            }

            memInfo['memRealUsed'] = memInfo['memTotal'] - \
                memInfo['memFree'] - memInfo['memBuffers'] - \
                memInfo['memCached']
        return memInfo

    def getMemUsed(self):
        # 取内存使用率
        try:
            import psutil
            mem = psutil.virtual_memory()

            if jh.getOs() == 'darwin':
                return mem.percent

            memInfo = {'memTotal': mem.total / 1024 / 1024, 'memFree': mem.free / 1024 / 1024,
                       'memBuffers': mem.buffers / 1024 / 1024, 'memCached': mem.cached / 1024 / 1024}
            tmp = memInfo['memTotal'] - memInfo['memFree'] - \
                memInfo['memBuffers'] - memInfo['memCached']
            tmp1 = memInfo['memTotal'] / 100
            return (tmp / tmp1)
        except Exception as ex:
            return 1

    def getDiskInfo(self):
        info = self.getDiskInfo2()
        if len(info) != 0:
            return info

        # 取磁盘分区信息
        diskIo = psutil.disk_partitions()
        diskInfo = []

        for disk in diskIo:
            if disk[1] == '/mnt/cdrom':
                continue
            if disk[1] == '/boot':
                continue
            tmp = {}
            tmp['path'] = disk[1]
            size_tmp = psutil.disk_usage(disk[1])
            tmp['size'] = [jh.toSize(size_tmp[0]), jh.toSize(
                size_tmp[1]), jh.toSize(size_tmp[2]), str(size_tmp[3]) + '%']
            diskInfo.append(tmp)
        return diskInfo

    def getDiskInfo2(self):
        # 取磁盘分区信息
        temp = jh.execShell(
            "df -h -P|grep '/'|grep -v tmpfs | grep -v devfs")[0]
        tempInodes = jh.execShell(
            "df -i -P|grep '/'|grep -v tmpfs | grep -v devfs")[0]
        temp1 = temp.split('\n')
        tempInodes1 = tempInodes.split('\n')
        diskInfo = []
        n = 0
        cuts = ['/mnt/cdrom', '/boot', '/boot/efi', '/dev',
                '/dev/shm', '/zroot', '/run/lock', '/run', '/run/shm', '/run/user']
        for tmp in temp1:
            n += 1
            inodes = tempInodes1[n - 1].split()
            disk = tmp.split()
            if len(disk) < 5:
                continue
            if disk[1].find('M') != -1:
                continue
            if disk[1].find('K') != -1:
                continue
            if len(disk[5].split('/')) > 4:
                continue
            if disk[5] in cuts:
                continue
            arr = {}
            arr['path'] = disk[5]
            tmp1 = [disk[1], disk[2], disk[3], disk[4]]
            arr['size'] = tmp1
            arr['inodes'] = [inodes[1], inodes[2], inodes[3], inodes[4]]
            diskInfo.append(arr)
        return diskInfo

    # 清理系统垃圾
    def clearSystem(self, get):
        count = total = 0
        tmp_total, tmp_count = self.ClearMail()
        count += tmp_count
        total += tmp_total
        tmp_total, tmp_count = self.ClearOther()
        count += tmp_count
        total += tmp_total
        return count, total

    # 清理邮件日志
    def clearMail(self):
        rpath = '/var/spool'
        total = count = 0
        import shutil
        con = ['cron', 'anacron', 'mail']
        for d in os.listdir(rpath):
            if d in con:
                continue
            dpath = rpath + '/' + d
            time.sleep(0.2)
            num = size = 0
            for n in os.listdir(dpath):
                filename = dpath + '/' + n
                fsize = os.path.getsize(filename)
                size += fsize
                if os.path.isdir(filename):
                    shutil.rmtree(filename)
                else:
                    os.remove(filename)
                print('mail clear ok')
                num += 1
            total += size
            count += num
        return total, count

    # 清理其它
    def clearOther(self):
        clearPath = [
            {'path': '/www/server/jh-monitor', 'find': 'testDisk_'},
            {'path': '/www/wwwlogs', 'find': 'log'},
            {'path': '/tmp', 'find': 'panelBoot.pl'},
            {'path': '/www/server/jh-monitor/install', 'find': '.rpm'}
        ]

        total = count = 0
        for c in clearPath:
            for d in os.listdir(c['path']):
                if d.find(c['find']) == -1:
                    continue
                filename = c['path'] + '/' + d
                fsize = os.path.getsize(filename)
                total += fsize
                if os.path.isdir(filename):
                    shutil.rmtree(filename)
                else:
                    os.remove(filename)
                count += 1
        jh.restartWeb()
        os.system('echo > /tmp/panelBoot.pl')
        return total, count

    def psutilNetIoCounters(self):
        '''
        统计网卡流量
        '''
        stat_pl = 'data/only_netio_counters.pl'
        if os.path.exists(stat_pl):
            local_lo = (0, 0, 0, 0)
            ioName = psutil.net_io_counters(pernic=True).keys()
            for x in ioName:

                if x.find("lo") > -1:
                    local_lo = psutil.net_io_counters(
                        pernic=True).get(x)[:4]

            all_io = psutil.net_io_counters()[:4]
            result_io = tuple([all_io[i] - local_lo[i]
                               for i in range(0, len(all_io))])

            # print(local_lo)
            # print(all_io)
            # print(result_io)
            return result_io
        return psutil.net_io_counters()[:4]

    def getNetWork(self):
        # 取网络流量信息
        try:
            # 取网络流量信息
            networkIo = self.psutilNetIoCounters()
            if not "otime" in session:
                session['up'] = networkIo[0]
                session['down'] = networkIo[1]
                session['otime'] = time.time()

            ntime = time.time()
            networkInfo = {}
            networkInfo['upTotal'] = networkIo[0]
            networkInfo['downTotal'] = networkIo[1]
            networkInfo['up'] = round(float(
                networkIo[0] - session['up']) / 1024 / (ntime - session['otime']), 2)
            networkInfo['down'] = round(
                float(networkIo[1] - session['down']) / 1024 / (ntime - session['otime']), 2)
            networkInfo['downPackets'] = networkIo[3]
            networkInfo['upPackets'] = networkIo[2]

            # print networkIo[1], session['down'], ntime, session['otime']
            session['up'] = networkIo[0]
            session['down'] = networkIo[1]
            session['otime'] = time.time()

            networkInfo['cpu'] = self.getCpuInfo()
            networkInfo['load'] = self.getLoadAverage()
            networkInfo['mem'] = self.getMemInfo()

            return networkInfo
        except Exception as e:
            print("getNetWork error:", e)
            return None

    def getNetWorkIoData(self, start, end):
        # 取指定时间段的网络Io
        data = jh.M('network').dbfile('system').where("addtime>=? AND addtime<=?", (start, end)).field(
            'id,up,down,total_up,total_down,down_packets,up_packets,addtime').order('id asc').select()
        return self.toAddtime(data)

    def getDiskIoData(self, start, end):
        # 取指定时间段的磁盘Io
        data = jh.M('diskio').dbfile('system').where("addtime>=? AND addtime<=?", (start, end)).field(
            'id,read_count,write_count,read_bytes,write_bytes,read_time,write_time,addtime').order('id asc').select()
        return self.toAddtime(data)

    def getCpuIoData(self, start, end):
        # 取指定时间段的CpuIo
        data = jh.M('cpuio').dbfile('system').where("addtime>=? AND addtime<=?",
                                                    (start, end)).field('id,pro,mem,addtime').order('id asc').select()
        return self.toAddtime(data, True)

    def getLoadAverageData(self, start, end):
        data = jh.M('load_average').dbfile('system').where("addtime>=? AND addtime<=?", (
            start, end)).field('id,pro,one,five,fifteen,addtime').order('id asc').select()
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
                if isinstance(data[i], dict):
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

    def setControl(self, stype, day):

        control_file = 'data/control.conf'
        control_notify_pl = 'data/control_notify.pl'
        control_report_notify_pl = 'data/control_report_notify.pl'

        stat_pl = 'data/only_netio_counters.pl'

        if stype == '0':
            jh.execShell("rm -rf " + control_file)
        elif stype == '1':
            _day = int(day)
            if _day < 1:
                return jh.returnJson(False, "设置失败!")
            jh.writeFile(control_file, day)
        elif stype == '2':
            jh.execShell("rm -rf " + stat_pl)
        elif stype == '3':
            jh.execShell("echo 'True' > " + stat_pl)
        elif stype == '4':
            jh.execShell("rm -rf " + control_notify_pl)
        elif stype == '5':
            jh.execShell("echo 'True' > " + control_notify_pl)
        elif stype == 'del':
            if not jh.isRestart():
                return jh.returnJson(False, '请等待所有安装任务完成再执行')
            os.remove("data/system.db")

            sql = db.Sql().dbfile('system')
            csql = jh.readFile('data/sql/system.sql')
            csql_list = csql.split(';')
            for index in range(len(csql_list)):
                sql.execute(csql_list[index], ())
            return jh.returnJson(True, "监控服务已关闭")
        else:
            data = {}
            if os.path.exists(control_file):
                try:
                    data['day'] = int(jh.readFile(control_file))
                except:
                    data['day'] = 30
                data['status'] = True
            else:
                data['day'] = 30
                data['status'] = False
            
            if os.path.exists(control_notify_pl):
                data['notify_status'] = True
            else:
                data['notify_status'] = False

            if os.path.exists(control_report_notify_pl):
                data['report_notify_status'] = True
            else:
                data['report_notify_status'] = False

            if os.path.exists(stat_pl):
                data['stat_all_status'] = True
            else:
                data['stat_all_status'] = False

            return jh.getJson(data)

        return jh.returnJson(True, "设置成功!")

    def versionDiff(self, old, new):
        '''
            test 测试
            new 有新版本
            none 没有新版本
        '''
        new_list = new.split('.')
        if len(new_list) > 3:
            return 'test'

        old_list = old.split('.')
        ret = 'none'

        isHasNew = True
        if int(new_list[0]) == int(old_list[0]) and int(new_list[1]) == int(old_list[1]) and int(new_list[2]) == int(old_list[2]):
            isHasNew = False

        if isHasNew:
            return 'new'
        return ret

    def getServerInfo(self):
        import urllib.request
        import ssl
        upAddr = 'https://api.github.com/repos/jianghujs/jh-monitor/releases/latest'
        try:
            context = ssl._create_unverified_context()
            req = urllib.request.urlopen(upAddr, context=context, timeout=3)
            result = req.read().decode('utf-8')
            version = json.loads(result)
            return version
        except Exception as e:
            print('getServerInfo', e)
        return {}

    def updateServer(self, stype, version=''):
        # 更新服务
        try:
            if not jh.isRestart():
                return jh.returnJson(False, '请等待所有安装任务完成再执行!')

            version_new_info = self.getServerInfo()
            version_now = config_api.config_api().getVersion()

            new_ver = version_new_info['name']

            if stype == 'check':
                if not 'name' in version_new_info:
                    return jh.returnJson(False, '服务器数据或网络有问题!')

                diff = self.versionDiff(version_now, new_ver)
                if diff == 'new':
                    return jh.returnJson(True, '有新版本!', new_ver)
                elif diff == 'test':
                    return jh.returnJson(True, '有测试版本!', new_ver)
                else:
                    return jh.returnJson(False, '已经是最新,无需更新!')

            if stype == 'info':
                if not 'name' in version_new_info:
                    return jh.returnJson(False, '服务器数据有问题!')
                diff = self.versionDiff(version_now, new_ver)
                data = {}
                data['version'] = new_ver
                data['content'] = version_new_info[
                    'body'].replace("\n", "<br/>")
                return jh.returnJson(True, '更新信息!', data)

            if stype == 'update':
                if version == '':
                    return jh.returnJson(False, '缺少版本信息!')

                if new_ver != version:
                    return jh.returnJson(False, '更新失败,请重试!')

                toPath = jh.getRootDir() + '/temp'
                if not os.path.exists(toPath):
                    jh.execShell('mkdir -p ' + toPath)

                newUrl = "https://github.com/jianghujs/jh-monitor/archive/refs/tags/" + version + ".zip"

                dist_jh = toPath + '/jh.zip'
                if not os.path.exists(dist_jh):
                    jh.execShell(
                        'wget --no-check-certificate -O ' + dist_jh + ' ' + newUrl)

                dist_to = toPath + "/jh-monitor-" + version
                if not os.path.exists(dist_to):
                    os.system('unzip -o ' + toPath +
                              '/jh.zip' + ' -d ' + toPath)

                cmd_cp = 'cp -rf ' + toPath + '/jh-monitor-' + \
                    version + '/* ' + jh.getServerDir() + '/jh-monitor'
                jh.execShell(cmd_cp)

                jh.execShell('rm -rf ' + toPath + '/jh-monitor-' + version)
                jh.execShell('rm -rf ' + toPath + '/jh.zip')

                self.restartMw(True)
                return jh.returnJson(True, '安装更新成功!')

            return jh.returnJson(False, '已经是最新,无需更新!')
        except Exception as ex:
            # print('updateServer', ex)
            return jh.returnJson(False, "连接服务器失败!" + str(ex))

    # 修复面板
    def repPanel(self, get):
        vp = ''
        if jh.readFile('/www/server/jh-monitor/class/common.py').find('checkSafe') != -1:
            vp = '_pro'
        jh.ExecShell("wget -O update.sh " + jh.get_url() +
                     "/install/update" + vp + ".sh && bash update.sh")
        if hasattr(web.ctx.session, 'getCloudPlugin'):
            del(web.ctx.session['getCloudPlugin'])
        return True

    def getNotifyValueApi(self):
        control_notify_value_file = 'data/control_notify_value.conf'
        if not os.path.exists(control_notify_value_file):
            jh.writeFile(control_notify_value_file, '{}')
        config_data = json.loads(jh.readFile(control_notify_value_file))
        return jh.returnData(True, 'ok', config_data)

    def setNotifyValue(self, notify_value):
        cpu = notify_value.get('cpu', '')
        memory = notify_value.get('memory', '')
        disk = notify_value.get('disk', '')
        ssl_cert = notify_value.get('ssl_cert', '')
        mysql_slave_status_notice = notify_value.get('mysql_slave_status_notice', '')
        rsync_status_notice = notify_value.get('rsync_status_notice', '')

        control_notify_value_file = 'data/control_notify_value.conf'
        if not os.path.exists(control_notify_value_file):
            jh.writeFile(control_notify_value_file, '{}')
        config_data = json.loads(jh.readFile(control_notify_value_file))

        if cpu != '':
            config_data['cpu'] = int(cpu)
        if memory != '':
            config_data['memory'] = int(memory)
        if disk != '':
            config_data['disk'] = int(disk)
        if ssl_cert != '':
            config_data['ssl_cert'] = int(ssl_cert)
        if mysql_slave_status_notice != '':
            config_data['mysql_slave_status_notice'] = int(mysql_slave_status_notice)
        if rsync_status_notice != '':
            config_data['rsync_status_notice'] = int(rsync_status_notice)
        jh.writeFile(control_notify_value_file, json.dumps(config_data))
        return config_data
  

    def setNotifyValueApi(self):
        self.setNotifyValue(request.form)
        return jh.returnJson(True, '设置成功!')

    def getReportCycleApi(self):
        control_report_cycle_file = 'data/control_report_cycle.conf'
        if not os.path.exists(control_report_cycle_file):
            jh.writeFile(control_report_cycle_file, '{}')
        config_data = json.loads(jh.readFile(control_report_cycle_file))
        return jh.returnData(True, 'ok', config_data)
    

    def setReportCycleFileApi(self):
        field_type = request.form.get('type', '')
        week = request.form.get('week', '')
        where1 = request.form.get('where1', '')
        hour = request.form.get('hour', '')
        minute = request.form.get('minute', '')
        
        params = {
            'type': field_type,
            'week': week,
            'where1': where1,
            'hour': hour,
            'minute': minute
        }
        
        control_report_cycle_file = 'data/control_report_cycle.conf'

        jh.writeFile(control_report_cycle_file, json.dumps(params))

        return jh.returnJson(True, '设置成功!')
