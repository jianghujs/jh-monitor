#!/usr/bin/env python3
# coding: utf-8

import argparse

from flask import Flask

from common.env import setup_test_env
from common.notify import NotifyDryRun
from common.response import parse_api_response, parse_csv_args, print_json
from common.timing import MethodTimer, StepLogger


setup_test_env(__file__)

import jh
import report_analyser as report_analyser_module
import report_sender as report_sender_module
from config_api import config_api
from host_api import host_api


h_api = host_api()


def build_form_data(args, fallback_host_ids=None):
    data = {}
    host_ids = parse_csv_args(args.host_id)
    if not host_ids:
        host_ids = list(fallback_host_ids or [])
    if host_ids:
        data['report_host_ids[]'] = host_ids
    for key in ('cpu', 'memory', 'disk', 'ssl_cert'):
        value = getattr(args, key)
        if value is not None:
            data[key] = str(value)
    if args.ha_enabled is not None:
        data['ha_enabled'] = 'true' if args.ha_enabled else 'false'
    return data


def summarize_send_result(result, captured_messages):
    data = result.get('data') if isinstance(result, dict) else None
    delivery_result = data.get('delivery_result', {}) if isinstance(data, dict) else {}
    analysis_result = data.get('analysis_result', {}) if isinstance(data, dict) else {}
    return {
        'status': result.get('status'),
        'msg': result.get('msg'),
        'analysis_status': analysis_result.get('status'),
        'delivery_status': delivery_result.get('status'),
        'delivery_reason': delivery_result.get('reason'),
        'delivery_error': delivery_result.get('error'),
        'report_date': delivery_result.get('report_date') or analysis_result.get('report_date'),
        'overview_sent': delivery_result.get('overview_sent'),
        'single_success': delivery_result.get('single_success'),
        'single_failed': delivery_result.get('single_failed'),
        'single_skipped': delivery_result.get('single_skipped'),
        'missing_host_ids': data.get('missing_host_ids', []) if isinstance(data, dict) else [],
        'recipients': data.get('recipients', []) if isinstance(data, dict) else [],
        'captured_messages': captured_messages,
    }


def collect_precheck(api):
    email_enabled, recipients = api._isEmailNotifyReady()
    report_config = api._getRawReportConfig()
    dispatch_config = {
        'enabled': bool(report_config.get('enabled', False)),
        'report_host_ids': api._normalizeReportHostIds(report_config.get('report_host_ids', [])),
        'cron': report_config.get('cron', api._getDefaultReportCron()),
    }
    configured_host_ids = list(dispatch_config.get('report_host_ids', []))
    host_rows = jh.M('view01_host').field(h_api.host_field).select()
    if isinstance(host_rows, str) or host_rows is None:
        host_rows = []
    host_row_map = {}
    for row in host_rows:
        if not isinstance(row, dict):
            continue
        host_id = str(row.get('host_id', '')).strip()
        if host_id:
            host_row_map[host_id] = row
    selected_rows = [host_row_map[host_id] for host_id in configured_host_ids if host_id in host_row_map]
    missing_host_ids = [host_id for host_id in configured_host_ids if host_id not in host_row_map]
    ok = len(selected_rows) > 0
    if not configured_host_ids:
        msg = '请先在服务器报告配置中选择报告主机!'
    elif not ok:
        msg = '选中的报告主机不存在或已被删除，请重新选择!'
    else:
        msg = 'ok'
    return {
        'email_enabled': email_enabled,
        'recipients': recipients,
        'dispatch_config': dispatch_config,
        'selected_hosts_ok': ok,
        'selected_hosts_msg': msg,
        'selected_host_count': len(selected_rows),
        'selected_host_ids': [row.get('host_id') for row in selected_rows if isinstance(row, dict)],
        'missing_host_ids': missing_host_ids or [],
    }


