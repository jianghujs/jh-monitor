#!/usr/bin/env python3
import argparse
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

DEFAULT_OUTPUT_DIR = os.environ.get(
    'REPORT_COLLECTOR_OUTPUT_DIR',
    '/home/ansible_user/jh-monitor-data'
)


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def append_text(path, content):
    output_dir = os.path.dirname(path) or '.'
    ensure_dir(output_dir)
    with open(path, 'a') as fp:
        fp.write(content)
        fp.flush()
        os.fsync(fp.fileno())


def append_ndjson(path, rows):
    if not rows:
        return
    content = '\n'.join([json.dumps(row, ensure_ascii=False) for row in rows]) + '\n'
    append_text(path, content)


def export_system_status(output_dir, payload):
    file_date = datetime.datetime.now().strftime('%Y%m%d')
    output_path = os.path.join(output_dir, 'host-pve-system-status-%s.json' % file_date)
    append_ndjson(output_path, [payload])
    return output_path


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
    parser = argparse.ArgumentParser(description='Collect PVE system status.')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--stdout-json', action='store_true')
    args = parser.parse_args()

    payload = build_system_status()
    if args.stdout_json:
        print(json.dumps(payload, ensure_ascii=False))
        return

    output_path = export_system_status(args.output_dir, payload)
    print(output_path)


if __name__ == '__main__':
    main()
