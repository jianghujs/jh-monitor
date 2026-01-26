# coding: utf-8

import json


def parse_report_payload(raw_text):
    if raw_text is None:
        return None, "empty"
    if isinstance(raw_text, dict):
        return raw_text, None
    if isinstance(raw_text, str):
        content = raw_text.strip()
        if not content:
            return None, "empty"
        try:
            return json.loads(content), None
        except Exception:
            try:
                last_line = content.splitlines()[-1]
                return json.loads(last_line), None
            except Exception as e:
                return None, str(e)
    return None, "invalid"


def fetch_reports(host_list, script_name, run_script_batch):
    host_ips = [row.get('ip') for row in host_list if row.get('ip')]
    if not host_ips:
        return {}, {}
    script_items = [{'name': script_name, 'args': 'get_report_data'}]
    batch_result = run_script_batch(script_items, target_hosts=host_ips) or {}
    reports = {}
    errors = {}
    for row in host_list:
        host_ip = row.get('ip')
        if not host_ip:
            continue
        result = batch_result.get(host_ip)
        if not result or result.get('status') != 'ok':
            errors[host_ip] = result.get('msg', 'execute_failed') if result else 'no_result'
            continue
        raw = result.get('data', {}).get(script_name, '')
        report_data, err = parse_report_payload(raw)
        if err:
            errors[host_ip] = err
            continue
        reports[host_ip] = report_data
    return reports, errors


def send_report_error(host_row, report_type, err_msg, jh):
    host_id = host_row.get('host_id')
    host_name = host_row.get('host_name', '')
    host_ip = host_row.get('ip', '')
    report_label = '面板' if report_type == 'panel' else 'PVE'
    title = "{0}({1})获取报告异常".format(host_name, host_ip)
    msg = (
        "<div style='font-family: Arial, sans-serif;'>"
        "<div><strong>报告类型：</strong>{0}</div>"
        "<div><strong>错误信息：</strong>{1}</div>"
        "<div style='color: #999; margin-top: 6px;'>时间：{2}</div>"
        "</div>"
    ).format(report_label, err_msg, jh.getDateFromNow())
    return jh.notifyMessage(
        msg=msg,
        msgtype='html',
        title=title,
        stype='host_report_error_{0}'.format(host_id),
        trigger_time=0
    )
