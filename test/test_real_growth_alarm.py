#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import json
import time
import datetime
import random
import sqlite3
import psutil
import tempfile

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

# 全局变量存储占用的内存和文件
memory_blocks = []
disk_files = []

def create_test_host():
    """创建测试主机"""
    # 检查主机是否已存在
    if not jh.M('host').where('host_id=?', (test_host['host_id'],)).count():
        jh.M('host').add("host_id,host_name,ip,addtime", 
            (test_host['host_id'], test_host['host_name'], test_host['ip'], time.strftime('%Y-%m-%d %H:%M:%S')))
    print("测试主机创建完成")

def allocate_memory(mb):
    """分配指定大小的内存
    
    Args:
        mb: 要分配的内存大小（MB）
    """
    try:
        # 分配内存（使用字节数组）
        block = bytearray(mb * 1024 * 1024)
        memory_blocks.append(block)
        print(f"已分配 {mb}MB 内存")
    except MemoryError:
        print("内存分配失败，可能已达到系统限制")

def create_large_file(mb, file_path):
    """创建指定大小的文件
    
    Args:
        mb: 文件大小（MB）
        file_path: 文件路径
    """
    try:
        with open(file_path, 'wb') as f:
            # 写入随机数据
            f.write(os.urandom(mb * 1024 * 1024))
        disk_files.append(file_path)
        print(f"已创建 {mb}MB 大小的文件: {file_path}")
    except Exception as e:
        print(f"创建文件失败: {str(e)}")

def simulate_growth(duration_minutes=30, interval_seconds=300, memory_step_mb=100, disk_step_mb=100):
    """模拟资源使用率持续增长
    
    Args:
        duration_minutes: 模拟持续时间（分钟）
        interval_seconds: 数据采集间隔（秒）
        memory_step_mb: 每次增加的内存大小（MB）
        disk_step_mb: 每次增加的磁盘空间大小（MB）
    """
    try:
        # 创建初始测试数据
        create_test_host()
        
        # 创建临时目录用于存储测试文件
        temp_dir = tempfile.mkdtemp()
        print(f"创建临时目录: {temp_dir}")
        
        # 模拟资源使用率持续增长
        current_time = int(time.time())
        base_time = current_time - (duration_minutes * 60)  # 转换为秒
        
        print("开始实际占用资源...")
        
        # 生成数据点
        for simulated_time in range(base_time, current_time, interval_seconds):
            # 获取当前系统资源使用情况
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # 计算当前使用率
            mem_used_percent = memory.percent
            disk_used_percent = disk.percent
            
            # 如果内存使用率低于90%，继续分配内存
            if mem_used_percent < 90:
                allocate_memory(memory_step_mb)
            
            # 如果磁盘使用率低于90%，继续创建文件
            if disk_used_percent < 90:
                file_path = os.path.join(temp_dir, f"test_file_{simulated_time}.dat")
                create_large_file(disk_step_mb, file_path)
            
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
                    'percent': psutil.cpu_percent()
                }),
                'mem_info': json.dumps({
                    'total': memory.total / (1024 * 1024),
                    'used': memory.used / (1024 * 1024),
                    'free': memory.free / (1024 * 1024),
                    'usedPercent': round(mem_used_percent, 2),
                    'buffers': memory.buffers / (1024 * 1024),
                    'cached': memory.cached / (1024 * 1024),
                    'swapTotal': psutil.swap_memory().total / (1024 * 1024),
                    'swapUsed': psutil.swap_memory().used / (1024 * 1024),
                    'swapFree': psutil.swap_memory().free / (1024 * 1024),
                    'swapUsedPercent': psutil.swap_memory().percent
                }),
                'disk_info': json.dumps([{
                    'total': disk.total,
                    'used': disk.used,
                    'free': disk.free,
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
                    '1min': psutil.getloadavg()[0],
                    '5min': psutil.getloadavg()[1],
                    '15min': psutil.getloadavg()[2],
                    'max': psutil.cpu_count()
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
            
            print(f"生成数据 - 时间: {datetime.datetime.fromtimestamp(simulated_time)} - 内存使用率: {mem_used_percent:.2f}%, 磁盘使用率: {disk_used_percent:.2f}%")
            
            # 等待指定的间隔时间
            time.sleep(interval_seconds)
        
        # 获取最新和历史记录
        latest_record = jh.M('host_detail').where('host_id=?', 
                            (test_host['host_id'],)).order('id desc').field('id,mem_info,disk_info,addtime').find()
        
        history_start = current_time - (60 * 60)  # 1小时
        history_records = jh.M('host_detail').where('host_id=? AND addtime>?', 
                            (test_host['host_id'], history_start,)).order('id desc').field('id,mem_info,disk_info,addtime').select()
        
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
        # 清理测试数据
        cleanup_test_data()
        
        # 释放内存
        memory_blocks.clear()
        
        # 删除临时文件
        for file_path in disk_files:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"删除文件失败: {str(e)}")
        
        # 删除临时目录
        try:
            os.rmdir(temp_dir)
        except Exception as e:
            print(f"删除临时目录失败: {str(e)}")

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
    if len(sys.argv) > 1:
        duration_minutes = int(sys.argv[1])
    else:
        duration_minutes = 30
    
    if len(sys.argv) > 2:
        interval_seconds = int(sys.argv[2])
    else:
        interval_seconds = 300
    
    if len(sys.argv) > 3:
        memory_step_mb = int(sys.argv[3])
    else:
        memory_step_mb = 100
    
    if len(sys.argv) > 4:
        disk_step_mb = int(sys.argv[4])
    else:
        disk_step_mb = 100
    
    print(f"开始实际占用资源，持续时间: {duration_minutes}分钟，采集间隔: {interval_seconds}秒")
    print(f"每次增加内存: {memory_step_mb}MB，每次增加磁盘空间: {disk_step_mb}MB")
    simulate_growth(duration_minutes, interval_seconds, memory_step_mb, disk_step_mb) 