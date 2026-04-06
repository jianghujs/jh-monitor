#!/usr/bin/env python3
import argparse
import datetime
import glob
import json
import os
import socket
import sys
import tempfile
import traceback

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from get_host_info import get_host_ip
from get_host_usage import get_cpu_info, get_disk_info, get_load_avg, get_mem_info

DEFAULT_OUTPUT_DIR = os.path.join(CURRENT_DIR, 'data')
DEFAULT_RETENTION_DAYS = 7
STATE_FILE_NAME = '.report-collector-state.json'
XTRABACKUP_HISTORY_FILE = '/www/server/xtrabackup/data/backup_history.json'
XTRABACKUP_INC_HISTORY_FILE = '/www/server/xtrabackup-inc/data/backup_history.json'
BACKUP_LOG_FILE = '/www/server/jh-panel/logs/backup.log'


def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


def safe_read(path):
    try:
        with open(path, 'r') as fp:
            return fp.read().strip()
    except Exception:
        return ''


def atomic_write_text(path, content):
    output_dir = os.path.dirname(path) or '.'
    ensure_dir(output_dir)
    fd, temp_path = tempfile.mkstemp(prefix='.tmp_', dir=output_dir)
    try:
        with os.fdopen(fd, 'w') as fp:
            fp.write(content)
            fp.flush()
            os.fsync(fp.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def atomic_write_json(path, data):
    atomic_write_text(path, json.dumps(data, ensure_ascii=False))


def write_ndjson(path, rows):
    content = '\n'.join([json.dumps(row, ensure_ascii=False) for row in rows])
    if content != '':
        content = content + '\n'
    atomic_write_text(path, content)


def load_state(output_dir):
    state_path = os.path.join(output_dir, STATE_FILE_NAME)
    if not os.path.exists(state_path):
        return {}, state_path
    try:
        with open(state_path, 'r') as fp:
            return json.load(fp), state_path
    except Exception:
        return {}, state_path


def save_state(state_path, state):
    atomic_write_json(state_path, state)


def get_primary_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(('8.8.8.8', 80))
        ip_addr = sock.getsockname()[0]
        sock.close()
        if ip_addr:
            return ip_addr
    except Exception:
        pass

    try:
        ip_addr = get_host_ip()
        if ip_addr:
            return ip_addr
    except Exception:
        pass
    return '127.0.0.1'


def get_host_id():
    machine_id = safe_read('/etc/machine-id')
    if machine_id:
        return machine_id
    return socket.gethostname()


def to_size(value):
    try:
        size = float(value)
    except Exception:
        size = 0.0

    units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
    for unit in units:
        if size < 1024 or unit == units[-1]:
            if unit == 'B':
                return '%d%s' % (int(size), unit)
            return '%.2f%s' % (size, unit)
        size = size / 1024.0
    return '0B'


def format_disks(disk_info):
    disks = []
    for disk in disk_info:
        total = int(disk.get('total', 0))
        used = int(disk.get('used', 0))
        free = int(disk.get('free', 0))
        used_percent = disk.get('usedPercent', 0)
        disks.append({
            'path': disk.get('mountpoint', ''),
            'size': [
                to_size(total),
                to_size(used),
                to_size(free),
                '%s%%' % int(used_percent)
            ],
            'inodes': ['', '', '', ''],
            'fstype': disk.get('fstype', ''),
            'device': disk.get('name', '')
        })
    return disks


def load_panel_runtime_info():
    runtime = {
        'site': [],
        'jianghujs': [],
        'docker': [],
        'mysql': {
            'total_size': '0B',
            'total_size_bytes': 0,
            'slave_status': [],
            'tables': []
        },
        'lsync': {
            'last_realtime_sync_date': None,
            'last_realtime_sync_timestamp': None,
            'realtime_delays': 0,
            'send_count': 0,
            'send_open_count': 0,
            'send_close_count': 0
        },
        'rsync': []
    }

    panel_dir = '/www/server/jh-panel'
    panel_core_dir = os.path.join(panel_dir, 'class/core')
    if not os.path.exists(panel_core_dir):
        return runtime

    old_cwd = os.getcwd()
    try:
        os.chdir(panel_dir)
        if panel_core_dir not in sys.path:
            sys.path.insert(0, panel_core_dir)
        import system_api as panel_system_api

        system_api_obj = panel_system_api.system_api()

        try:
            site_info = system_api_obj.getSiteInfo()
            for site in site_info.get('site_list', []):
                cert_data = site.get('cert_data') or {}
                ssl_type = site.get('ssl_type') or ''
                runtime['site'].append({
                    'id': site.get('id'),
                    'name': site.get('name', ''),
                    'path': site.get('path', ''),
                    'ps': site.get('ps', ''),
                    'status': site.get('status', ''),
                    'ssl_status': '已配置' if cert_data else '未配置',
                    'ssl_type': ssl_type,
                    'ssl_data': cert_data,
                    'add_time': site.get('addtime', '')
                })
        except Exception:
            pass

        try:
            jianghujs_info = system_api_obj.getJianghujsInfo()
            for project in jianghujs_info.get('project_list', []):
                runtime['jianghujs'].append({
                    'id': project.get('id'),
                    'name': project.get('name', ''),
                    'path': project.get('path', ''),
                    'status': project.get('status', ''),
                    'add_time': project.get('addtime', '')
                })
        except Exception:
            pass

        try:
            docker_info = system_api_obj.getDockerInfo()
            for project in docker_info.get('project_list', []):
                runtime['docker'].append({
                    'id': project.get('id'),
                    'name': project.get('name', ''),
                    'path': project.get('path', ''),
                    'status': project.get('status', ''),
                    'add_time': project.get('addtime', '')
                })
        except Exception:
            pass

        try:
            mysql_info = system_api_obj.getMysqlInfo()
            runtime['mysql']['total_size'] = mysql_info.get('total_size', '0B')
            runtime['mysql']['total_size_bytes'] = mysql_info.get('total_bytes', 0)
            for table in mysql_info.get('database_list', []):
                runtime['mysql']['tables'].append({
                    'id': table.get('id'),
                    'pid': table.get('pid', 0),
                    'table_name': table.get('name', ''),
                    'size': table.get('size', '0B'),
                    'size_bytes': table.get('size_bytes', 0)
                })
        except Exception:
            pass
    except Exception:
        pass
    finally:
        os.chdir(old_cwd)
    return runtime


def get_host_meta():
    return {
        'host_id': get_host_id(),
        'host_name': socket.gethostname(),
        'host_ip': get_primary_ip()
    }


def build_status_payload(host_meta):
    now = datetime.datetime.now()
    add_time = now.strftime('%Y-%m-%d %H:%M:%S')
    add_timestamp = now.timestamp()

    cpu_info = get_cpu_info()
    mem_info = get_mem_info()
    load_avg = get_load_avg()
    disk_info = get_disk_info()
    runtime = load_panel_runtime_info()

    cpu_cores = cpu_info.get('cpuCount', 1) or 1
    load_one = float(load_avg.get('1min', 0))
    load_pro = round((load_one / float(cpu_cores)) * 100, 2)

    return {
        'host': {
            'host_id': host_meta['host_id'],
            'host_name': host_meta['host_name'],
            'host_ip': host_meta['host_ip'],
            'host_group': '',
            'host_status': 'running'
        },
        'system': {
            'cpu': round(float(cpu_info.get('percent', 0)), 2),
            'memory': round(float(mem_info.get('usedPercent', 0)), 2),
            'load': {
                'pro': load_pro,
                'one': round(load_one, 2),
                'five': round(float(load_avg.get('5min', 0)), 2),
                'fifteen': round(float(load_avg.get('15min', 0)), 2)
            },
            'disks': format_disks(disk_info)
        },
        'site': runtime.get('site', []),
        'jianghujs': runtime.get('jianghujs', []),
        'docker': runtime.get('docker', []),
        'mysql': runtime.get('mysql', {}),
        'lsync': runtime.get('lsync', {}),
        'rsync': runtime.get('rsync', []),
        'add_time': add_time,
        'add_timestamp': add_timestamp,
        'collector': {
            'source': 'report_collector.py',
            'version': '1.1.0'
        }
    }


def export_status_payload(output_dir, payload):
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    output_path = os.path.join(output_dir, 'host-system-status-%s.json' % timestamp)
    atomic_write_json(output_path, payload)
    return output_path


def export_history_records(source_path, output_dir, state, state_key, file_prefix, host_meta):
    if not os.path.exists(source_path):
        return None

    try:
        with open(source_path, 'r') as fp:
            source_data = json.load(fp)
    except Exception:
        return None

    if not isinstance(source_data, dict):
        return None

    seen_ids = set(state.get('history_ids', {}).get(state_key, []))
    rows = []
    items = sorted(source_data.items(), key=lambda item: item[1].get('add_timestamp', 0))
    for record_id, record in items:
        if record_id in seen_ids:
            continue
        row = {
            'host_id': host_meta['host_id'],
            'host_name': host_meta['host_name'],
            'host_ip': host_meta['host_ip'],
            'id': record.get('id', record_id),
            'add_time': record.get('add_time', ''),
            'add_timestamp': record.get('add_timestamp', 0),
            'size': record.get('size', ''),
            'size_bytes': record.get('size_bytes', 0),
            'collector_source': os.path.basename(source_path)
        }
        if 'backup_type' in record:
            row['backup_type'] = record.get('backup_type')
        rows.append(row)
        seen_ids.add(record_id)

    if len(rows) == 0:
        return None

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    output_path = os.path.join(output_dir, '%s-%s.ndjson' % (file_prefix, timestamp))
    write_ndjson(output_path, rows)
    state.setdefault('history_ids', {})[state_key] = sorted(list(seen_ids))
    return output_path


def parse_backup_log_line(line, host_meta):
    record = None
    try:
        record = json.loads(line)
    except Exception:
        record = {
            'message': line
        }

    if not isinstance(record, dict):
        record = {
            'message': line
        }

    record['host_id'] = host_meta['host_id']
    record['host_name'] = host_meta['host_name']
    record['host_ip'] = host_meta['host_ip']
    if 'add_time' not in record or str(record.get('add_time', '')).strip() == '':
        record['add_time'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    record['collector_source'] = os.path.basename(BACKUP_LOG_FILE)
    return record


def export_backup_log(output_dir, state, host_meta):
    if not os.path.exists(BACKUP_LOG_FILE):
        return None

    stat_info = os.stat(BACKUP_LOG_FILE)
    backup_state = state.get('backup_log', {})
    last_inode = backup_state.get('inode')
    last_offset = int(backup_state.get('offset', 0))

    if last_inode != stat_info.st_ino or stat_info.st_size < last_offset:
        last_offset = 0

    rows = []
    with open(BACKUP_LOG_FILE, 'r') as fp:
        fp.seek(last_offset)
        for line in fp:
            line = line.strip()
            if line == '':
                continue
            rows.append(parse_backup_log_line(line, host_meta))
        new_offset = fp.tell()

    state['backup_log'] = {
        'inode': stat_info.st_ino,
        'offset': new_offset
    }

    if len(rows) == 0:
        return None

    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')
    output_path = os.path.join(output_dir, 'host-backup-%s.ndjson' % timestamp)
    write_ndjson(output_path, rows)
    return output_path


def cleanup_old_files(output_dir, retention_days):
    now_ts = datetime.datetime.now().timestamp()
    expire_ts = now_ts - int(retention_days) * 86400
    patterns = [
        'host-system-status-*.json',
        'host-xtrabackup-*.ndjson',
        'host-xtrabackup-inc-*.ndjson',
        'host-backup-*.ndjson',
    ]
    for pattern in patterns:
        for path in glob.glob(os.path.join(output_dir, pattern)):
            try:
                if os.path.getmtime(path) < expire_ts:
                    os.remove(path)
            except Exception:
                pass


def run(output_dir, retention_days):
    ensure_dir(output_dir)
    cleanup_old_files(output_dir, retention_days)
    state, state_path = load_state(output_dir)
    host_meta = get_host_meta()

    created_files = []
    status_path = export_status_payload(output_dir, build_status_payload(host_meta))
    created_files.append(status_path)

    xtrabackup_path = export_history_records(
        XTRABACKUP_HISTORY_FILE,
        output_dir,
        state,
        'host-xtrabackup',
        'host-xtrabackup',
        host_meta
    )
    if xtrabackup_path:
        created_files.append(xtrabackup_path)

    xtrabackup_inc_path = export_history_records(
        XTRABACKUP_INC_HISTORY_FILE,
        output_dir,
        state,
        'host-xtrabackup-inc',
        'host-xtrabackup-inc',
        host_meta
    )
    if xtrabackup_inc_path:
        created_files.append(xtrabackup_inc_path)

    backup_log_path = export_backup_log(output_dir, state, host_meta)
    if backup_log_path:
        created_files.append(backup_log_path)

    save_state(state_path, state)
    print(status_path)
    return 0


def main():
    parser = argparse.ArgumentParser(description='Collect host report source data.')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--retention-days', type=int, default=DEFAULT_RETENTION_DAYS)
    args = parser.parse_args()

    try:
        return run(args.output_dir, args.retention_days)
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
