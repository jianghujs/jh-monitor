#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import datetime
import random
import sqlite3

sys.path.append(os.getcwd() + "/class/core")
import jh
import db

# 创建测试主机
# test_host = {
#     'host_id': 'test_host_001',
#     'host_name': '测试主机',
#     'ip': '192.168.1.100',
#     'status': 'Running'
# }
test_host = {
    'host_id': 'H_debian_GZUI',
    'host_name': 'BK100-32',
    'ip': '192.168.3.32',
    'status': 'Running'
}

def create_test_host():
    """创建测试主机"""
    
    # 检查主机是否已存在
    if not jh.M('host').where('host_id=?', (test_host['host_id'],)).count():
        jh.M('host').add("host_id,host_name,ip,addtime", (test_host['host_id'], test_host['host_name'], test_host['ip'], time.strftime('%Y-%m-%d %H:%M:%S')))
    
    print("测试主机创建完成")

def create_test_host_detail(duration_seconds=600, interval_seconds=60):
    """持续模拟生成监控数据
    
    Args:
        duration_seconds: 模拟持续时间（秒）
        interval_seconds: 数据生成间隔（秒）
    """
    current_time = int(time.time())
    base_time = current_time - duration_seconds  # 基准时间设为当前时间减去持续时间
    last_mem_percent = 60.0  # 增加初始内存使用率
    last_disk_percent = 45.0  # 增加初始磁盘使用率
    
    print("开始生成模拟监控数据...")
    
    # 使用模拟时间
    for simulated_time in range(base_time, current_time, interval_seconds):

        # 生成波动的监控数据 - 增加变化幅度

        # 紧急
        # mem_used_percent = min(95, max(2, last_mem_percent + random.uniform(-2, 10)))  # 增加内存增长幅度
        # disk_used_percent = min(95, max(2, last_disk_percent + random.uniform(-2, 8)))  # 增加磁盘增长幅度
        # 警告

        mem_used_percent = min(95, max(2, last_mem_percent + random.uniform(-0.001, 0.2)))  # 增加内存增长幅度
        disk_used_percent = min(95, max(2, last_disk_percent + random.uniform(-0.001, 0.05)))  # 增加磁盘增长幅度
        
        # 构建主机详情数据
        host_detail = {
            'host_id': test_host['host_id'],
            'host_name': test_host['host_name'],
            'host_status': test_host['status'],
            'uptime': '',
            'host_info': json.dumps({
                'hostName': 'debian',
                'kernelArch': 'x86_64',
                'kernelVersion': '5.10.0-30-amd64',
                'os': 'Debian GNU/Linux 11 (bullseye)',
                'platform': 'Linux',
                'platformFamily': 'Linux',
                'platformVersion': '#1 SMP Debian 5.10.218-1 (2024-06-01)',
                'procs': 2,
                'upTime': 4010576,
                'upTimeStr': '46天 10小时 2分钟',
                'cpuModel': '11th Gen Intel(R) Core(TM) i3-1115G4 @ 3.00GHz',
                'lastBootTime': '2025-02-16 22:54',
                'isJHPanel': True,
                'jhPanelUrl': 'http://127.0.1.1:10744/ghy2sdop',
                'isPVE': False,
                'pveUrl': ''
            }),
            'cpu_info': json.dumps({
                'cpuCount': 2,
                'logicalCores': 1,
                'modelName': '11th Gen Intel(R) Core(TM) i3-1115G4 @ 3.00GHz * 2',
                'percent': 23.4
            }),
            'mem_info': json.dumps({
                'total': 3919.43359375,
                'used': 1211.80859375,
                'free': 174.51953125,
                'usedPercent': round(mem_used_percent, 2),
                'buffers': 504.56640625,
                'cached': 2028.5390625,
                'swapTotal': 3919.43359375,
                'swapUsed': 468.99609375,
                'swapFree': 506.0,
                'swapUsedPercent': 48.1
            }),
            'disk_info': json.dumps([{
                'total': 32626225152,
                'used': int(32626225152 * (disk_used_percent / 100)),
                'free': int(32626225152 * ((100 - disk_used_percent) / 100)),
                'usedPercent': round(disk_used_percent, 1),
                'fstype': 'ext4',
                'name': '/dev/sda1',
                'mountpoint': '/',
                'readSpeed': 0,
                'writeSpeed': 24576
            }]),
            'net_info': json.dumps({
                'upTotal': 263634072010,
                'downTotal': 370600524882,
                'up': 102.43,
                'down': 98.23,
                'downPackets': 774608536,
                'upPackets': 734088483
            }),
            'load_avg': json.dumps({
                '1min': 1.27,
                '5min': 3.08,
                '15min': 3.56,
                'max': 4
            }),
            'firewall_info': '{}',
            'port_info': '{}',
            'backup_info': '{}',
            'temperature_info': '{}',
            'ssh_user_list': '{}',
            'last_update': None,
            'addtime': str(simulated_time)  # 转换为字符串
        }
        
        print(host_detail['addtime'])
        
        # 插入新的监控数据
        host_detail_keys = ','.join(list(host_detail.keys()))
        host_detail_values = tuple(host_detail.values())
        result = jh.M('host_detail').add(host_detail_keys, host_detail_values)
        print(result)
        
        last_mem_percent = mem_used_percent
        last_disk_percent = disk_used_percent
        
        print(f"生成数据 - 时间: {datetime.datetime.fromtimestamp(simulated_time)} - 内存使用率: {mem_used_percent:.2f}%, 磁盘使用率: {disk_used_percent:.2f}%")
    
    # 打印创建的数据长度
    print(jh.M('host_detail').where('host_id=?', (test_host['host_id'],)).count())
    
    print("监控数据生成完成")

def test_growth_alarm():
    """测试增长告警功能"""
    try:
        # 创建初始测试数据
        create_test_host()
        
        # 持续模拟生成新的监控数据（持续5分钟，每分钟一次）
        create_test_host_detail(duration_seconds=600, interval_seconds=60)
        
        # 等待10秒
        time.sleep(15)
        
        # 检查告警记录
        alarms = jh.M('host_alarm').where('host_id=?', (test_host['host_id'],)).select()
        
        print("\n告警记录:")
        if alarms:
            for alarm in alarms:
                print(f"时间: {alarm[6]}")  # addtime 在第7个位置
                print(f"类型: {alarm[3]}")  # alarm_type 在第4个位置
                print(f"级别: {alarm[4]}")  # alarm_level 在第5个位置
                print(f"内容: {alarm[5]}")  # alarm_content 在第6个位置
                print("-" * 50)
        else:
            print("未检测到告警记录")

        # time.sleep(10)
    finally:
        # cleanup_test_data()
        pass

def cleanup_test_data():
    """清理测试数据"""
    # 删除测试主机
    # jh.M('host').where('host_id=?', (test_host['host_id'],)).delete()
    
    # 删除测试主机的监控数据
    jh.M('host_detail').where('host_id=?', (test_host['host_id'],)).delete()
    
    # 删除测试主机的告警记录
    jh.M('host_alarm').where('host_id=?', (test_host['host_id'],)).delete()
    
    print("测试数据清理完成")

if __name__ == "__main__":
    # 检查命令行参数
    import sys
    command = sys.argv[1] if len(sys.argv) > 1 else 'test'
    if command == "clean":
        print("清理测试数据...")
        cleanup_test_data()
    elif command == "clean_and_test":
        print("清理测试数据...")
        cleanup_test_data()
        print("测试增长告警...")
        test_growth_alarm()
    else:
        print("测试增长告警...")
        test_growth_alarm() 