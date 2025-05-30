import psutil
import time
import json
import subprocess
import os
import re
import sys
import datetime
import shlex
import tempfile
from flask import Flask, session

def isAppleSystem():
    if sys.platform == 'darwin':
        return True
    return False

def readFile(filename):
    # 读文件内容
    try:
        fp = open(filename, 'r')
        fBody = fp.read()
        fp.close()
        return fBody
    except Exception as e:
        # print(e)
        return False
    
def getPercent(num, total):
    try:
        num = float(num)
        total = float(total)
    except ValueError:
        return None
    
    if total <= 0:
        return 0
    
    return round(num / total * 100, 2)

def execShell(cmdstring, cwd=None, timeout=None, shell=True, useTmpFile=False):

    if shell:
        cmdstring_list = cmdstring
    else:
        cmdstring_list = shlex.split(cmdstring)
    if timeout:
        end_time = datetime.datetime.now() + datetime.timedelta(seconds=timeout)
    
    if useTmpFile:
        with tempfile.TemporaryFile() as tempf:
            sub = subprocess.Popen(cmdstring_list, cwd=cwd, stdin=subprocess.PIPE,
                                shell=shell, bufsize=4096, stdout=tempf, stderr=subprocess.PIPE, preexec_fn=os.setsid)

            sub.wait()
            tempf.seek(0)
            data = tempf.read()
        # python3 fix 返回byte数据
        
        if isinstance(data, bytes):
            t = str(data, encoding='utf-8')
        

        return (t, '', sub.returncode)
    else:
        sub = subprocess.Popen(cmdstring_list, cwd=cwd, stdin=subprocess.PIPE,
                           shell=shell, bufsize=4096, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid)

        while sub.poll() is None:
            time.sleep(0.1)
            if timeout:
                if end_time <= datetime.datetime.now():
                    raise Exception("Timeout：%s" % cmdstring)

        if sys.version_info[0] == 2:
            return sub.communicate()

        data = sub.communicate()
        # python3 fix 返回byte数据
        if isinstance(data[0], bytes):
            t1 = str(data[0], encoding='utf-8')

        if isinstance(data[1], bytes):
            t2 = str(data[1], encoding='utf-8')
        
        if sub.returncode != 0:
            t1 = t1 if t1 else t2

        return (t1, t2, sub.returncode)

def get_cpu_type():
    cpuType = ''
    if isAppleSystem():
        cmd = "system_profiler SPHardwareDataType | grep 'Processor Name' | awk -F ':' '{print $2}'"
        cpuinfo = execShell(cmd)
        return cpuinfo[0].strip()

    # 取CPU类型
    cpuinfo = open('/proc/cpuinfo', 'r').read()
    rep = "model\s+name\s+:\s+(.+)"
    tmp = re.search(rep, cpuinfo, re.I)
    if tmp:
        cpuType = tmp.groups()[0]
    else:
        cpuinfo = execShell('LANG="en_US.UTF-8" && lscpu')[0]
        rep = "Model\s+name:\s+(.+)"
        tmp = re.search(rep, cpuinfo, re.I)
        if tmp:
            cpuType = tmp.groups()[0]
    return cpuType


def get_cpu_info():

    # 获取CPU信息
    cpuCount = psutil.cpu_count()
    cpuLogicalNum = psutil.cpu_count(logical=False)
    if os.path.exists('/proc/cpuinfo'):
        c_tmp = readFile('/proc/cpuinfo')
        d_tmp = re.findall("physical id.+", c_tmp)
        cpuLogicalNum = len(set(d_tmp))
    cpu_name = get_cpu_type() + " * {}".format(cpuCount)
    return {
        'cpuCount': cpuCount,
        'logicalCores': cpuLogicalNum,
        'modelName': cpu_name,
        'percent': psutil.cpu_percent(interval=1)
    }

