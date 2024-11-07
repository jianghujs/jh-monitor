# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 计划任务
# ---------------------------------------------------------------------------------

import sys
import os
import json
import time
import threading
import psutil
import traceback
import ansible_runner

if sys.version_info[0] == 2:
    reload(sys)
    sys.setdefaultencoding('utf-8')


sys.path.append(os.getcwd() + "/class/core")
import jh
import db
sys.path.append(os.getcwd() + "/scripts/client")
from run_script_batch import run_script_batch

# print sys.path

# cmd = 'ls /usr/local/lib/ | grep python  | cut -d \\  -f 1 | awk \'END {print}\''
# info = jh.execShell(cmd)
# p = "/usr/local/lib/" + info[0].strip() + "/site-packages"
# sys.path.append(p)


global pre, timeoutCount, logPath, isTask, oldEdate, isCheck
pre = 0
timeoutCount = 0
isCheck = 0
oldEdate = None

logPath = os.getcwd() + '/tmp/panelExec.log'
isTask = os.getcwd() + '/tmp/panelTask.pl'

if not os.path.exists(os.getcwd() + "/tmp"):
    os.system('mkdir -p ' + os.getcwd() + "/tmp")

if not os.path.exists(logPath):
    os.system("touch " + logPath)


def service_cmd(method):
    cmd = '/etc/init.d/jhm'
    if os.path.exists(cmd):
        execShell(cmd + ' ' + method)
        return

    cmd = jh.getRunDir() + '/scripts/init.d/jhm'
    if os.path.exists(cmd):
        execShell(cmd + ' ' + method)
        return


def jh_async(f):
    def wrapper(*args, **kwargs):
        thr = threading.Thread(target=f, args=args, kwargs=kwargs)
        thr.start()
    return wrapper


@jh_async
def restartMw():
    time.sleep(1)
    cmd = jh.getRunDir() + '/scripts/init.d/jhm reload &'
    jh.execShell(cmd)


def execShell(cmdstring, cwd=None, timeout=None, shell=True):
    try:
        global logPath
        import shlex
        import datetime
        import subprocess

        if timeout:
            end_time = datetime.datetime.now() + datetime.timedelta(seconds=timeout)

        cmd = cmdstring + ' > ' + logPath + ' 2>&1'
        sub = subprocess.Popen(
            cmd, cwd=cwd, stdin=subprocess.PIPE, shell=shell, bufsize=4096)
        while sub.poll() is None:
            time.sleep(0.1)

        data = sub.communicate()
        # python3 fix 返回byte数据
        if isinstance(data[0], bytes):
            t1 = str(data[0], encoding='utf-8')

        if isinstance(data[1], bytes):
            t2 = str(data[1], encoding='utf-8')
        # jh.writeFile('/root/1.txt', '执行成功:' + str(t1 + t2))
        return True
    except Exception as e:
        # jh.writeFile('/root/1.txt', '执行失败:' + str(e))
        return False


def downloadFile(url, filename):
    # 下载文件
    try:
        import urllib
        import socket
        socket.setdefaulttimeout(300)

        headers = (
            'User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36')
        opener = urllib.request.build_opener()
        opener.addheaders = [headers]
        urllib.request.install_opener(opener)

        urllib.request.urlretrieve(
            url, filename=filename, reporthook=downloadHook)

        if not jh.isAppleSystem():
            os.system('chown www.www ' + filename)

        writeLogs('done')
    except Exception as e:
        writeLogs(str(e))


def downloadHook(count, blockSize, totalSize):
    # 下载文件进度回调
    global pre
    used = count * blockSize
    pre1 = int((100.0 * used / totalSize))
    if pre == (100 - pre1):
        return
    speed = {'total': totalSize, 'used': used, 'pre': pre1}
    writeLogs(json.dumps(speed))


def writeLogs(logMsg):
    # 写输出日志
    try:
        global logPath
        fp = open(logPath, 'w+')
        fp.write(logMsg)
        fp.close()
    except:
        pass


