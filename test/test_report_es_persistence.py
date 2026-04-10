#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import os
import sys
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT_DIR, 'class', 'core')
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
ES_MODEL_DIR = os.path.join(ROOT_DIR, 'class', 'es', 'model')
CLIENT_DIR = os.path.join(ROOT_DIR, 'scripts', 'client')
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')

for path in (ROOT_DIR, CORE_DIR, PLUGIN_DIR, ES_MODEL_DIR, CLIENT_DIR, SCRIPTS_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(ROOT_DIR)

import jh
import report_analyser as report_analyser_module
import report_sender as report_sender_module
from config_api import config_api
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


def normalize_response(response):
    if hasattr(response, 'body'):
        return response.body
    if hasattr(response, 'to_dict'):
        return response.to_dict()
    return response or {}


def is_true(value):
    return value in (1, True, '1', 'true', 'True', 'yes', 'YES', 'on', 'ON')


def configure_report_indices(use_live_index=True):
    single_index = 'host-report-single'
    overview_index = 'host-report-overview'
    single_data_stream_prefix = 'host-report-single'
    overview_data_stream_prefix = 'host-report-overview'
    if not use_live_index:
        single_index = 'host-report-single-test'
        overview_index = 'host-report-overview-test'
        single_data_stream_prefix = 'host-report-test-single'
        overview_data_stream_prefix = 'host-report-test-overview'

    report_analyser_module.SINGLE_REPORT_INDEX = single_index
    report_analyser_module.OVERVIEW_REPORT_INDEX = overview_index
    report_analyser_module.SINGLE_REPORT_DATA_STREAM_PREFIX = single_data_stream_prefix
    report_analyser_module.OVERVIEW_REPORT_DATA_STREAM_PREFIX = overview_data_stream_prefix
    report_sender_module.SINGLE_REPORT_INDEX = single_index
    report_sender_module.OVERVIEW_REPORT_INDEX = overview_index
    return single_index, overview_index, single_data_stream_prefix, overview_data_stream_prefix


def build_monthly_data_stream_name(prefix, report_date):
    month_text = str(report_date or '')[:7]
    return '{0}-{1}'.format(prefix, month_text)


def load_target_hosts(host_ids=None, host_ips=None, scheduled_only=False):
    host_ids = set(host_ids or [])
    host_ips = set(host_ips or [])

    scheduled_host_ids = set()
    if scheduled_only:
        dispatch_config = config_api().getReportDispatchConfigData() or {}
        scheduled_host_ids = set(dispatch_config.get('report_host_ids', []) or [])

    host_rows = jh.M('view01_host').field(h_api.host_field).order('id desc').select()
    if isinstance(host_rows, str) or host_rows is None:
        return []

    result = []
    for row in host_rows:
        host_id = str(row.get('host_id', '')).strip()
        host_ip = str(row.get('ip', '')).strip()
        if host_ids and host_id not in host_ids:
            continue
        if host_ips and host_ip not in host_ips:
            continue
        if scheduled_only and host_id not in scheduled_host_ids:
            continue
        result.append(row)
    return result


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


def fetch_doc(es_client, index_name, doc_id):
    doc = es_client.get(index_name, doc_id)
    doc = normalize_response(doc)
    if isinstance(doc, dict) and '_source' in doc:
        return doc.get('_source')
    if isinstance(doc, dict) and doc:
        return doc
    return None


def build_single_doc_summary(doc, doc_id):
    if not isinstance(doc, dict):
        return {
            'doc_id': doc_id,
            'exists': False
        }
    return {
        'doc_id': doc_id,
        'exists': True,
        'report_type': doc.get('report_type', ''),
        'host_id': doc.get('host_id', ''),
        'host_name': doc.get('host_name', ''),
        'host_ip': doc.get('host_ip', ''),
        'report_date': doc.get('report_date', ''),
        'validation_status': (doc.get('validation') or {}).get('status', ''),
        'validation_complete': bool((doc.get('validation') or {}).get('is_complete')),
        'delivery_status': (doc.get('delivery') or {}).get('status', ''),
        'html_length': len(str(doc.get('html_content', '') or '')),
    }


def build_overview_doc_summary(doc, doc_id):
    if not isinstance(doc, dict):
        return {
            'doc_id': doc_id,
            'exists': False
        }
    return {
        'doc_id': doc_id,
        'exists': True,
        'report_type': doc.get('report_type', ''),
        'title': doc.get('title', ''),
        'report_date': doc.get('report_date', ''),
        'validation_status': (doc.get('validation') or {}).get('status', ''),
        'validation_complete': bool((doc.get('validation') or {}).get('is_complete')),
        'delivery_status': (doc.get('delivery') or {}).get('status', ''),
        'html_length': len(str(doc.get('html_content', '') or '')),
        'single_host_report_list_count': len(doc.get('single_host_report_list', []) or []),
    }


def search_single_docs(es_client, sender, index_name, host_ids, report_date):
    if len(host_ids) == 0:
        return []
    return es_client.searchAll(
        index=index_name,
        body=sender._build_single_report_delivery_query(host_ids, report_date),
        page_size=PAGE_SIZE,
        scroll='1m'
    )


def search_latest_data_stream_doc(es_client, index_name, report_date, host_id=''):
    filters = [{'term': {'report_date': report_date}}]
    if host_id:
        filters.append({
            'bool': {
                'should': [
                    {'term': {'host_id.keyword': host_id}},
                    {'term': {'host_id': host_id}}
                ],
                'minimum_should_match': 1
            }
        })
    response = es_client.search(
        index=index_name,
        body={
            'size': 1,
            'query': {
                'bool': {
                    'filter': filters
                }
            },
            'sort': [
                {'@timestamp': {'order': 'desc'}},
                {'report_time': {'order': 'desc'}}
            ]
        }
    )
    response = normalize_response(response)
    hits = ((response.get('hits') or {}).get('hits') or [])
    if len(hits) == 0:
        return None
    return hits[0].get('_source', {})


def build_args():
    parser = argparse.ArgumentParser(description='检查服务器报告写入 ES 后是否真实存在')
    parser.add_argument('--report-date', default='', help='报告日期，格式 YYYY-MM-DD，默认取当前窗口日期')
    parser.add_argument('--host-id', action='append', default=[], help='指定 host_id，可重复或逗号分隔')
    parser.add_argument('--host-ip', action='append', default=[], help='指定 host_ip，可重复或逗号分隔')
    parser.add_argument('--scheduled-only', action='store_true', help='只检查已加入服务器报告配置的主机')
    parser.add_argument('--list-hosts', action='store_true', help='仅输出匹配到的主机')
    parser.add_argument('--skip-analysis', action='store_true', help='不生成报告，只检查当前 ES 中是否已有报告')
    parser.add_argument('--send', action='store_true', help='在检查写入后继续执行发送流程')
    parser.add_argument('--dry-run', action='store_true', help='发送时不真实发通知，只记录发送摘要')
    parser.add_argument('--use-test-index', action='store_true', help='使用 *-test 测试索引，默认使用正式索引')
    return parser.parse_args()


def main():
    args = build_args()
    use_live_index = not args.use_test_index
    single_index, overview_index, single_data_stream_prefix, overview_data_stream_prefix = configure_report_indices(use_live_index=use_live_index)

    host_ids = parse_csv_args(args.host_id)
    host_ips = parse_csv_args(args.host_ip)
    host_rows = load_target_hosts(
        host_ids=host_ids,
        host_ips=host_ips,
        scheduled_only=args.scheduled_only
    )

    if args.list_hosts:
        print(json.dumps([
            {
                'host_id': row.get('host_id', ''),
                'host_name': row.get('host_name', ''),
                'host_ip': row.get('ip', ''),
                'is_pve': is_true(row.get('is_pve')),
                'is_jhpanel': is_true(row.get('is_jhpanel')),
            }
            for row in host_rows
        ], ensure_ascii=False, indent=2))
        return 0

    if len(host_rows) == 0:
        print(json.dumps({
            'status': 'error',
            'message': '未找到匹配的主机',
            'host_ids': host_ids,
            'host_ips': host_ips,
            'scheduled_only': args.scheduled_only,
        }, ensure_ascii=False, indent=2))
        return 1

    analyser = HostReportAnalyser()
    sender = HostReportSender(es_client=analyser._es)
    report_date = analyser.get_report_window(args.report_date or None)['report_date']
    single_data_stream = build_monthly_data_stream_name(single_data_stream_prefix, report_date)
    overview_data_stream = build_monthly_data_stream_name(overview_data_stream_prefix, report_date)
    selected_host_ids = [row.get('host_id') for row in host_rows if row.get('host_id')]
    overview_doc_id = report_date
    single_doc_ids = ['{0}:{1}'.format(report_date, host_id) for host_id in selected_host_ids]

    result = {
        'status': 'ok',
        'report_date': report_date,
        'indexes': {
            'single': single_index,
            'overview': overview_index,
            'single_data_stream': single_data_stream,
            'overview_data_stream': overview_data_stream,
            'mode': 'live' if use_live_index else 'test'
        },
        'es_config': {
            'hosts': getattr(analyser._es, '_es_hosts', []),
            'username': getattr(analyser._es, '_username', ''),
            'config_path': getattr(analyser._es, '_config_path', ''),
        },
        'target_hosts': [
            {
                'host_id': row.get('host_id', ''),
                'host_name': row.get('host_name', ''),
                'host_ip': row.get('ip', ''),
            }
            for row in host_rows
        ],
    }

    if not args.skip_analysis:
        try:
            analysis_result = analyser.run_analysis(host_rows=host_rows, report_date=report_date)
            result['analysis'] = analysis_result
        except Exception as ex:
            result['status'] = 'error'
            result['analysis'] = {
                'status': 'exception',
                'message': str(ex),
                'es_error': str(analyser._es.getError()) if analyser._es.getError() else ''
            }
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 2
    else:
        result['analysis'] = {
            'status': 'skipped',
            'reason': 'skip_analysis'
        }

    overview_doc = fetch_doc(analyser._es, overview_index, overview_doc_id)
    single_doc_summaries = []
    for doc_id in single_doc_ids:
        single_doc = fetch_doc(analyser._es, single_index, doc_id)
        single_doc_summaries.append(build_single_doc_summary(single_doc, doc_id))

    searched_single_docs = search_single_docs(analyser._es, sender, single_index, selected_host_ids, report_date)
    overview_ds_doc = search_latest_data_stream_doc(analyser._es, overview_data_stream, report_date)
    single_ds_doc_summaries = []
    for host_id in selected_host_ids:
        single_ds_doc = search_latest_data_stream_doc(analyser._es, single_data_stream, report_date, host_id=host_id)
        single_ds_doc_summaries.append(build_single_doc_summary(single_ds_doc, '{0}:{1}'.format(report_date, host_id)))

    result['es_checks'] = {
        'overview': build_overview_doc_summary(overview_doc, overview_doc_id),
        'overview_data_stream': build_overview_doc_summary(overview_ds_doc, overview_doc_id),
        'single_docs_by_get': single_doc_summaries,
        'single_docs_in_data_stream': single_ds_doc_summaries,
        'single_doc_get_found_count': len([item for item in single_doc_summaries if item.get('exists')]),
        'single_doc_data_stream_found_count': len([item for item in single_ds_doc_summaries if item.get('exists')]),
        'single_doc_search_found_count': len(searched_single_docs),
        'single_doc_search_host_ids': [doc.get('host_id', '') for doc in searched_single_docs],
        'es_last_error': str(analyser._es.getError()) if analyser._es.getError() else '',
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
                report_config={host_id: {'enabled': True} for host_id in selected_host_ids},
                report_date=report_date
            )
            result['send'] = send_result
            if args.dry_run:
                result['dry_run_messages'] = sent_messages
        except Exception as ex:
            result['status'] = 'error'
            result['send'] = {
                'status': 'exception',
                'message': str(ex),
                'es_error': str(sender._es.getError()) if sender._es.getError() else ''
            }
        finally:
            if args.dry_run and original_notify is not None and original_get_notify_data is not None:
                restore_dry_run_hooks(original_notify, original_get_notify_data)
    else:
        result['send'] = {
            'status': 'skipped',
            'reason': 'send_disabled'
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))

    if result.get('status') != 'ok':
        return 3
    if not result['es_checks']['overview'].get('exists'):
        return 4
    if result['es_checks']['single_doc_get_found_count'] != len(selected_host_ids):
        return 5
    if not result['es_checks']['overview_data_stream'].get('exists'):
        return 6
    if result['es_checks']['single_doc_data_stream_found_count'] != len(selected_host_ids):
        return 7
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
