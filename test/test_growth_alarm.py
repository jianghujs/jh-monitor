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
test_host = {
    'host_id': 'test_host_001',
    'host_name': '测试主机',
    'ip': '192.168.1.100',
    'status': 'Running'
}
# test_host = {
#     'host_id': 'H_debian_GZUI',
#     'host_name': 'BK100-32',
#     'ip': '192.168.3.32',
#     'status': 'Running'
# }

def create_test_host():
    """创建测试主机"""
    
    # 检查主机是否已存在
    if not jh.M('host').where('host_id=?', (test_host['host_id'],)).count():
        jh.M('host').add("host_id,host_name,ip,addtime", (test_host['host_id'], test_host['host_name'], test_host['ip'], time.strftime('%Y-%m-%d %H:%M:%S')))
    
    print("测试主机创建完成")

def test_short_term_fluctuation():
    """测试短暂波动不会触发告警的情况"""
    try:
        # 创建初始测试数据
        create_test_host()
        
        # 模拟短暂波动（持续1分钟，每10秒一次）
        current_time = int(time.time())
        base_time = current_time - 60  # 1分钟
        last_mem_percent = 60.0
        last_disk_percent = 45.0
        
        print("开始生成短暂波动测试数据...")
        
        # 生成6个数据点（每10秒一个）
        for simulated_time in range(base_time, current_time, 10):
            # 生成随机波动（范围较小）
            mem_used_percent = min(95, max(2, last_mem_percent + random.uniform(-0.5, 0.5)))
            disk_used_percent = min(95, max(2, last_disk_percent + random.uniform(-0.2, 0.2)))
            
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
                'addtime': str(simulated_time)
            }
            
            # 插入新的监控数据
            host_detail_keys = ','.join(list(host_detail.keys()))
            host_detail_values = tuple(host_detail.values())
            jh.M('host_detail').add(host_detail_keys, host_detail_values)
            last_mem_percent = mem_used_percent
            last_disk_percent = disk_used_percent
            
            print(f"生成数据 - 时间: {datetime.datetime.fromtimestamp(simulated_time)} - 内存使用率: {mem_used_percent:.2f}%, 磁盘使用率: {disk_used_percent:.2f}%")
        
        # 获取最新和历史记录
        latest_record = jh.M('host_detail').where('host_id=? AND host_status=?', 
                            (test_host['host_id'], 'Running')).order('id desc').field('id,mem_info,disk_info,addtime').find()
        
        history_start = current_time - (60 * 60)  # 1小时
        history_records = jh.M('host_detail').where('host_id=? AND addtime>?', 
                            (test_host['host_id'], history_start, )).order('id desc').field('id,mem_info,disk_info,addtime').select()
        
        if latest_record and history_records:
            # 直接调用分析函数
            memory_alarm = jh.analyze_resource_growth(
                test_host['host_id'], test_host['host_name'], latest_record, history_records, 
                'memory', 'mem_info', 80,  # warning_threshold
                72,  # prediction_critical_hours
                168,  # prediction_warning_hours
                3600,  # notify_critical_interval
                7200,  # notify_warning_interval
                current_time, 60  # scan_history_minutes
            )
            
            disk_alarm = jh.analyze_resource_growth(
                test_host['host_id'], test_host['host_name'], latest_record, history_records, 
                'disk', 'disk_info', 80,  # warning_threshold
                72,  # prediction_critical_hours
                168,  # prediction_warning_hours
                3600,  # notify_critical_interval
                7200,  # notify_warning_interval
                current_time, 60  # scan_history_minutes
            )
            
            print("\n分析结果:")
            print("内存告警:", memory_alarm)
            print("磁盘告警:", disk_alarm)
            
            # 验证是否没有触发告警
            assert memory_alarm['level'] is None, "短暂波动不应该触发内存告警"
            assert disk_alarm['level'] is None, "短暂波动不应该触发磁盘告警"
            
            print("测试通过：短暂波动没有触发告警")
        else:
            print("错误：无法获取足够的测试数据")
            
    finally:
        # cleanup_test_data()
        pass

