#!/usr/bin/env python3
# coding: utf-8

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in (
    ROOT,
    os.path.join(ROOT, 'class', 'core'),
    os.path.join(ROOT, 'class', 'plugin'),
    os.path.join(ROOT, 'class', 'es', 'model'),
    os.path.join(ROOT, 'class', 'es', 'query'),
    os.path.join(ROOT, 'class', 'es', 'service'),
    os.path.join(ROOT, 'scripts'),
    os.path.join(ROOT, 'scripts', 'client'),
):
    if path not in sys.path:
        sys.path.insert(0, path)
os.chdir(ROOT)

import host_query
import report_analyser
from report_analyser import HostReportAnalyser


class EmptyEs(object):
    def get(self, *args, **kwargs):
        return {}


class SearchEs(object):
    def searchAll(self, index=None, body=None, page_size=None, scroll=None):
        return []


def build_analyser():
    analyser = HostReportAnalyser.__new__(HostReportAnalyser)
    analyser.es_available = True
    analyser.es_skip_reason = ''
    analyser._es = EmptyEs()
    analyser.thresholds = {'cpu': 80, 'memory': 80, 'disk': 80, 'ssl_cert': 14, 'ha_enabled': True}
    analyser._resolve_report_host_rows = lambda rows: rows
    analyser._build_monitor_task_section = lambda host_row, now_ts: {'monitor_task_results': []}
    analyser.now_ts = 200000
    return analyser


def status_doc(timestamp, status='running'):
    return {
        'host': {'host_id': 'H_REPORT', 'host_status': status, 'panel_title': 'report-host'},
        'system': {'cpu': 1, 'memory': 2, 'load': {'pro': 3}, 'disks': []},
        'add_timestamp': timestamp,
        'add_time': '1970-01-03 00:00:00',
    }


def build_report(report_time, created_time):
    analyser = build_analyser()
    window = {
        'report_date': '1970-01-03',
        'report_time': '1970-01-03 07:33:20',
        'start_time': '1970-01-02 07:33:20',
        'end_time': '1970-01-03 07:33:20',
        'start_date': '1970-01-02',
        'end_date': '1970-01-03',
        'start_timestamp': 113600,
        'end_timestamp': 200000,
    }
    row = {
        'host_id': 'H_REPORT', 'host_name': '日报主机', 'host_remark': '日报主机',
        'ip': '10.0.0.20', 'addtime': created_time, '_collected_host_name_resolved': True,
        'is_pve': False,
    }
    docs = [status_doc(report_time)] if report_time else []
    return analyser.build_single_host_report(
        row, {'status': docs, 'xtrabackup': [], 'xtrabackup_inc': [], 'backup': []}, window
    )[1]


def main():
    query = host_query.buildLatestStatusSearchBody(
        {'host_id': 'H_REPORT', 'ip': '10.0.0.20'}, end_timestamp=200000
    )
    filters = query['query']['bool']['filter']
    assert {'range': {'add_timestamp': {'lte': 200000}}} in filters, query

    short_gap = build_report(200000 - 901, 1000)
    assert 'stale_system_status' in short_gap['validation']['errors'], short_gap
    assert 'reporting_stale_24h' not in short_gap['validation']['errors'], short_gap
    assert not short_gap['reporting_abnormal'], short_gap

    stale = build_report(200000 - 86400, 1000)
    assert 'reporting_stale_24h' in stale['validation']['errors'], stale
    assert stale['reporting_abnormal'], stale
    assert stale['reporting_freshness'] == 'stale', stale
    assert len([tip for tip in stale['error_tips'] if '超过24小时未上报' in tip]) == 1, stale
    assert '系统监控状态异常' not in stale['error_tips'], stale

    never = build_report(None, 200000 - 86400)
    assert 'never_reported_24h' in never['validation']['errors'], never
    assert never['reporting_freshness'] == 'never_reported', never

    pending = build_report(None, 200000 - 86399)
    assert 'never_reported_24h' not in pending['validation']['errors'], pending
    assert pending['reporting_freshness'] == 'pending', pending

    future_excluded = host_query.buildLatestStatusQuery(
        {'host_id': 'H_REPORT'}, end_timestamp=200000
    )
    assert future_excluded['bool']['filter'][-1]['range']['add_timestamp']['lte'] == 200000

    analyser = build_analyser()
    analyser._es = SearchEs()
    analyser.log = lambda message: None
    window = {
        'report_date': '1970-01-03', 'start_timestamp': 113600, 'end_timestamp': 200000
    }
    host_row = {'host_id': 'H_REPORT', 'host_name': '日报主机', 'ip': '10.0.0.20'}
    original_latest = report_analyser.host_status_service_utils.getLatestStatusDocsAtOrBefore
    report_analyser.host_status_service_utils.getLatestStatusDocsAtOrBefore = lambda rows, end_timestamp, es_client=None: {
        'storage_available': True,
        'status_docs': {'H_REPORT': status_doc(100000)}
    }
    try:
        groups = analyser.load_raw_groups([host_row], window)
    finally:
        report_analyser.host_status_service_utils.getLatestStatusDocsAtOrBefore = original_latest
    assert groups['H_REPORT']['status'][0]['add_timestamp'] == 100000, groups

    print('reporting freshness report: ok')


if __name__ == '__main__':
    main()
