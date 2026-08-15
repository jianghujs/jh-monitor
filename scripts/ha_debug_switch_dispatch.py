#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import os
import sys

ROOT = '/www/server/jh-monitor'
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'class/core'))

from ha_api import ha_api
import jh


def print_json(title, data):
    print('\n## ' + title)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description='诊断云监控 HA 切换任务是否会下发给指定主机')
    parser.add_argument('--pair-id', default='', help='主备关系 pair_id，不填取最新一条')
    parser.add_argument('--host-id', default='', help='模拟轮询的插件 host_id，不填会列出全部可见主机')
    parser.add_argument('--limit', type=int, default=10, help='展示最近切换任务数量')
    args = parser.parse_args()

    api = ha_api()
    api.ensureHaSchema()
    pair = {}
    if args.pair_id:
        pair = api._getPair(args.pair_id)
    else:
        rows = jh.M('ha_pair').field(api.pair_fields).order('id desc').limit('1').select()
        pair = rows[0] if isinstance(rows, list) and rows else {}
    if not pair:
        print('未找到主备关系')
        return 1

    normalized = api._normalizePair(pair, include_log=False, include_events=False)
    runs = jh.M('ha_switch_run').where('pair_id=?', (pair.get('pair_id'),)).field(api.run_fields).order('id desc').limit(str(args.limit)).select()
    if not isinstance(runs, list):
        runs = []

    print_json('主备关系', {
        'pair_id': pair.get('pair_id'),
        'pair_name': pair.get('pair_name'),
        'desired_master_host_id': pair.get('desired_master_host_id'),
        'actual_master_host_id': pair.get('actual_master_host_id'),
        'current_switch_run_id': pair.get('current_switch_run_id'),
        'status': pair.get('status'),
        'status_text': pair.get('status_text'),
    })
    print_json('云监控展示主机', [{
        'host_id': host.get('host_id'),
        'alias_ids': host.get('host_alias_ids'),
        'name': host.get('name'),
        'ip': host.get('ip'),
        'role': host.get('role'),
        'collect_method': host.get('collect_method'),
        'report_host_id': host.get('report_host_id'),
        'site_scope': host.get('site_scope'),
        'last_report_at': host.get('last_report_at'),
    } for host in normalized.get('hosts', [])])
    print_json('最近切换任务', [api._normalizeRun(row) for row in runs])

    if not args.host_id:
        print('\n提示：使用 --host-id <插件本机host_id> 可模拟该主机拉取任务时会拿到什么 execute_phase。')
        return 0

    host_id = args.host_id
    raw_states = api._getStates(pair.get('pair_id'))
    states = api._displayStates(raw_states)

    def resolve_executor(target_host_id):
        if not target_host_id:
            return '', ''
        if host_id == target_host_id:
            return target_host_id, 'local'
        for state in raw_states:
            detail = api._jsonLoads(state.get('health_detail'), {})
            alias_ids = [state.get('host_id')]
            source_host_id = detail.get('_source_host_id') if isinstance(detail, dict) else ''
            if source_host_id:
                alias_ids.append(source_host_id)
            if target_host_id not in alias_ids:
                continue
            if state.get('collect_method') == 'ssh_peer' and state.get('report_host_id') == host_id:
                return host_id, 'ssh_peer'
        for state in states:
            alias_ids = state.get('_alias_host_ids') or []
            if state.get('host_id') not in alias_ids:
                alias_ids.append(state.get('host_id'))
            if target_host_id not in alias_ids:
                continue
            if state.get('host_id') == host_id:
                return host_id, 'local'
            if state.get('report_host_id') == host_id and state.get('collect_method') == 'ssh_peer':
                return host_id, 'ssh_peer'
        return '', ''

    run = api._getRun(pair.get('current_switch_run_id') or '') if pair.get('current_switch_run_id') else {}
    result = {'host_id': host_id, 'switch_run': {}}
    if run:
        phase = run.get('current_phase') or ''
        target_host_id = ''
        execute_role = ''
        if phase == 'prepare_online':
            target_host_id = run.get('new_master_host_id')
            execute_role = 'master'
        elif phase == 'offline':
            target_host_id = run.get('old_master_host_id')
            execute_role = 'standby'
        elif phase == 'online':
            target_host_id = run.get('new_master_host_id')
            execute_role = 'master'
        executor_host_id, execute_method = resolve_executor(target_host_id)
        result['switch_run'] = api._normalizeRun(run)
        result['switch_run'].update({
            'execute_phase': phase if executor_host_id == host_id and phase in ('prepare_online', 'offline', 'online') else '',
            'execute_role': execute_role,
            'execute_method': execute_method,
            'execute_target_host_id': target_host_id,
            'executor_host_id': executor_host_id,
        })
    print_json('模拟拉取结果', result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
