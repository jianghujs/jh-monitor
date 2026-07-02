#!/usr/bin/env python3
# coding: utf-8
"""Smoke test for report_analyser.py.

Examples:
  python3 /www/server/jh-monitor/test/test_report_analyser_host.py
  python3 /www/server/jh-monitor/test/test_report_analyser_host.py --host-id H_xxx
  python3 /www/server/jh-monitor/test/test_report_analyser_host.py --host-id H_xxx --report-date 2026-07-02

What it does:
  1. Always runs: python3 -m py_compile /www/server/jh-monitor/scripts/report_analyser.py
  2. If --host-id is provided, loads raw ES docs for that host/date and builds a
     single-host report in memory. It does not write report docs or send messages.
"""

import argparse
import datetime
import json
import os
import py_compile
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT_DIR, 'class', 'core')
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
ES_MODEL_DIR = os.path.join(ROOT_DIR, 'class', 'es', 'model')
CLIENT_DIR = os.path.join(ROOT_DIR, 'scripts', 'client')
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')
REPORT_ANALYSER_FILE = os.path.join(SCRIPTS_DIR, 'report_analyser.py')

for path in (ROOT_DIR, CORE_DIR, PLUGIN_DIR, ES_MODEL_DIR, CLIENT_DIR, SCRIPTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(ROOT_DIR)

import jh
import value_tool
from report_analyser import HostReportAnalyser, h_api


def json_default(value):
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return str(value)


def load_host_row(host_id):
    rows = jh.M('view01_host').field(h_api.host_field).where('host_id=?', (host_id,)).select()
    if isinstance(rows, str) or not rows:
        return None
    return rows[0]


def build_summary(doc_id, document):
    return {
        'doc_id': doc_id,
        'host_id': document.get('host_id', ''),
        'host_name': document.get('host_name', ''),
        'host_ip': document.get('host_ip', ''),
        'report_date': document.get('report_date', ''),
        'is_abnormal': bool(document.get('is_abnormal')),
        'validation': document.get('validation', {}),
        'raw_counts': value_tool.getNested(document, ['extra_info', 'raw_counts'], {}),
        'summary_tips': document.get('summary_tips', []),
        'error_tips': document.get('error_tips', []),
        'backup_tips_count': len(document.get('backup_tips', []) or []),
        'backup_tips': document.get('backup_tips', []),
        'html_length': len(str(document.get('html_content', '') or '')),
    }


class NonWritingAnalyser(HostReportAnalyser):
    """Avoid ES get failure for delivery state when running a local smoke test."""

    def __init__(self, *args, **kwargs):
        super(NonWritingAnalyser, self).__init__(*args, **kwargs)

    def _get_doc(self, index_name, doc_id):
        try:
            return super(NonWritingAnalyser, self)._get_doc(index_name, doc_id)
        except Exception:
            return {}


def main():
    parser = argparse.ArgumentParser(description='Smoke test report_analyser.py for a single host.')
    parser.add_argument('--host-id', default='', help='指定 host_id；不指定时只做 py_compile')
    parser.add_argument('--report-date', default='', help='报告日期 YYYY-MM-DD，默认今天')
    parser.add_argument('--print-html', action='store_true', help='输出 HTML 片段，默认只输出摘要 JSON')
    args = parser.parse_args()

    py_compile.compile(REPORT_ANALYSER_FILE, doraise=True)
    print('[OK] py_compile: %s' % REPORT_ANALYSER_FILE)

    if not args.host_id:
        return 0

    now_ts = int(time.time())
    analyser = NonWritingAnalyser(now_ts=now_ts, logger=lambda msg: print(str(msg), file=sys.stderr))
    report_date = args.report_date or time.strftime('%Y-%m-%d', time.localtime(now_ts))
    window = analyser.get_report_window(report_date)

    host_row = load_host_row(args.host_id)
    if not host_row:
        print(json.dumps({
            'status': False,
            'msg': 'host_id not found: %s' % args.host_id
        }, ensure_ascii=False, indent=2))
        return 2

    groups = analyser.load_raw_groups([host_row], window)
    host_group = groups.get(args.host_id, {})
    doc_id, document = analyser.build_single_host_report(host_row, host_group, window)
    print(json.dumps(build_summary(doc_id, document), ensure_ascii=False, indent=2, default=json_default))
    if args.print_html:
        print('\n===== html_content =====')
        print(document.get('html_content', ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