def get_mem_info():
    # 获取内存使用信息
    # {"total": 4109926400, "free": 3076767744, "used": 467066880, "usedPercent": 11.36, "buffers": 65052672, "cached": 501039104, "swapFree": 1022357504, "swapTotal": 1022357504, "swapUsed": 0, "swapUsedPercent": 0}
    virtual_mem = psutil.virtual_memory()
    swap_mem = psutil.swap_memory()

    return {
        'total': virtual_mem.total / (1024 ** 2),  # 转换为 MB
        'used': virtual_mem.used / (1024 ** 2),
        'free': virtual_mem.free / (1024 ** 2),
        # 'usedPercent': virtual_mem.percent,
        'usedPercent': getPercent(virtual_mem.used, virtual_mem.total),
        'buffers': virtual_mem.buffers / (1024 ** 2),
        'cached': virtual_mem.cached / (1024 ** 2),
        'swapTotal': virtual_mem.total / (1024 ** 2),
        'swapUsed': swap_mem.used / (1024 ** 2),
        'swapFree': swap_mem.free / (1024 ** 2),
        'swapUsedPercent': swap_mem.percent
    }

def get_disk_info():
    # 获取磁盘使用信息
    partitions = psutil.disk_partitions()
    disk_info = []

    # 获取初始的磁盘 I/O 计数
    initial_io_counters = psutil.disk_io_counters(perdisk=True)

    # 等待一段时间以测量速度
    time.sleep(1)

    # 获取之后的磁盘 I/O 计数
    final_io_counters = psutil.disk_io_counters(perdisk=True)

    for partition in partitions:
        if 'rw' in partition.opts:  # 仅考虑可读写的分区
            disk_usage = psutil.disk_usage(partition.mountpoint)
            device_name = partition.device.split('/')[-1]  # 提取设备名称

            # 获取初始和最终的 I/O 计数
            initial_io = initial_io_counters.get(device_name)
            final_io = final_io_counters.get(device_name)

            if initial_io and final_io:
                read_bytes = final_io.read_bytes - initial_io.read_bytes
                write_bytes = final_io.write_bytes - initial_io.write_bytes

                # 计算读写速度
                read_speed = read_bytes 
                write_speed = write_bytes 

                disk_info.append({
                    'total': disk_usage.total,
                    'used': disk_usage.used,
                    'free': disk_usage.free,
                    'usedPercent': disk_usage.percent,
                    'fstype': partition.fstype,
                    'name': partition.device,
                    'mountpoint': partition.mountpoint,
                    'readSpeed': read_speed,
                    'writeSpeed': write_speed
                })

    return disk_info

def get_disk_io_speed(interval=1):
    # 获取初始磁盘 IO 统计
    disk_io_start = psutil.disk_io_counters()
    bytes_read_start = disk_io_start.read_bytes
    bytes_written_start = disk_io_start.write_bytes
    
    # 等待指定的时间间隔
    time.sleep(interval)
    
    # 获取结束时的磁盘 IO 统计
    disk_io_end = psutil.disk_io_counters()
    bytes_read_end = disk_io_end.read_bytes
    bytes_written_end = disk_io_end.write_bytes
    
    # 计算读写速度（字节/秒转换为 KB/秒）
    read_speed = (bytes_read_end - bytes_read_start) / interval
    write_speed = (bytes_written_end - bytes_written_start)  / interval
    
    return read_speed, write_speed

def get_net_info(interval=1):

    # 计算网速
    initial_io = psutil.net_io_counters()
    initial_time = time.time()
    time.sleep(interval)
    current_io = psutil.net_io_counters()
    current_time = time.time()
    # 时间差
    time_diff = current_time - initial_time
    if time_diff == 0:
        time_diff = 1  # 防止除以零
    # 计算流量差异
    bytes_sent = current_io.bytes_sent - initial_io.bytes_sent
    bytes_recv = current_io.bytes_recv - initial_io.bytes_recv
    # 速度
    up_speed = round(float(bytes_sent) / 1024 / time_diff, 2)
    down_speed = round(float(bytes_recv) / 1024 / time_diff, 2)

    # 其他
    local_lo = (0, 0, 0, 0)
    test_io = psutil.net_io_counters(pernic=True)
    for x in test_io.keys():
        if x.find("lo") > -1:
            local_lo = psutil.net_io_counters(pernic=True).get(x)[:4]
    
    all_io = psutil.net_io_counters()[:4]
    networkIo = tuple([all_io[i] - local_lo[i]
                        for i in range(0, len(all_io))])

    return {
        'upTotal': networkIo[0],
        'downTotal': networkIo[1],
        'up': up_speed,
        'down': down_speed,
        'downPackets': networkIo[3],
        'upPackets': networkIo[2]
    }

