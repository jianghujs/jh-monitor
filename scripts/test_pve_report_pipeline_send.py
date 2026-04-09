#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CORE_DIR = os.path.join(ROOT_DIR, 'class', 'core')
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
ES_MODEL_DIR = os.path.join(ROOT_DIR, 'class', 'es', 'model')
CLIENT_DIR = os.path.join(ROOT_DIR, 'scripts', 'client')

for path in (CURRENT_DIR, CORE_DIR, PLUGIN_DIR, ES_MODEL_DIR, CLIENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

import jh
import report_analyser as report_analyser_module
import report_sender as report_sender_module
from report_analyser import HostReportAnalyser, PAGE_SIZE, h_api
from report_sender import HostReportSender


def parse_csv_args(raw_items):
    values = []
    for item in raw_items or []:
        for value in str(item or '').split(','):
            value = value.strip()
            if value != '' and value not in values:
                values.append(value)
    return values


def is_true(value):
    return value in (1, True, '1', 'true', 'True', 'yes', 'YES', 'on', 'ON')


def nested_get(data, path, default=None):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
        if current is None:
            return default
    return current


def load_pve_hosts(host_ids=None, host_ips=None):
    host_ids = set(host_ids or [])
    host_ips = set(host_ips or [])
    host_rows = jh.M('view01_host').field(h_api.host_field).order('id desc').select()
    if isinstance(host_rows, str) or host_rows is None:
        return []

    pve_rows = []
    for row in host_rows:
        if not is_true(row.get('is_pve')):
            continue
        if host_ids and str(row.get('host_id', '')) not in host_ids:
            continue
        if host_ips and str(row.get('ip', '')) not in host_ips:
            continue
        pve_rows.append(row)
    return pve_rows


def build_single_summary(doc, report_date):
    return {
        'doc_id': '{0}:{1}'.format(report_date, doc.get('host_id', '')),
        'host_id': doc.get('host_id', ''),
        'host_name': doc.get('host_name', ''),
        'host_ip': doc.get('host_ip', ''),
        'is_abnormal': bool(doc.get('is_abnormal')),
        'validation': doc.get('validation', {}),
        'delivery': doc.get('delivery', {}),
        'error_tips': doc.get('error_tips', [])[:10],
        'summary_tips_count': len(doc.get('summary_tips', []) or []),
        'latest_status_time': nested_get(doc, ['extra_info', 'latest_status_time'], ''),
        'raw_counts': nested_get(doc, ['extra_info', 'raw_counts'], {}),
    }


def build_overview_summary(doc):
    if not isinstance(doc, dict):
        return {}
    return {
        'title': doc.get('title', ''),
        'validation': doc.get('validation', {}),
        'delivery': doc.get('delivery', {}),
        'host_overview_info': doc.get('host_overview_info', {}),
        'exception_host_summary_tips_count': len(doc.get('exception_host_summary_tips', []) or []),
        'single_host_report_list_count': len(doc.get('single_host_report_list', []) or []),
    }


def install_dry_run_hooks():
    sent_messages = []
    original_notify = jh.notifyMessage
    original_get_notify_data = jh.getNotifyData

    def fake_get_notify_data(is_parse=False):
        return {
            'email': {
                'enable': True,
                'data': {
                    'to_mail_addr': 'dry-run@example.invalid'
                }
            }
        }

    def fake_notify(msg, msgtype='text', title='江湖云监控通知', stype='common', trigger_time=300, is_write_log=True):
        sent_messages.append({
            'title': title,
            'stype': stype,
            'msgtype': msgtype,
            'trigger_time': trigger_time,
            'content_length': len(str(msg or ''))
        })
        print('[dry-run-send] title={0} stype={1} msgtype={2} content_length={3}'.format(
            title,
            stype,
            msgtype,
            len(str(msg or ''))
        ))
        return True

    jh.getNotifyData = fake_get_notify_data
    jh.notifyMessage = fake_notify
    report_sender_module.jh.getNotifyData = fake_get_notify_data
    report_sender_module.jh.notifyMessage = fake_notify
    report_analyser_module.jh.getNotifyData = fake_get_notify_data
    report_analyser_module.jh.notifyMessage = fake_notify
    return sent_messages, original_notify, original_get_notify_data


def restore_dry_run_hooks(original_notify, original_get_notify_data):
    jh.notifyMessage = original_notify
    jh.getNotifyData = original_get_notify_data
    report_sender_module.jh.notifyMessage = original_notify
    report_sender_module.jh.getNotifyData = original_get_notify_data
    report_analyser_module.jh.notifyMessage = original_notify
    report_analyser_module.jh.getNotifyData = original_get_notify_data


def configure_report_indices(use_live_index=False):
    single_index = 'host-report-single'
    overview_index = 'host-report-overview'
    if not use_live_index:
        single_index = 'host-report-single-test'
        overview_index = 'host-report-overview-test'

    report_analyser_module.SINGLE_REPORT_INDEX = single_index
    report_analyser_module.OVERVIEW_REPORT_INDEX = overview_index
    report_sender_module.SINGLE_REPORT_INDEX = single_index
    report_sender_module.OVERVIEW_REPORT_INDEX = overview_index
    return single_index, overview_index


def main():
    parser = argparse.ArgumentParser(description='测试 PVE 报告统计与发送流程')
    parser.add_argument('--report-date', default='', help='报告日期，格式 YYYY-MM-DD，默认取昨天')
    parser.add_argument('--host-id', action='append', default=[], help='指定 host_id，可重复或逗号分隔')
    parser.add_argument('--host-ip', action='append', default=[], help='指定 host_ip，可重复或逗号分隔')
    parser.add_argument('--list-hosts', action='store_true', help='仅列出当前 PVE 主机')
    parser.add_argument('--skip-analysis', action='store_true', help='跳过统计阶段，直接测试发送已有报告')
    parser.add_argument('--send', action='store_true', help='执行发送阶段')
    parser.add_argument('--dry-run', action='store_true', help='发送时不真正下发通知，只打印发送摘要')
    parser.add_argument('--use-live-index', action='store_true', help='读写正式报告索引，默认使用 *-test 测试索引')
    args = parser.parse_args()

    host_ids = parse_csv_args(args.host_id)
    host_ips = parse_csv_args(args.host_ip)
    host_rows = load_pve_hosts(host_ids=host_ids, host_ips=host_ips)

    if args.list_hosts:
        print(json.dumps([
            {
                'host_id': row.get('host_id', ''),
                'host_name': row.get('host_name', ''),
                'host_ip': row.get('ip', ''),
                'host_status': row.get('host_status', ''),
            }
            for row in host_rows
        ], ensure_ascii=False, indent=2))
        return 0

    if len(host_rows) == 0:
        print(json.dumps({
            'status': 'error',
            'message': '未找到匹配的 PVE 主机',
            'host_ids': host_ids,
            'host_ips': host_ips,
        }, ensure_ascii=False, indent=2))
        return 1

    single_index, overview_index = configure_report_indices(use_live_index=args.use_live_index)
    analyser = HostReportAnalyser()
    report_date = analyser.get_report_window(args.report_date or None)['report_date']

    result = {
        'report_date': report_date,
        'report_indices': {
            'single': single_index,
            'overview': overview_index,
            'mode': 'live' if args.use_live_index else 'test',
        },
        'target_hosts': [
            {
                'host_id': row.get('host_id', ''),
                'host_name': row.get('host_name', ''),
                'host_ip': row.get('ip', ''),
            }
            for row in host_rows
        ]
    }

    if not args.skip_analysis:
        analysis_result = analyser.run_analysis(host_rows=host_rows, report_date=report_date)
        result['analysis'] = analysis_result
    else:
        result['analysis'] = {'status': 'skipped', 'reason': 'skip_analysis', 'report_date': report_date}

    sender = HostReportSender()
    selected_host_ids = [row.get('host_id') for row in host_rows if row.get('host_id')]
    single_documents = sender._es.searchAll(
        index=single_index,
        body=sender._build_single_report_delivery_query(selected_host_ids, report_date),
        page_size=PAGE_SIZE,
        scroll='1m'
    ) if selected_host_ids else []
    single_documents = sorted(single_documents, key=lambda item: (item.get('host_name', ''), item.get('host_id', '')))

    overview_document = sender._es.get(overview_index, report_date)
    if isinstance(overview_document, dict):
        overview_document = overview_document.get('_source', overview_document)

    result['reports'] = {
        'overview': build_overview_summary(overview_document),
        'single_total': len(single_documents),
        'single_ready': len([doc for doc in single_documents if nested_get(doc, ['validation', 'is_complete'], False)]),
        'single_abnormal': len([doc for doc in single_documents if doc.get('is_abnormal')]),
        'single_documents': [build_single_summary(doc, report_date) for doc in single_documents],
    }

    if args.send:
        sent_messages = []
        original_notify = None
        original_get_notify_data = None
        try:
            if args.dry_run:
                sent_messages, original_notify, original_get_notify_data = install_dry_run_hooks()
            send_result = sender.run_delivery(
                due_rows=host_rows,
                enabled_rows=host_rows,
                report_config={row.get('host_id'): {'enabled': True} for row in host_rows if row.get('host_id')},
                report_date=report_date
            )
            result['send'] = send_result
            if args.dry_run:
                result['dry_run_messages'] = sent_messages
        finally:
            if args.dry_run and original_notify is not None and original_get_notify_data is not None:
                restore_dry_run_hooks(original_notify, original_get_notify_data)
    else:
        result['send'] = {'status': 'skipped', 'reason': 'send_disabled', 'report_date': report_date}

    print(json.dumps(result, ensure_ascii=False, indent=2))

    send_status = result.get('send', {}).get('status', '')
    if send_status in ('failed', 'blocked'):
        return 2
    analysis_status = result.get('analysis', {}).get('status', '')
    if analysis_status not in ('ok', 'skipped'):
        return 3
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
