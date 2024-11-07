import psutil
import time
import json
import subprocess

def get_cpu_info():
    # 获取CPU信息
    return {
        'logicalCores': psutil.cpu_count(logical=True),
        'modelName': psutil.cpu_freq().current,
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
        'usedPercent': virtual_mem.percent,
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
    for partition in partitions:
        if 'rw' in partition.opts:  # 仅考虑可读写的分区
            disk_usage = psutil.disk_usage(partition.mountpoint)
            # disk_io_counters = psutil.disk_io_counters(perdisk=True)
            disk_info.append({
                'total': disk_usage.total / (1024 ** 3),  # 转换为 GB
                'used': disk_usage.used / (1024 ** 3),
                'free': disk_usage.free / (1024 ** 3),
                'usedPercent': disk_usage.percent,
                'fstype': partition.fstype,
                'name': partition.device,
                # 'ioPercent': 
                # 'ioTime': 
                # 'iops': 
                'mountpoint': partition.mountpoint
            })
            # usage_info[partition.mountpoint] = {
            #     'total': usage.total / (1024 ** 3),  # 转换为 GB
            #     'used': usage.used / (1024 ** 3),
            #     'free': usage.free / (1024 ** 3),
            #     'percent': usage.percent
            # }
    return disk_info

# def get_disk_io_speed(interval=1):
#     # 获取初始磁盘 IO 统计
#     disk_io_start = psutil.disk_io_counters()
#     bytes_read_start = disk_io_start.read_bytes
#     bytes_written_start = disk_io_start.write_bytes
    
#     # 等待指定的时间间隔
#     time.sleep(interval)
    
#     # 获取结束时的磁盘 IO 统计
#     disk_io_end = psutil.disk_io_counters()
#     bytes_read_end = disk_io_end.read_bytes
#     bytes_written_end = disk_io_end.write_bytes
    
#     # 计算读写速度（字节/秒转换为 KB/秒）
#     read_speed = (bytes_read_end - bytes_read_start) / 1024 / interval
#     write_speed = (bytes_written_end - bytes_written_start) / 1024 / interval
    
#     return read_speed, write_speed

def get_net_info(interval=1):
    # 获取初始网络 IO 信息
    net_info_start = psutil.net_io_counters(pernic=True)
    time.sleep(interval)  # 等待指定的时间间隔
    # 获取时间间隔后的网络 IO 信息
    net_info_end = psutil.net_io_counters(pernic=True)

    net_info = []
    for name, io_start in net_info_start.items():
        io_end = net_info_end[name]
        recv_per_second = (io_end.bytes_recv - io_start.bytes_recv) / interval
        sent_per_second = (io_end.bytes_sent - io_start.bytes_sent) / interval
        net_info.append({
            'name': name,
            'recv': io_end.bytes_recv,
            'recv_per_second': recv_per_second,
            'sent': io_end.bytes_sent,
            'sent_per_second': sent_per_second
        })
    
    return net_info

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
        '15min': load_avg[2]
    }

def get_firewall_info():
    # 检查防火墙是否正在运行
    is_running = False
    try:
        # 通过执行iptables命令检查防火墙状态
        subprocess.run(["iptables", "-L"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        is_running = True
    except subprocess.CalledProcessError:
        is_running = False

    # 获取防火墙规则
    rules = []
    try:
        # 获取iptables规则
        result = subprocess.run(["iptables", "-L", "-n", "-v"], check=True, stdout=subprocess.PIPE)
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
        "firewall_info": get_firewall_info(),

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