# def get_network_speed(interval=1):
#     # 获取初始网络 IO 统计
#     net_io_start = psutil.net_io_counters()
#     bytes_sent_start = net_io_start.bytes_sent
#     bytes_recv_start = net_io_start.bytes_recv
    
#     # 等待指定的时间间隔
#     time.sleep(interval)
    
#     # 获取结束时的网络 IO 统计
#     net_io_end = psutil.net_io_counters()
#     bytes_sent_end = net_io_end.bytes_sent
#     bytes_recv_end = net_io_end.bytes_recv
    
#     # 计算上传和下载速度（字节/秒转换为 KB/秒）
#     upload_speed = (bytes_sent_end - bytes_sent_start) / 1024 / interval
#     download_speed = (bytes_recv_end - bytes_recv_start) / 1024 / interval
    
#     return upload_speed, download_speed

def get_load_avg():
    # 获取系统负载信息
    load_avg = psutil.getloadavg()
    return {
        '1min': load_avg[0],
        '5min': load_avg[1],
        '15min': load_avg[2],
        'max': psutil.cpu_count() * 2
    }

def get_firewall_info():
    # 检查防火墙是否正在运行
    is_running = False
    try:
        # 通过执行iptables命令检查防火墙状态
        subprocess.run(["sudo", "iptables", "-L"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        is_running = True
    except subprocess.CalledProcessError:
        is_running = False

    # 获取防火墙规则
    rules = []
    try:
        # 获取iptables规则
        result = subprocess.run(["sudo", "iptables", "-L", "-n", "-v"], check=True, stdout=subprocess.PIPE)
        output = result.stdout.decode('utf-8')

        # 解析输出，提取规则信息
        for line in output.splitlines():
            # 过滤规则行
            if line and not line.startswith("Chain") and not line.startswith("pkts") and not line.startswith("target"):
                parts = line.split()
                if len(parts) >= 8:
                    access = parts[0]
                    protocol = parts[1]
                    source = parts[3]
                    destination = parts[4]
                    release_port = 'N/A'
                    # 尝试获取端口信息
                    if 'dpt:' in line:
                        release_port = line.split('dpt:')[1].split()[0]
                    rules.append({
                        "access": access,
                        "protocol": protocol,
                        "release_port": release_port,
                        "source": source,
                        "destination": destination
                    })
    except subprocess.CalledProcessError as e:
        print("Error retrieving firewall rules:", e)

    # 构建输出的JSON数据
    firewall_info = {
        "is_running": is_running,
        "rules": rules,
        "rule_change": {"add": None, "del": None}
    }

    return firewall_info



def main():
    interval = 1  # 秒

    system_stats = {
        "cpu_info": get_cpu_info(),
        "mem_info": get_mem_info(),
        "disk_info": get_disk_info(),
        "net_info": get_net_info(), 
        "load_avg": get_load_avg(),
        # "firewall_info": get_firewall_info(),

        # "Memory Usage": get_memory_info(),
        # "Disk Usage": get_disk_usage(),
        # "Network IO": get_network_io(),
        # "Network Speed": {
        #     "Upload Speed (KB/s)": get_network_speed(interval)[0],
        #     "Download Speed (KB/s)": get_network_speed(interval)[1]
        # },
        # "Disk IO Speed": {
        #     "Read Speed (KB/s)": get_disk_io_speed(interval)[0],
        #     "Write Speed (KB/s)": get_disk_io_speed(interval)[1]
        # }
    }

    # 将字典转换为 JSON 格式的字符串并打印
    print(json.dumps(system_stats, ensure_ascii=False, indent=4))

if __name__ == '__main__':
    main()