def build_trace_patches():
    return [
        (config_api, '_isEmailNotifyReady', 'config._isEmailNotifyReady'),
        (config_api, '_buildTestReportHostRows', 'config._buildTestReportHostRows'),
        (config_api, '_normalizeReportConfig', 'config._normalizeReportConfig'),
        (config_api, 'testSendReportMailApi', 'config.testSendReportMailApi'),
        (report_analyser_module.HostReportAnalyser, 'run_analysis', 'analyser.run_analysis'),
        (report_analyser_module.HostReportAnalyser, 'load_raw_groups', 'analyser.load_raw_groups'),
        (report_analyser_module.HostReportAnalyser, 'build_single_host_report', 'analyser.build_single_host_report'),
        (report_analyser_module.HostReportAnalyser, 'build_overview_report', 'analyser.build_overview_report'),
        (report_analyser_module.HostReportAnalyser, '_try_save_report_outputs', 'analyser._try_save_report_outputs'),
        (report_sender_module.HostReportSender, 'run_delivery', 'sender.run_delivery'),
        (report_sender_module.HostReportSender, '_send_report_document', 'sender._send_report_document'),
        (report_sender_module.HostReportSender, '_mark_report_skipped', 'sender._mark_report_skipped'),
    ]


def main():
    parser = argparse.ArgumentParser(description='测试 config_api.testSendReportMailApi 接口')
    parser.add_argument('--host-id', action='append', default=[], help='指定 report_host_ids，可重复或逗号分隔；默认使用已保存的报告主机')
    parser.add_argument('--cpu', default=None, help='临时 CPU 阈值')
    parser.add_argument('--memory', default=None, help='临时内存阈值')
    parser.add_argument('--disk', default=None, help='临时磁盘阈值')
    parser.add_argument('--ssl-cert', default=None, dest='ssl_cert', help='临时 SSL 证书阈值')
    parser.add_argument('--ha-enabled', action='store_true', default=None, help='本次测试启用 HA 报告')
    parser.add_argument('--ha-disabled', action='store_false', dest='ha_enabled', help='本次测试关闭 HA 报告')
    parser.add_argument('--send', action='store_true', help='真实发送邮件；默认 dry-run 只拦截发送动作')
    parser.add_argument('--precheck-only', action='store_true', help='只检查邮件通知和报告主机配置，不执行接口')
    parser.add_argument('--full-json', action='store_true', help='输出完整接口返回；默认输出摘要')
    parser.add_argument('--quiet', action='store_true', help='关闭测试脚本阶段日志')
    parser.add_argument('--trace-methods', action='store_true', help='打印报告分析和发送关键方法耗时')
    args = parser.parse_args()

    step_logger = StepLogger(enabled=not args.quiet)
    step_logger.log('start test script', mode='send' if args.send else 'dry-run')

    api = config_api()
    step_logger.log('collect precheck start')
    precheck = collect_precheck(api)
    step_logger.log(
        'collect precheck done',
        email_enabled=str(precheck.get('email_enabled')).lower(),
        recipients=len(precheck.get('recipients') or []),
        selected_hosts=precheck.get('selected_host_count'),
    )
    output = {
        'api': 'config/test_send_report_mail',
        'method': 'POST',
        'mode': 'send' if args.send else 'dry-run',
        'precheck': precheck,
    }

    if args.precheck_only:
        print_json(output)
        return 0 if precheck['email_enabled'] and precheck['recipients'] and precheck['selected_hosts_ok'] else 2

    dry_run = NotifyDryRun(jh, [report_sender_module, report_analyser_module]) if not args.send else None
    method_timer = MethodTimer(step_logger, build_trace_patches()) if args.trace_methods else None
    try:
        if dry_run is not None:
            step_logger.log('install notify dry-run hooks')
            dry_run.__enter__()
        if method_timer is not None:
            step_logger.log('install method timing hooks')
            method_timer.__enter__()
        app = Flask(__name__)
        form_data = build_form_data(args, precheck.get('selected_host_ids', []))
        step_logger.log('form data ready', host_count=len(form_data.get('report_host_ids[]', [])))
        with app.test_request_context('/config/test_send_report_mail', method='POST', data=form_data):
            step_logger.log('call api start')
            raw_result = api.testSendReportMailApi()
            step_logger.log('call api done')
        result = parse_api_response(raw_result)
        step_logger.log('parse result done', status=str(result.get('status')).lower())
        output['form_data'] = form_data
        captured_messages = dry_run.messages if dry_run is not None else []
        output['result'] = result if args.full_json else summarize_send_result(result, captured_messages)
        step_logger.log('print result')
        print_json(output)
        return 0 if result.get('status') else 1
    finally:
        if method_timer is not None:
            method_timer.restore()
        if dry_run is not None:
            dry_run.restore()


if __name__ == '__main__':
    raise SystemExit(main())