def runTask():
    global isTask
    try:
        if os.path.exists(isTask):
            sql = db.Sql()
            sql.table('tasks').where(
                "status=?", ('-1',)).setField('status', '0')
            taskArr = sql.table('tasks').where("status=?", ('0',)).field(
                'id,type,execstr').order("id asc").select()
            for value in taskArr:
                start = int(time.time())
                if not sql.table('tasks').where("id=?", (value['id'],)).count():
                    continue
                sql.table('tasks').where("id=?", (value['id'],)).save(
                    'status,start', ('-1', start))
                if value['type'] == 'download':
                    argv = value['execstr'].split('|jh|')
                    downloadFile(argv[0], argv[1])
                elif value['type'] == 'execshell':
                    execStatus = execShell(value['execstr'])
                end = int(time.time())
                sql.table('tasks').where("id=?", (value['id'],)).save(
                    'status,end', ('1', end))

                if(sql.table('tasks').where("status=?", ('0')).count() < 1):
                    os.system('rm -f ' + isTask)

            sql.close()
    except Exception as e:
        print(str(e))

    # 站点过期检查
    siteEdate()


def startTask():
    # 任务队列
    try:
        while True:
            runTask()
            time.sleep(2)
    except Exception as e:
        time.sleep(60)
        startTask()


def siteEdate():
    # 网站到期处理
    global oldEdate
    try:
        if not oldEdate:
            oldEdate = jh.readFile('data/edate.pl')
        if not oldEdate:
            oldEdate = '0000-00-00'
        mEdate = time.strftime('%Y-%m-%d', time.localtime())
        if oldEdate == mEdate:
            return False
        edateSites = jh.M('sites').where('edate>? AND edate<? AND (status=? OR status=?)',
                                         ('0000-00-00', mEdate, 1, '正在运行')).field('id,name').select()
        import site_api
        for site in edateSites:
            site_api.site_api().stop(site['id'], site['name'])
        oldEdate = mEdate
        jh.writeFile('data/edate.pl', mEdate)
    except Exception as e:
        print(str(e))


