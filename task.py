# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
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
from colorama import init, Fore, Style

# 初始化 colorama
init(autoreset=True)

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
def restartPanel():
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
            print(f"{Fore.BLUE}★ ========= [clientTask] STARTED -  开始时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(addtime))}{Style.RESET_ALL}")
            # 预备主机数据
            hostM = jh.M('view01_host')
            host_list = hostM.field(h_api.host_field).select()

            # 执行脚本
            script_list = ['get_host_info.py', 'get_host_usage.py', 'get_panel_backup_report.py']
            batch_result = run_script_batch(script_list)

            # 循环主机列表获取状态
            for host in host_list:
                ip = host['ip']
                host_detail = {
                    'host_id': host['host_id'],
                    'host_name': host['host_name'],
                    'host_status': 'Stopped',
                    'uptime': '',
                    'host_info': '{}',
                    'cpu_info': '{}',
                    'mem_info': '{}',
                    'disk_info': '{}',
                    'net_info': '{}',
                    'load_avg': '{}',
                    'firewall_info': {},
                    'addtime': addtime
                }
                if batch_result.get(ip, None) is not None:
                    ip_batch_result = batch_result[ip]
                    if ip_batch_result:
                        if ip_batch_result['status'] == 'ok':
                            data = ip_batch_result.get('data', {}) 
                            uptime = data.get('uptime', '')
                            host_info = data.get('get_host_info.py', {})
                            host_usage = data.get('get_host_usage.py', {})
                            cpu_info = host_usage.get('cpu_info', {})
                            mem_info = host_usage.get('mem_info', {})
                            disk_info = host_usage.get('disk_info', [])
                            net_info = host_usage.get('net_info', [])
                            load_avg = host_usage.get('load_avg', {})
                            firewall_info = host_usage.get('firewall_info', {})
                            backup_info = data.get('get_panel_backup_report.py', [])
                            
                            host_detail.update({
                                'host_status': 'Running',
                                'uptime': uptime,
                                'host_info': json.dumps(host_info),
                                'cpu_info': json.dumps(cpu_info),
                                'mem_info': json.dumps(mem_info),
                                'disk_info': json.dumps(disk_info),
                                'net_info': json.dumps(net_info),
                                'load_avg': json.dumps(load_avg),
                                'firewall_info': json.dumps(firewall_info),
                                'backup_info': json.dumps(backup_info),
                                'addtime': addtime
                            })

                print("！！！！！！！！！！", host_detail)

                host_detail_keys = ','.join(list(host_detail.keys()))
                host_detail_values = tuple(host_detail.values())

                sql.table('host_detail').add(host_detail_keys, host_detail_values)
                sql.table('host_detail').where("addtime<?", (deltime,)).delete()

            endtime = int(time.time())
          
            print(f"{Fore.GREEN}★ ========= [clientTask] SUCCESS - 完成时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(endtime))} 用时: {str(endtime - addtime) + 's'} {Style.RESET_ALL}")
          
            time.sleep(5)
            count += 1
            del(batch_result)

    except Exception as ex:
        traceback.print_exc()
        jh.writeFile('logs/sys_interrupt.pl', str(ex))
        print(f"{Fore.RED}★ ========= [clientTask] ERROR：{str(ex)} {Style.RESET_ALL}")
    
        notify_msg = jh.generateCommonNotifyMessage("客户端监控异常：" + str(ex))
        jh.notifyMessage(title='客户端异常通知', msg=notify_msg, stype='客户端监控', trigger_time=3600)

        restartPanel()

        time.sleep(30)
        clientTask()

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
