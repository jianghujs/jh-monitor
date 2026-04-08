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

from get_host_info import get_host_ip, is_pve_machine
from get_pve_system_status import build_system_status as build_pve_system_status

DEFAULT_OUTPUT_DIR = os.environ.get(
    'REPORT_COLLECTOR_OUTPUT_DIR',
    '/home/ansible_user/jh-monitor-data'
)
DEFAULT_HOST_ID_FILE = os.environ.get(
    'JH_MONITOR_HOST_ID_FILE',
    os.path.join(DEFAULT_OUTPUT_DIR, 'host_id')
)
DEFAULT_RETENTION_DAYS = 30
STATE_FILE_NAME = '.report-collector-state.json'


def log(message):
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sys.stderr.write('[report-collector] %s %s\n' % (now, message))
    sys.stderr.flush()


def log_exception(stage):
    log('%s failed:\n%s' % (stage, traceback.format_exc().rstrip()))


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


def load_state(output_dir):
    state_path = os.path.join(output_dir, STATE_FILE_NAME)
    if not os.path.exists(state_path):
        log('state file not found, use empty state: %s' % state_path)
        return {}, state_path
    try:
        with open(state_path, 'r') as fp:
            state = json.load(fp)
        log('state loaded: %s' % state_path)
        return state, state_path
    except Exception:
        log_exception('load_state')
        return {}, state_path


def save_state(state_path, state):
    atomic_write_json(state_path, state)
    log('state saved: %s' % state_path)


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
    saved_host_id = safe_read(DEFAULT_HOST_ID_FILE)
    if saved_host_id:
        return saved_host_id
    machine_id = safe_read('/etc/machine-id')
    if machine_id:
        return machine_id
    return socket.gethostname()


def get_host_meta():
    return {
        'host_id': get_host_id(),
        'host_name': socket.gethostname(),
        'host_ip': get_primary_ip()
    }


def export_status_payload(output_dir, payload, file_prefix='host-debian-system-status'):
    file_date = datetime.datetime.now().strftime('%Y%m%d')
    output_path = os.path.join(output_dir, '%s-%s.json' % (file_prefix, file_date))
    append_ndjson(output_path, [payload])
    log('status payload exported: %s' % output_path)
    return output_path


def cleanup_old_files(output_dir, retention_days):
    now_ts = datetime.datetime.now().timestamp()
    expire_ts = now_ts - int(retention_days) * 86400
    patterns = [
        'host-debian-system-status-*.json',
        'host-pve-system-status-*.json',
        'host-debian-xtrabackup-*.ndjson',
        'host-debian-xtrabackup-inc-*.ndjson',
        'host-debian-backup-*.ndjson',
    ]
    for pattern in patterns:
        for path in glob.glob(os.path.join(output_dir, pattern)):
            try:
                if os.path.getmtime(path) < expire_ts:
                    os.remove(path)
                    log('expired file removed: %s' % path)
            except Exception:
                log_exception('cleanup_old_files')


def collect_status_payloads(host_meta, is_pve=None):
    if is_pve is None:
        is_pve = is_pve_machine()
    if is_pve:
        log('collect pve system status')
        return [
            ('host-pve-system-status', build_pve_system_status(host_meta))
        ]
    from get_debian_system_status import build_system_status as build_debian_system_status
    log('collect debian system status')
    return [
        ('host-debian-system-status', build_debian_system_status(host_meta))
    ]


def run(output_dir, retention_days):
    log('collector start, output_dir=%s retention_days=%s' % (output_dir, retention_days))
    ensure_dir(output_dir)
    log('output dir ready: %s' % output_dir)
    cleanup_old_files(output_dir, retention_days)
    state, state_path = load_state(output_dir)
    host_meta = get_host_meta()
    is_pve = is_pve_machine()
    log(
        'host detected: host_id=%s host_name=%s host_ip=%s is_pve=%s'
        % (host_meta['host_id'], host_meta['host_name'], host_meta['host_ip'], is_pve)
    )

    created_files = []
    for file_prefix, payload in collect_status_payloads(host_meta, is_pve=is_pve):
        log('export status payload: %s' % file_prefix)
        status_path = export_status_payload(output_dir, payload, file_prefix=file_prefix)
        created_files.append(status_path)

    if not is_pve:
        from get_debian_system_status import collect_extra_exports as collect_debian_extra_exports
        log('collect debian extra exports')
        created_files.extend(collect_debian_extra_exports(output_dir, state, host_meta))
    else:
        log('skip debian extra exports on pve host')

    save_state(state_path, state)
    if created_files:
        log('collector finished, created_files=%s' % json.dumps(created_files, ensure_ascii=False))
        print(created_files[0])
    else:
        log('collector finished, no files created')
    return 0


def main():
    parser = argparse.ArgumentParser(description='Collect host report source data.')
    parser.add_argument('--output-dir', default=DEFAULT_OUTPUT_DIR)
    parser.add_argument('--retention-days', type=int, default=DEFAULT_RETENTION_DAYS)
    args = parser.parse_args()

    try:
        return run(args.output_dir, args.retention_days)
    except Exception:
        log_exception('main')
        return 1


if __name__ == '__main__':
    sys.exit(main())