def test_growth_alarm():
    """测试增长告警功能"""
    try:
        # 创建初始测试数据
        create_test_host()
        
        # 持续模拟生成新的监控数据（持续5分钟，每分钟一次）
        create_test_host_detail(duration_seconds=600, interval_seconds=60)
        
        # 获取最新和历史记录
        current_time = int(time.time())
        latest_record = jh.M('host_detail').where('host_id=? AND host_status=?', 
                            (test_host['host_id'], 'Running')).order('id desc').field('id,mem_info,disk_info,addtime').find()
        
        history_start = current_time - (60 * 60)  # 1小时
        history_records = jh.M('host_detail').where('host_id=? AND addtime>?', 
                            (test_host['host_id'], history_start, )).order('id desc').field('id,mem_info,disk_info,addtime').select()
        print("history_records", len(history_records), history_records)


        if latest_record and history_records:
            # 直接调用分析函数
            memory_alarm = jh.analyze_resource_growth(
                test_host['host_id'], test_host['host_name'], latest_record, history_records, 
                'memory', 'mem_info', 80,  # warning_threshold
                72,  # prediction_critical_hours
                168,  # prediction_warning_hours
                3600,  # notify_critical_interval
                7200,  # notify_warning_interval
                current_time, 60  # scan_history_minutes
            )
            
            disk_alarm = jh.analyze_resource_growth(
                test_host['host_id'], test_host['host_name'], latest_record, history_records, 
                'disk', 'disk_info', 80,  # warning_threshold
                72,  # prediction_critical_hours
                168,  # prediction_warning_hours
                3600,  # notify_critical_interval
                7200,  # notify_warning_interval
                current_time, 60  # scan_history_minutes
            )
            
            print("\n分析结果:")
            print("内存告警:", memory_alarm)
            print("磁盘告警:", disk_alarm)
            
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
        else:
            print("错误：无法获取足够的测试数据")
            
    finally:
        cleanup_test_data()

def test_trigger_alarm():
    """测试资源使用率持续增长触发告警的情况"""
    try:
        # 创建初始测试数据
        create_test_host()
        
        # 模拟资源使用率持续增长（持续30分钟，每5分钟一次）
        current_time = int(time.time())
        base_time = current_time - (30 * 60)  # 30分钟
        last_mem_percent = 60.0
        last_disk_percent = 45.0
        
        print("开始生成持续增长测试数据...")
        
        # 生成6个数据点（每5分钟一个）
        for simulated_time in range(base_time, current_time, 300):
            # 生成持续增长的数据（内存每5分钟增长1%，磁盘每5分钟增长0.5%）
            mem_used_percent = min(95, last_mem_percent + 1.0)
            disk_used_percent = min(95, last_disk_percent + 0.5)
            
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
                'addtime': str(simulated_time)
            }
            
            # 插入新的监控数据
            host_detail_keys = ','.join(list(host_detail.keys()))
            host_detail_values = tuple(host_detail.values())
            jh.M('host_detail').add(host_detail_keys, host_detail_values)
            
            last_mem_percent = mem_used_percent
            last_disk_percent = disk_used_percent
            
            print(f"生成数据 - 时间: {datetime.datetime.fromtimestamp(simulated_time)} - 内存使用率: {mem_used_percent:.2f}%, 磁盘使用率: {disk_used_percent:.2f}%")
        
        # 获取最新和历史记录
        latest_record = jh.M('host_detail').where('host_id=?', 
                            (test_host['host_id'],)).order('id desc').field('id,mem_info,disk_info,addtime').find()
        
        history_start = current_time - (60 * 60)  # 1小时
        history_records = jh.M('host_detail').where('host_id=? AND addtime>?', 
                            (test_host['host_id'], history_start,)).order('id desc').field('id,mem_info,disk_info,addtime').select()
        
        print("latest_record", latest_record)
        print("history_records", len(history_records))
        
        if latest_record and history_records:
            # 直接调用分析函数
            memory_alarm = jh.analyze_resource_growth(
                test_host['host_id'], test_host['host_name'], latest_record, history_records, 
                'memory', 'mem_info', 80,  # warning_threshold
                72,  # prediction_critical_hours
                168,  # prediction_warning_hours
                3600,  # notify_critical_interval
                7200,  # notify_warning_interval
                current_time, 60  # scan_history_minutes
            )
            
            disk_alarm = jh.analyze_resource_growth(
                test_host['host_id'], test_host['host_name'], latest_record, history_records, 
                'disk', 'disk_info', 80,  # warning_threshold
                72,  # prediction_critical_hours
                168,  # prediction_warning_hours
                3600,  # notify_critical_interval
                7200,  # notify_warning_interval
                current_time, 60  # scan_history_minutes
            )
            
            print("\n分析结果:")
            print("内存告警:", memory_alarm)
            print("磁盘告警:", disk_alarm)
            
            # 验证是否触发了告警
            assert memory_alarm['level'] is not None, "持续增长应该触发内存告警"
            assert disk_alarm['level'] is not None, "持续增长应该触发磁盘告警"
            
            print("测试通过：持续增长触发了告警")
        else:
            print("错误：无法获取足够的测试数据")
            
    finally:
        # cleanup_test_data()
        pass

def cleanup_test_data():
    """清理测试数据"""
    # 删除测试主机
    jh.M('host').where('host_id=?', (test_host['host_id'],)).delete()
    
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
        print("测试增长告警...")
        test_growth_alarm()
    elif command == "test_fluctuation":
        print("测试短暂波动...")
        cleanup_test_data()
        test_short_term_fluctuation()
    elif command == "test_trigger":
        print("测试触发告警...")
        cleanup_test_data()
        test_trigger_alarm()