def clientTask():
    # 系统监控任务
    try:
        import host_api
        h_api = host_api.host_api()
        sql = db.Sql()
        count = 0
        filename = 'data/control.conf'
        
        while True:
            # 预备主机数据
            hostM = jh.M('view01_host')
            host_list = hostM.field(h_api.host_field).select()
            print('host_list', host_list)
            
            # 获取配置的保留天数
            day = 30
            # try:
            #     day = int(jh.readFile(filename))
            #     if day < 1:
            #         time.sleep(10)
            #         continue
            # except:
            #     day = 30
            addtime = int(time.time())
            deltime = addtime - (day * 86400)

            # 执行脚本
            script_list = ['get_host_info.py', 'get_host_usage.py']
            batch_result = run_script_batch(script_list)

            # 填充执行结果
            for r in batch_result:
                ip = r['ip']
                data = r['data']

                if ip is not None and data is not None:
                    host_info = data.get('get_host_info.py', {})
                    host_usage = data.get('get_host_usage.py', {})
                    cpu_info = host_usage.get('cpu_info', {})
                    mem_info = host_usage.get('mem_info', {})
                    disk_info = host_usage.get('disk_info', [])
                    net_info = host_usage.get('net_info', [])
                    load_avg = host_usage.get('load_avg', {})
                    firewall_info = host_usage.get('firewall_info', {})

                    print('ip', ip)
                    # 从host_list找到ip匹配的host
                    host_data = [h for h in host_list if h.get('ip') == ip]
                    if len(host_data) == 0:
                        print("未匹配到主机")
                        continue
                    host = host_data[0]
                    print('host', host)
                    
                    # INSERT INTO `host_detail` (host_id, host_name, host_status, uptime, host_info, cpu_info, mem_info, disk_info, net_info, load_avg, firewall_info, port_info, backup_info, temperature_info, ssh_user_list, last_update, addtime) VALUES
                    # ('H00001', 'Host1', 'Running', '15 days', '{"hostName":"debian","kernelArch":"x86_64","kernelVersion":"5.10.0-23-amd64","os":"linux","platform":"debian","platformFamily":"debian","platformVersion":"11.6","procs":97,"upTime":14472}', '{"logicalCores":2,"modelName":"Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz","percent":4.15}', '{"total":4109926400,"free":3076767744,"used":467066880,"usedPercent":11.36,"buffers":65052672,"cached":501039104,"swapFree":1022357504,"swapTotal":1022357504,"swapUsed":0,"swapUsedPercent":0}', '[{"total":19947929600,"free":15416078336,"used":3492610048,"usedPercent":18.47,"fstype":"ext4","ioPercent":0,"ioTime":139824,"iops":0,"mountpoint":"/","name":"/dev/sda1"}]', '[{"name":"enp0s3","recv":145488948,"recv_per_second":1612,"sent":32678885,"sent_per_second":90}]', '{"1min":0.15,"5min":0.10,"15min":0.05}', '{"is_running":true,"rules":[{"access":"ACCEPT","protocol":"tcp","release_port":"22","source":"anywhere"},{"access":"ACCEPT","protocol":"tcp","release_port":"806","source":"anywhere"}],"rule_change":{"add":null,"del":null}}', '{"2129988847542649187":{"ip":"0.0.0.0","port":22,"protocol":"tcp","pne_id":-7672102068318330115},"6588906985071447406":{"ip":"127.0.0.1","port":37177,"protocol":"tcp","pne_id":-4512644645752656383},"6677558488157980451":{"ip":"::","port":806,"protocol":"tcp","pne_id":-7910089643010597800},"344772759478166149":{"ip":"::","port":22,"protocol":"tcp","pne_id":-7672102068318330115}}', '{}', '{}', '[]', '2023-10-03 12:00:00', '2023-10-01 12:00:00'),
                    # ('H00002', 'Host2', 'Running', '20 days', '{"hostName":"debian","kernelArch":"x86_64","kernelVersion":"5.10.0-23-amd64","os":"linux","platform":"debian","platformFamily":"debian","platformVersion":"11.6","procs":97,"upTime":14472}', '{"logicalCores":2,"modelName":"Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz","percent":4.15}', '{"total":4109926400,"free":3076767744,"used":467066880,"usedPercent":11.36,"buffers":65052672,"cached":501039104,"swapFree":1022357504,"swapTotal":1022357504,"swapUsed":0,"swapUsedPercent":0}', '[{"total":19947929600,"free":15416078336,"used":3492610048,"usedPercent":18.47,"fstype":"ext4","ioPercent":0,"ioTime":139824,"iops":0,"mountpoint":"/","name":"/dev/sda1"}]', '[{"name":"enp0s3","recv":145488948,"recv_per_second":1612,"sent":32678885,"sent_per_second":90}]', '{"1min":0.15,"5min":0.10,"15min":0.05}', '{"is_running":true,"rules":[{"access":"ACCEPT","protocol":"tcp","release_port":"22","source":"anywhere"},{"access":"ACCEPT","protocol":"tcp","release_port":"806","source":"anywhere"}],"rule_change":{"add":null,"del":null}}', '{"2129988847542649187":{"ip":"0.0.0.0","port":22,"protocol":"tcp","pne_id":-7672102068318330115},"6588906985071447406":{"ip":"127.0.0.1","port":37177,"protocol":"tcp","pne_id":-4512644645752656383},"6677558488157980451":{"ip":"::","port":806,"protocol":"tcp","pne_id":-7910089643010597800},"344772759478166149":{"ip":"::","port":22,"protocol":"tcp","pne_id":-7672102068318330115}}', '{}', '{}', '[]', '2023-10-03 12:00:00', '2023-10-01 12:00:00'),
                    # ('H00003', 'Host3', 'Stopped', '5 days', '{"hostName":"debian","kernelArch":"x86_64","kernelVersion":"5.10.0-23-amd64","os":"linux","platform":"debian","platformFamily":"debian","platformVersion":"11.6","procs":97,"upTime":14472}', '{"logicalCores":2,"modelName":"Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz","percent":4.15}', '{"total":4109926400,"free":3076767744,"used":467066880,"usedPercent":11.36,"buffers":65052672,"cached":501039104,"swapFree":1022357504,"swapTotal":1022357504,"swapUsed":0,"swapUsedPercent":0}', '[{"total":19947929600,"free":15416078336,"used":3492610048,"usedPercent":18.47,"fstype":"ext4","ioPercent":0,"ioTime":139824,"iops":0,"mountpoint":"/","name":"/dev/sda1"}]', '[{"name":"enp0s3","recv":145488948,"recv_per_second":1612,"sent":32678885,"sent_per_second":90}]', '{"1min":0.15,"5min":0.10,"15min":0.05}', '{"is_running":true,"rules":[{"access":"ACCEPT","protocol":"tcp","release_port":"22","source":"anywhere"},{"access":"ACCEPT","protocol":"tcp","release_port":"806","source":"anywhere"}],"rule_change":{"add":null,"del":null}}', '{"2129988847542649187":{"ip":"0.0.0.0","port":22,"protocol":"tcp","pne_id":-7672102068318330115},"6588906985071447406":{"ip":"127.0.0.1","port":37177,"protocol":"tcp","pne_id":-4512644645752656383},"6677558488157980451":{"ip":"::","port":806,"protocol":"tcp","pne_id":-7910089643010597800},"344772759478166149":{"ip":"::","port":22,"protocol":"tcp","pne_id":-7672102068318330115}}', '{}', '{}', '[]', '2023-10-03 12:00:00', '2023-10-01 12:00:00');


                    host_detail = {
                        'host_id': host['host_id'],
                        'host_name': host['host_name'],
                        'host_status': 'Running',
                        'uptime': data.get('uptime', ''),
                        'host_info': json.dumps(host_info),
                        'cpu_info': json.dumps(cpu_info),
                        'mem_info': json.dumps(mem_info),
                        'disk_info': json.dumps(disk_info),
                        'net_info': json.dumps(net_info),
                        'load_avg': json.dumps(load_avg),
                        'firewall_info': json.dumps(firewall_info),
                        'addtime': addtime
                    }
                    # 获取host_detail的所有key用,分割的字符串
                    host_detail_keys = ','.join(list(host_detail.keys()))
                    print(host_detail_keys)
                    # 获取host_detail的所有value用,分割的字符串
                    host_detail_values = tuple(host_detail.values())
                    print(host_detail_values)

                    sql.table('host_detail').add(host_detail_keys, host_detail_values)
                    sql.table('host_detail').where("addtime<?", (deltime,)).delete()

                

            time.sleep(5)
            count += 1
            continue
            run_result = run_script('get_host_info.py')
            print('run_result', run_result)
            time.sleep(5)
            count += 1
            continue


            if not os.path.exists(filename):
                time.sleep(10)
                continue

            day = 30
            try:
                day = int(jh.readFile(filename))
                if day < 1:
                    time.sleep(10)
                    continue
            except:
                day = 30

            tmp = {}
            # 取当前CPU Io
            tmp['used'] = psutil.cpu_percent(interval=1)

            if not cpuInfo:
                tmp['mem'] = sm.getMemUsed()
                cpuInfo = tmp

            # TODO 不太理解，这里如果出现cpuInfo未清理的情况下会导致cpu信息一直停留在高位
            if cpuInfo['used'] < tmp['used']:
                tmp['mem'] = sm.getMemUsed()
                cpuInfo = tmp

            # 取当前网络Io
            networkIo = sm.psutilNetIoCounters()
            if not network_up:
                network_up = networkIo[0]
                network_down = networkIo[1]
            tmp = {}
            tmp['upTotal'] = networkIo[0]
            tmp['downTotal'] = networkIo[1]
            tmp['up'] = round(float((networkIo[0] - network_up) / 1024), 2)
            tmp['down'] = round(float((networkIo[1] - network_down) / 1024), 2)
            tmp['downPackets'] = networkIo[3]
            tmp['upPackets'] = networkIo[2]

            network_up = networkIo[0]
            network_down = networkIo[1]

            if not networkInfo:
                networkInfo = tmp
            if (tmp['up'] + tmp['down']) > (networkInfo['up'] + networkInfo['down']):
                networkInfo = tmp
            # 取磁盘Io
            # if os.path.exists('/proc/diskstats'):
            diskio_2 = psutil.disk_io_counters()
            if not diskio_1:
                diskio_1 = diskio_2
            tmp = {}
            tmp['read_count'] = diskio_2.read_count - diskio_1.read_count
            tmp['write_count'] = diskio_2.write_count - diskio_1.write_count
            tmp['read_bytes'] = diskio_2.read_bytes - diskio_1.read_bytes
            tmp['write_bytes'] = diskio_2.write_bytes - diskio_1.write_bytes
            tmp['read_time'] = diskio_2.read_time - diskio_1.read_time
            tmp['write_time'] = diskio_2.write_time - diskio_1.write_time

            if not diskInfo:
                diskInfo = tmp
            else:
                diskInfo['read_count'] += tmp['read_count']
                diskInfo['write_count'] += tmp['write_count']
                diskInfo['read_bytes'] += tmp['read_bytes']
                diskInfo['write_bytes'] += tmp['write_bytes']
                diskInfo['read_time'] += tmp['read_time']
                diskInfo['write_time'] += tmp['write_time']
            diskio_1 = diskio_2
            diskInfo['disk_list'] = sm.getDiskInfo()

            # 网站
            siteInfo = sm.getSiteInfo()
            
            # mysql
            mysqlInfo = sm.getMysqlInfo()
            # 报告
            jh.generateMonitorReportAndNotify(cpuInfo, networkInfo, diskInfo, siteInfo, mysqlInfo)
            
            # print diskInfo
            if count >= 12:
                try:
                    addtime = int(time.time())
                    deltime = addtime - (day * 86400)

                    data = (cpuInfo['used'], cpuInfo['mem'], addtime)
                    sql.table('cpuio').add('pro,mem,addtime', data)
                    sql.table('cpuio').where("addtime<?", (deltime,)).delete()

                    data = (networkInfo['up'] / 5, networkInfo['down'] / 5, networkInfo['upTotal'], networkInfo[
                        'downTotal'], networkInfo['downPackets'], networkInfo['upPackets'], addtime)
                    sql.table('network').add(
                        'up,down,total_up,total_down,down_packets,up_packets,addtime', data)
                    sql.table('network').where(
                        "addtime<?", (deltime,)).delete()
                    # if os.path.exists('/proc/diskstats'):
                    data = (diskInfo['read_count'], diskInfo['write_count'], diskInfo['read_bytes'], diskInfo[
                        'write_bytes'], diskInfo['read_time'], diskInfo['write_time'], addtime)
                    sql.table('diskio').add(
                        'read_count,write_count,read_bytes,write_bytes,read_time,write_time,addtime', data)
                    sql.table('diskio').where(
                        "addtime<?", (deltime,)).delete()
                   
                    # LoadAverage
                    load_average = sm.getLoadAverage()
                    lpro = round(
                        (load_average['one'] / load_average['max']) * 100, 2)
                    if lpro > 100:
                        lpro = 100
                    sql.table('load_average').add('pro,one,five,fifteen,addtime', (lpro, load_average[
                        'one'], load_average['five'], load_average['fifteen'], addtime))

                    # Database
                    mysql_write_lock_data_key = 'MySQL信息写入面板数据库任务'
                    if not jh.checkLockValid(mysql_write_lock_data_key, 'day_start'):
                        mysqlInfo = sm.getMysqlInfo()
                        database_list = mysqlInfo.get('database_list', [])
                        sql.table('database').add('total_size,total_bytes,list,addtime', (
                            mysqlInfo.get('total_size', 0),
                            mysqlInfo.get('total_tytes', 0),
                            json.dumps(mysqlInfo.get('database_list', [])),
                            addtime
                        ))
                        sql.table('database').where(
                            "addtime<?", (deltime,)).delete()
                        jh.updateLockData(mysql_write_lock_data_key)

                    lpro = None
                    load_average = None
                    cpuInfo = None
                    networkInfo = None
                    diskInfo = None
                    count = 0
                    reloadNum += 1
                    if reloadNum > 1440:
                        reloadNum = 0
                        jh.writeFile('logs/sys_interrupt.pl',
                                     "reload num:" + str(reloadNum))
                        restartMw()
                except Exception as ex:
                    lpro = None
                    load_average = None
                    cpuInfo = None
                    networkInfo = None
                    diskInfo = None
                    print(str(ex))
                    jh.writeFile('logs/sys_interrupt.pl', str(ex))

            del(tmp)
            time.sleep(5)
            count += 1
    except Exception as ex:
        traceback.print_exc()
        print(str(ex))
        jh.writeFile('logs/sys_interrupt.pl', str(ex))
        
        notify_msg = jh.generateCommonNotifyMessage("服务器监控异常：" + str(ex))
        jh.notifyMessage(title='服务器异常通知', msg=notify_msg, stype='服务器监控', trigger_time=3600)

        restartMw()

        time.sleep(30)
        systemTask()

