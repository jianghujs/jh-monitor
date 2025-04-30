#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import time
import random
import psutil
import tempfile

# 全局变量存储占用的内存和文件
memory_blocks = []
disk_files = []

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
            
            print(f"时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(simulated_time))} - 内存使用率: {mem_used_percent:.2f}%, 磁盘使用率: {disk_used_percent:.2f}%")
            
            # 等待指定的间隔时间
            time.sleep(interval_seconds)
            
    finally:
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

if __name__ == "__main__":
    # 检查命令行参数
    import sys
    duration_minutes = 30
    interval_seconds = 300
    memory_step_mb = 100
    disk_step_mb = 100

    if len(sys.argv) > 1:
        duration_minutes = int(sys.argv[1])
    if len(sys.argv) > 2:
        interval_seconds = int(sys.argv[2])
    if len(sys.argv) > 3:
        memory_step_mb = int(sys.argv[3])
    if len(sys.argv) > 4:
        disk_step_mb = int(sys.argv[4])
    
    print(f"开始实际占用资源，持续时间: {duration_minutes}分钟，采集间隔: {interval_seconds}秒")
    print(f"每次增加内存: {memory_step_mb}MB，每次增加磁盘空间: {disk_step_mb}MB")
    simulate_growth(duration_minutes, interval_seconds, memory_step_mb, disk_step_mb) 