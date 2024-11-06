import os
import socket
import subprocess
import json

def get_host_ip():
    # 获取主机IP地址
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

def get_os_info():
    # 获取操作系统信息
    with open('/etc/os-release') as f:
        lines = f.readlines()
    os_info = {}
    for line in lines:
        key, value = line.strip().split('=', 1)
        os_info[key] = value.strip('"')
    return os_info.get('PRETTY_NAME', 'Unknown OS')

def get_uptime():
    # 获取系统运行时间并转换为天、小时、分钟格式
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    return int(uptime_seconds)

def get_uptime_str():
    # 获取系统运行时间并转换为天、小时、分钟格式
    with open('/proc/uptime', 'r') as f:
        uptime_seconds = float(f.readline().split()[0])
    days = int(uptime_seconds // (60 * 60 * 24))
    hours = int((uptime_seconds % (60 * 60 * 24)) // (60 * 60))
    minutes = int((uptime_seconds % (60 * 60)) // 60)
    return f"{days}天 {hours}小时 {minutes}分钟"


def get_cpu_model():
    # 获取 CPU 型号
    with open('/proc/cpuinfo', 'r') as f:
        for line in f:
            if line.startswith('model name'):
                return line.split(':', 1)[1].strip()
    return "Unknown CPU Model"

def get_last_boot_time():
    # 获取上次启动时间
    result = subprocess.run(['who', '-b'], stdout=subprocess.PIPE)
    last_boot_info = result.stdout.decode().strip()
    last_boot_time = last_boot_info.split(' ')[-2:]
    return ' '.join(last_boot_time)

def is_jh_panel_installed():
    try:
        # 执行命令并获取输出
        result = subprocess.run(
            "ps -ef | grep -v grep | grep jh-panel",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 检查输出是否包含 jh-panel
        if result.stdout:
            return True
        else:
            return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def is_pve_machine():
    # 检查 /etc/pve 目录是否存在
    return os.path.exists('/etc/pve')

def main():
    host_info = {
        "hostName": socket.gethostname(),
        "kernelArch": os.uname().machine,
        "kernelVersion": os.uname().release,
        "os": get_os_info(),
        "platform": os.uname().sysname,
        "platformFamily": os.uname().sysname,
        "platformVersion": os.uname().version,
        "procs": os.cpu_count(),
        "upTime": get_uptime(),
        "upTimeStr": get_uptime_str(),
        "cpuModel": get_cpu_model(),
        "lastBootTime": get_last_boot_time(),
        "isJHPanel": is_jh_panel_installed(),
        "isPVE": is_pve_machine()
    }
    
    # 将字典转换为 JSON 格式的字符串并打印
    print(json.dumps(host_info))


if __name__ == '__main__':
    main()