# --------------------------------------Panel Restart Start   --------------------------------------------- #
def restartService():
    restartTip = 'data/restart.pl'
    while True:
        if os.path.exists(restartTip):
            os.remove(restartTip)
            service_cmd('restart')
        time.sleep(1)

def restartPanelService():
    restartPanelTip = 'data/restart_panel.pl'
    while True:
        if os.path.exists(restartPanelTip):
            os.remove(restartPanelTip)
            service_cmd('restart_panel')
        time.sleep(1)
# --------------------------------------Panel Restart End   --------------------------------------------- #


# --------------------------------------Debounce Commands Start   --------------------------------------------- #
debounce_commands_pool_file = 'data/debounce_commands_pool.json'
def read_debounce_commands_pool():
    if not os.path.exists(debounce_commands_pool_file):
        write_debounce_commands_pool([])
        return []
    try:
        with open(debounce_commands_pool_file, 'r') as file:
            return json.load(file)
    except:
        # 往文件写入[]
        write_debounce_commands_pool([])
        return []
    
def write_debounce_commands_pool(debounce_commands_pool):
    with open(debounce_commands_pool_file, 'w') as file:
        json.dump(debounce_commands_pool, file)

def debounceCommandsService():
    while True:
      if not os.path.exists(debounce_commands_pool_file):
        write_debounce_commands_pool([])
      # 倒计时并执行命令
      debounce_commands_pool = read_debounce_commands_pool()
      debounce_commands_to_remove = []
      for debounce_commands_info in debounce_commands_pool:
        debounce_commands_info['seconds_to_run'] -= 1
        if debounce_commands_info['seconds_to_run'] < 0:
          command = debounce_commands_info.get('command', '')
          debounce_commands_to_remove.append(debounce_commands_info)
          if command:
            jh.execShell(command)
      # 删除已经执行的命令
      for debounce_commands_info in debounce_commands_to_remove:
        debounce_commands_pool.remove(debounce_commands_info)
      # 写回文件
      write_debounce_commands_pool(debounce_commands_pool)
      time.sleep(1)

# --------------------------------------Debounce Commands End   --------------------------------------------- #


def setDaemon(t):
    if sys.version_info.major == 3 and sys.version_info.minor >= 10:
        t.daemon = True
    else:
        t.setDaemon(True)
    return t


    
if __name__ == "__main__":
   
    # client监控
    ct = threading.Thread(target=clientTask)
    ct = setDaemon(ct)
    ct.start()

    # Panel Restart Start
    rps = threading.Thread(target=restartPanelService)
    rps = setDaemon(rps)
    rps.start()

    # Restart Start
    rs = threading.Thread(target=restartService)
    rs = setDaemon(rs)
    rs.start()

    # Debounce Commands
    dcs = threading.Thread(target=debounceCommandsService)
    dcs = setDaemon(dcs)
    dcs.start()



    startTask()
