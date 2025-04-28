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
            script_list = [
                'get_host_info.py', 
                'get_host_usage.py', 
                # 'get_panel_backup_report.py'
            ]
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
                            # backup_info = data.get('get_panel_backup_report.py', [])
                            
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
                                # 'backup_info': json.dumps(backup_info),
                                'addtime': addtime
                            })

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


def hostGrowthAlarmTask():
    """资源增长预测和告警"""
    try:
        sql = db.Sql()
        last_alarm_times = {}  # 记录最后告警时间，格式为 {host_id}_{resource_type}: timestamp
        
        while True:
            # 读取配置
            config = jh.getGrowthAlarmConfig()
            scan_interval = config.get('scan_interval', 5)
            scan_history_minutes = config.get('scan_history_minutes', 5)
            warning_threshold = config.get('warning_threshold', 80)
            prediction_critical_hours = config.get('prediction_critical_hours', 72)
            prediction_warning_hours = config.get('prediction_warning_hours', 168)
            notify_critical_interval = config.get('notify_critical_interval', 3600)
            notify_warning_interval = config.get('notify_warning_interval', 7200)
            
            current_time = int(time.time())

            
            print(f"{Fore.BLUE}★ ========= [resourceGrowthAlarm] STARTED - 开始分析资源增长: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))}{Style.RESET_ALL}")
            
            # 获取主机列表
            host_list = jh.M('view01_host').field('host_id,host_name').select()
            
            for host in host_list:
                if host['host_id'] != 'test_host_001':
                    continue

                host_id = host['host_id']
                host_name = host['host_name']
                
                # 获取历史数据进行分析（最近X分钟的数据）
                history_start = current_time - (scan_history_minutes * 60)

                # 获取最新一条记录和历史记录
                latest_record = sql.table('host_detail').where('host_id=? AND host_status=?', 
                                    (host_id, 'Running')).order('id desc').field('id,mem_info,disk_info,addtime').find()

                # 如果没有最新记录，则跳过
                if not latest_record:
                    continue
                
                # 获取历史记录
                old_record = sql.table('host_detail').where('host_id=? AND host_status=? AND addtime<?', 
                                    (host_id, 'Running', history_start)).order('id desc').field('id,mem_info,disk_info,addtime').find()
                
                # 如果没有足够的历史记录，则跳过
                if not old_record:
                    continue
                
                # 分析内存增长
                try:
                    latest_mem_info = json.loads(latest_record['mem_info'])
                    old_mem_info = json.loads(old_record['mem_info'])
                    
                    if 'usedPercent' in latest_mem_info and 'usedPercent' in old_mem_info:
                        latest_used_percent = float(latest_mem_info['usedPercent'])
                        old_used_percent = float(old_mem_info['usedPercent'])
                        
                        # 计算增长率和预测
                        growth_percentage = latest_used_percent - old_used_percent
                        time_diff_hours = (float(latest_record['addtime']) - float(old_record['addtime'])) / 3600
                        
                        if time_diff_hours > 0:
                            growth_rate_per_hour = growth_percentage / time_diff_hours
                            # 如果增长率为正，预测何时达到警戒线
                            if growth_rate_per_hour > 0:
                                hours_to_threshold = (warning_threshold - latest_used_percent) / growth_rate_per_hour
                                days_to_threshold = hours_to_threshold / 24

                                # 根据预计到达阈值的时间设置告警级别
                                prediction_level = None
                                if hours_to_threshold <= prediction_critical_hours: 
                                    prediction_level = 'critical'
                                    notify_interval = notify_critical_interval
                                elif hours_to_threshold <= prediction_warning_hours: 
                                    prediction_level = 'warning'
                                    notify_interval = notify_warning_interval

                                if prediction_level:
                                    # 从host_alarm表获取最后一条告警记录
                                    alarm_key = f"{host_id}_memory"
                                    last_alarm = sql.table('host_alarm').where('host_id=? AND alarm_type=?', 
                                        (host_id, '资源增长预警')).order('id desc').field('addtime').find()
                                    last_alarm_time = int(time.mktime(time.strptime(last_alarm['addtime'], '%Y-%m-%d %H:%M:%S'))) if last_alarm else 0
                                    
                                    if (current_time - last_alarm_time) >= notify_interval:
                                        # 生成告警内容
                                        alarm_level_map = {
                                            'critical': '紧急',
                                            'warning': '警告'
                                        }

                                        alarm_color = {
                                            'critical': '#d9534f',
                                            'warning': '#f0ad4e'
                                        }
                                        
                                        alarm_content = f"""
<div style="font-family: Arial, sans-serif; padding: 15px; margin-top: 10px;border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9;">
    <h3 style="color: {alarm_color[prediction_level]}; margin-top: 10px;">内存使用率增长过快</h3>
    <ul style="list-style-type: none; padding-left: 0;">
        <li style="margin-bottom: 8px;"><strong>告警级别:</strong> <span style="color: {alarm_color[prediction_level]};">{alarm_level_map[prediction_level]}</span></li>
        <li style="margin-bottom: 8px;"><strong>过去{scan_history_minutes}分钟已增长:</strong> <span style="color: {alarm_color[prediction_level]};">{growth_percentage:.2f}%</span></li>
        <li style="margin-bottom: 8px;"><strong>当前使用率:</strong> <span style="color: {alarm_color[prediction_level]};">{latest_used_percent:.2f}%</span></li>
        <li style="margin-bottom: 8px;"><strong>预计每小时增长:</strong> <span style="color: {alarm_color[prediction_level]};">{growth_rate_per_hour:.2f}%</span></li>
        <li style="margin-bottom: 8px;"><strong>预计达到警戒线（{warning_threshold}%）时间:</strong> <span style="color: {alarm_color[prediction_level]};">{days_to_threshold:.1f} 天后（{hours_to_threshold:.1f} 小时后）</span></li>
    </ul>
</div>
                                        """
                                        
                                        # 添加告警记录
                                        sql.table('host_alarm').add(
                                            'host_id,host_name,alarm_type,alarm_level,alarm_content,addtime',
                                            (host_id, host_name, '资源增长预警', alarm_level_map[prediction_level], alarm_content, time.strftime('%Y-%m-%d %H:%M:%S'))
                                        )
                                        # print(f"添加告警记录: {res}")
                                        print(f"添加告警记录: {host_id}, {host_name}, 资源增长预警, {alarm_level_map[prediction_level]}, {alarm_content}, {time.strftime('%Y-%m-%d %H:%M:%S')}")
                                        
                                        # 发送通知消息
                                        notify_msg = jh.generateCommonNotifyMessage(f"主机 [{host_name}] {alarm_content}")
                                        jh.notifyMessage(
                                            title=f'资源增长预警-{alarm_level_map[prediction_level]}', 
                                            msg=notify_msg, 
                                            msgtype='html',
                                            stype='资源增长预警', 
                                            trigger_time=0
                                        )
                except Exception as e:
                    print(f"分析内存数据出错: {str(e)}")
                
                # 分析磁盘增长
                # try:
                #     latest_disk_info = json.loads(latest_record['disk_info'])
                #     old_disk_info = json.loads(old_record['disk_info'])
                    
                #     # 按挂载点整理磁盘信息
                #     latest_disk_by_mount = {disk.get('mountpoint'): disk for disk in latest_disk_info if 'mountpoint' in disk and 'usedPercent' in disk}
                #     old_disk_by_mount = {disk.get('mountpoint'): disk for disk in old_disk_info if 'mountpoint' in disk and 'usedPercent' in disk}
                    
                #     # 对每个挂载点进行分析
                #     for mountpoint in latest_disk_by_mount:
                #         if mountpoint in old_disk_by_mount:
                #             latest_used_percent = float(latest_disk_by_mount[mountpoint]['usedPercent'])
                #             old_used_percent = float(old_disk_by_mount[mountpoint]['usedPercent'])
                            
                #             # 计算增长率和预测
                #             growth_percentage = latest_used_percent - old_used_percent
                #             time_diff_hours = (float(latest_record['addtime']) - float(old_record['addtime'])) / 3600
                            
                #             if time_diff_hours > 0:
                #                 growth_rate_per_hour = growth_percentage / time_diff_hours
                                
                #                 # 如果增长率为正，预测何时达到警戒线
                #                 if growth_rate_per_hour > 0:
                #                     hours_to_threshold = (warning_threshold - latest_used_percent) / growth_rate_per_hour
                #                     days_to_threshold = hours_to_threshold / 24
                                    
                #                     # 根据预计到达阈值的时间设置告警级别
                #                     prediction_level = None
                #                     if hours_to_threshold <= 24:  # 24小时内达到阈值
                #                         prediction_level = 'critical'
                #                         notify_interval = notify_critical_interval
                #                     elif hours_to_threshold <= 72:  # 24-72小时内达到阈值
                #                         prediction_level = 'warning'
                #                         notify_interval = notify_warning_interval
                                    
                #                     if prediction_level:
                #                         # 从host_alarm表获取最后一条告警记录
                #                         alarm_key = f"{host_id}_disk_{mountpoint}"
                #                         last_alarm = sql.table('host_alarm').where('host_id=? AND alarm_type=?', 
                #                             (host_id, '资源增长预警')).order('id desc').field('addtime').find()
                #                         last_alarm_time = int(time.mktime(time.strptime(last_alarm['addtime'], '%Y-%m-%d %H:%M:%S'))) if last_alarm else 0
                                        
                #                         if (current_time - last_alarm_time) >= notify_interval:
                #                             # 生成告警内容
                #                             alarm_level_map = {
                #                                 'critical': '紧急',
                #                                 'warning': '警告'
                #                             }
                                            
                #                             alarm_content = f"磁盘({mountpoint})使用率增长过快，已增长 {growth_percentage:.2f}%，当前使用率 {latest_used_percent:.2f}%，每小时增长 {growth_rate_per_hour:.2f}%，预计 {days_to_threshold:.1f} 天后（{hours_to_threshold:.1f} 小时后）将达到 {warning_threshold}% 的警戒线"
                                            
                #                             # 添加告警记录
                #                             sql.table('host_alarm').add(
                #                                 'host_id,host_name,alarm_type,alarm_level,alarm_content,addtime',
                #                                 (host_id, host_name, '资源增长预警', alarm_level_map[prediction_level], alarm_content, time.strftime('%Y-%m-%d %H:%M:%S'))
                #                             )
                                            
                #                             # 发送通知消息
                #                             notify_msg = jh.generateCommonNotifyMessage(f"主机 [{host_name}] {alarm_content}")
                #                             jh.notifyMessage(
                #                                 title=f'资源增长预警-{alarm_level_map[prediction_level]}', 
                #                                 msg=notify_msg, 
                #                                 stype='资源增长预警', 
                #                                 trigger_time=notify_interval
                #                             )
                # except Exception as e:
                #     print(f"分析磁盘数据出错: {str(e)}")
            
            print(f"{Fore.GREEN}★ ========= [resourceGrowthAlarm] SUCCESS - 完成资源增长分析: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(int(time.time())))}{Style.RESET_ALL}")
            
            # 休眠至下次执行
            time.sleep(scan_interval)
    
    except Exception as ex:
        traceback.print_exc()
        jh.writeFile('logs/resource_growth_interrupt.pl', str(ex))
        print(f"{Fore.RED}★ ========= [resourceGrowthAlarm] ERROR：{str(ex)} {Style.RESET_ALL}")
        
        notify_msg = jh.generateCommonNotifyMessage("资源增长预测异常：" + str(ex))
        jh.notifyMessage(title='资源增长预测异常通知', msg=notify_msg, stype='资源增长预测', trigger_time=3600)
        
        time.sleep(300)  # 出错后等待5分钟再重试
        hostGrowthAlarmTask()  # 递归重启
  

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
    # ct = threading.Thread(target=clientTask)
    # ct = setDaemon(ct)
    # ct.start()

    # 资源增长告警
    hga = threading.Thread(target=hostGrowthAlarmTask)
    hga = setDaemon(hga)
    hga.start()

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
