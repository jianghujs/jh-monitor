#!/usr/bin/env python3
import datetime
import json
import os
import socket
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from get_host_info import get_host_ip, is_pve_machine
from get_pve_hardware_report import DEFAULT_THRESHOLDS, HardwareReporter


def format_pve_disks(filesystems):
    disks = []
    for fs in filesystems or []:
        disks.append({
            'path': fs.get('mountpoint', ''),
            'size': [
                fs.get('size', '0B'),
                fs.get('used', '0B'),
                fs.get('available', '0B'),
                '{0}%'.format(int(float(fs.get('use_percent', 0) or 0)))
            ],
            'inodes': ['', '', '', ''],
            'fstype': '',
            'device': fs.get('filesystem', '')
        })
    return disks


def build_system_status(host_meta=None):
    if host_meta is None:
        host_meta = {
            'host_id': socket.gethostname(),
            'host_name': socket.gethostname(),
            'host_ip': get_host_ip() or '127.0.0.1'
        }

    now = datetime.datetime.now()
    add_time = now.strftime('%Y-%m-%d %H:%M:%S')
    add_timestamp = now.timestamp()

    reporter = HardwareReporter(DEFAULT_THRESHOLDS, None, False, enable_log=False)
    collect_error = ''
    pve_data = {}
    pve_issues = []
    thresholds = dict(DEFAULT_THRESHOLDS)

    if not is_pve_machine():
        collect_error = 'not_pve_machine'
    else:
        try:
            reporter.collect_all()
            reporter._analyze_all_and_collect_issues()
            pve_data = reporter.report_data or {}
            pve_issues = reporter.issues or []
            thresholds = reporter.thresholds or dict(DEFAULT_THRESHOLDS)
        except Exception as ex:
            collect_error = str(ex)

    cpu_data = pve_data.get('cpu', {}) if isinstance(pve_data, dict) else {}
    memory_data = pve_data.get('memory', {}) if isinstance(pve_data, dict) else {}
    disk_data = pve_data.get('disk', {}) if isinstance(pve_data, dict) else {}
    load_data = cpu_data.get('load', [0.0, 0.0, 0.0]) or [0.0, 0.0, 0.0]
    while len(load_data) < 3:
        load_data.append(0.0)
    cpu_count = os.cpu_count() or 1
    load_one = float(load_data[0] or 0.0)

    return {
        'host': {
            'host_id': host_meta['host_id'],
            'host_name': host_meta['host_name'],
            'host_ip': host_meta['host_ip'],
            'host_group': '',
            'host_status': 'running',
            'system_type': 'pve'
        },
        'system': {
            'cpu': round(float(cpu_data.get('usage', 0) or 0), 2),
            'memory': round(float(memory_data.get('usage_percent', 0) or 0), 2),
            'load': {
                'pro': round((load_one / float(cpu_count)) * 100, 2),
                'one': round(load_one, 2),
                'five': round(float(load_data[1] or 0), 2),
                'fifteen': round(float(load_data[2] or 0), 2)
            },
            'disks': format_pve_disks(disk_data.get('filesystems', []))
        },
        'pve': {
            'data': pve_data,
            'issues': pve_issues,
            'thresholds': thresholds,
            'error': collect_error
        },
        'add_time': add_time,
        'add_timestamp': add_timestamp,
        'collector': {
            'source': 'get_pve_system_status.py',
            'version': '1.0.0'
        }
    }


def main():
    print(json.dumps(build_system_status(), ensure_ascii=False))


if __name__ == '__main__':
    main()
