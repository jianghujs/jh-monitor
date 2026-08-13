# coding: utf-8

import json
import os
import sys
import time
import atexit

ROOT = '/www/server/jh-monitor'
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'class/core'))

from route import app
from ha_api import ha_api
import jh


def _cleanup_pairs(pair_ids):
    api = ha_api()
    api.ensureHaSchema()
    for pair_id in sorted(set([x for x in pair_ids if x])):
        runs = jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).field('switch_run_id,log_path').select()
        run_ids = []
        if isinstance(runs, list):
            for run in runs:
                if not isinstance(run, dict):
                    continue
                if run.get('switch_run_id'):
                    run_ids.append(run.get('switch_run_id'))
                log_path = run.get('log_path') or ''
                if log_path.startswith(api.LOG_ROOT) and os.path.isfile(log_path):
                    os.remove(log_path)
        jh.M('ha_switch_event').where('pair_id=?', (pair_id,)).delete()
        for switch_run_id in run_ids:
            jh.M('ha_switch_event').where('switch_run_id=?', (switch_run_id,)).delete()
        jh.M('ha_callback_record').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_host_state').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_api_nonce').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).delete()


def _json(text):
    return json.loads(text)


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    cleanup_pair_ids = []
    atexit.register(_cleanup_pairs, cleanup_pair_ids)
    pair_id = 'HA_UI_' + str(int(time.time()))
    cleanup_pair_ids.append(pair_id)
    secret = 'ui-secret-' + pair_id
    payload = {
        'pair_id': pair_id,
        'pair_name': 'HA UI Flow',
        'api_secret': secret,
        'local_host': {'host_id': 'H_UI_A', 'host_name': 'UI-A', 'host_ip': '10.10.1.1', 'role': 'master', 'online_status': 'online'},
        'peer_host': {'host_id': 'H_UI_B', 'host_name': 'UI-B', 'host_ip': '10.10.1.2', 'role': 'standby', 'online_status': 'online'}
    }
    with app.test_request_context('/pub/ha_register_pair', method='POST', json=payload):
        assert _json(api.publicRegisterPair())['status']

    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pairs = [x for x in res['data']['list'] if x['pair_id'] == pair_id]
        assert len(pairs) == 1
        pair = pairs[0]
        assert len(pair['hosts']) == 2
        assert pair['status'] == 'normal'

    with app.test_request_context('/ha/get_detail', method='POST', data={'pair_id': pair_id}):
        res = _json(api.getDetailApi())
        assert res['status']
        detail = res['data']
        assert detail['pair_name'] == 'HA UI Flow'
        assert sorted([x['host_id'] for x in detail['hosts']]) == ['H_UI_A', 'H_UI_B']

    api._upsertState(pair_id, {'host_id': 'H_PEER_PLACEHOLDER', 'host_name': '对端 10.10.1.1', 'host_ip': '10.10.1.1', 'role': 'standby', 'online_status': 'unknown'}, 'standby', api._now())
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pair = [x for x in res['data']['list'] if x['pair_id'] == pair_id][0]
        assert len([x for x in pair['hosts'] if x['ip'] == '10.10.1.1']) == 1, pair
        assert pair['hosts'][0]['name'] != '对端 10.10.1.1', pair
        assert 'H_PEER_PLACEHOLDER' in pair['hosts'][0]['host_alias_ids'], pair

    both_local_pair_id = pair_id + '_BOTH_LOCAL'
    cleanup_pair_ids.append(both_local_pair_id)
    now = api._now()
    api_secret = 'secret-both-local'
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (both_local_pair_id, 'BothLocal', 'H_PEER_B', api_secret, 'unknown', '等待插件上报', now, now))
    api._upsertState(both_local_pair_id, {'host_id': 'H_PANEL_A2', 'host_name': 'BothLocal-A', 'host_ip': '10.10.2.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'health_detail': {'script_checks': [{'name': 'OpenResty', 'status': 'pass'}]}}, 'standby', now)
    api._upsertState(both_local_pair_id, {'host_id': 'H_PANEL_B2', 'host_name': 'BothLocal-B', 'host_ip': '10.10.2.2', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'health_detail': {'script_checks': [{'name': 'OpenResty', 'status': 'pass'}]}}, 'master', now)
    api._upsertState(both_local_pair_id, {'host_id': 'H_PEER_B', 'host_name': '对端 10.10.2.2', 'host_ip': '10.10.2.2', 'role': 'master', 'online_status': 'unknown'}, 'master', now)
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pair = [x for x in res['data']['list'] if x['pair_id'] == both_local_pair_id][0]
        assert len(pair['hosts']) == 2, pair
        assert pair['actual_master_host_id'] == 'H_PANEL_B2', pair
        assert pair['desired_master_host_id'] == 'H_PANEL_B2', pair
        assert pair['status'] == 'normal', pair
        host_b = [x for x in pair['hosts'] if x['ip'] == '10.10.2.2'][0]
        assert 'H_PEER_B' in host_b['host_alias_ids'], host_b
        assert 'local' in host_b['host_alias_collect_methods'], host_b

    single_local_pair_id = pair_id + '_SINGLE_LOCAL'
    cleanup_pair_ids.append(single_local_pair_id)
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (single_local_pair_id, 'SingleLocal', 'H_REMOTE_B', api_secret, 'unknown', '等待插件上报', now, now))
    api._upsertState(single_local_pair_id, {'host_id': 'H_LOCAL_A', 'host_name': 'SingleLocal-A', 'host_ip': '10.10.3.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'site_scope': 'local', 'health_detail': {'script_checks': [{'name': 'OpenResty', 'status': 'pass'}]}}, 'standby', now)
    api._upsertState(single_local_pair_id, {'host_id': 'H_REMOTE_B', 'host_name': 'SingleLocal-B', 'host_ip': '10.10.3.2', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'report_host_id': 'H_LOCAL_A', 'site_scope': 'remote', 'health_detail': {'script_checks': [{'name': 'OpenResty', 'status': 'pass'}]}}, 'master', now)
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pair = [x for x in res['data']['list'] if x['pair_id'] == single_local_pair_id][0]
        assert len(pair['hosts']) == 2, pair
        assert pair['actual_master_host_id'] == 'H_REMOTE_B', pair
        assert pair['desired_master_host_id'] == 'H_REMOTE_B', pair
        assert pair['status'] == 'normal', pair
        remote = [x for x in pair['hosts'] if x['host_id'] == 'H_REMOTE_B'][0]
        assert remote['collect_method'] == 'ssh_peer', remote
        assert remote['collect_status'] == 'success', remote
        assert remote['online_status'] == 'online', remote
        assert remote['site_scope'] == 'remote', remote

    same_site_pair_id = pair_id + '_SAME_SITE'
    cleanup_pair_ids.append(same_site_pair_id)
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (same_site_pair_id, 'SameSite', 'H_SITE_A', api_secret, 'unknown', '等待插件上报', now, now))
    api._upsertState(same_site_pair_id, {'host_id': 'H_SITE_A', 'host_name': 'SameSite-A', 'host_ip': '10.10.4.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'site_scope': 'local'}, 'master', now)
    api._upsertState(same_site_pair_id, {'host_id': 'H_SITE_B', 'host_name': 'SameSite-B', 'host_ip': '10.10.4.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'report_host_id': 'H_SITE_A', 'site_scope': 'local'}, 'standby', now)
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pair = [x for x in res['data']['list'] if x['pair_id'] == same_site_pair_id][0]
        assert len(pair['hosts']) == 2, pair
        assert [x['site_scope'] for x in pair['hosts']] == ['local', 'local'], pair

    dual_report_pair_id = pair_id + '_DUAL_REPORT'
    cleanup_pair_ids.append(dual_report_pair_id)
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (dual_report_pair_id, 'DualReport', 'H_DUAL_B', api_secret, 'unknown', '等待插件上报', now, now))
    api._upsertState(dual_report_pair_id, {'host_id': 'H_DUAL_A', 'host_name': 'Dual-A', 'host_ip': '10.10.5.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'report_host_id': 'H_DUAL_A', 'site_scope': 'local'}, 'standby', now)
    api._upsertState(dual_report_pair_id, {'host_id': 'H_DUAL_B_ALIAS', 'host_name': 'Dual-B via A', 'host_ip': '10.10.5.2', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'report_host_id': 'H_DUAL_A', 'site_scope': 'local'}, 'master', now)
    api._upsertState(dual_report_pair_id, {'host_id': 'H_DUAL_B', 'host_name': 'Dual-B', 'host_ip': '10.10.5.2', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'report_host_id': 'H_DUAL_B', 'site_scope': 'local'}, 'master', now)
    api._upsertState(dual_report_pair_id, {'host_id': 'H_DUAL_A_ALIAS', 'host_name': 'Dual-A via B', 'host_ip': '10.10.5.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'report_host_id': 'H_DUAL_B', 'site_scope': 'local'}, 'standby', now)
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pair = [x for x in res['data']['list'] if x['pair_id'] == dual_report_pair_id][0]
        assert len(pair['hosts']) == 2, pair
        assert pair['actual_master_host_id'] == 'H_DUAL_B', pair
        assert pair['desired_master_host_id'] == 'H_DUAL_B', pair
        assert pair['status'] == 'normal', pair
        assert all([x['site_scope'] == 'local' for x in pair['hosts']]), pair
        assert all([x['collect_method'] == 'local' for x in pair['hosts']]), pair
        host_a = [x for x in pair['hosts'] if x['ip'] == '10.10.5.1'][0]
        host_b = [x for x in pair['hosts'] if x['ip'] == '10.10.5.2'][0]
        assert 'local' in host_a['host_alias_collect_methods'], host_a
        assert 'ssh_peer' in host_a['host_alias_collect_methods'], host_a
        assert 'local' in host_b['host_alias_collect_methods'], host_b
        assert 'ssh_peer' in host_b['host_alias_collect_methods'], host_b

    dual_real_id_pair_id = pair_id + '_DUAL_REAL_ID'
    cleanup_pair_ids.append(dual_real_id_pair_id)
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (dual_real_id_pair_id, 'DualRealId', 'H_REAL_B', api_secret, 'unknown', '等待插件上报', now, now))
    api._upsertState(dual_real_id_pair_id, {'host_id': 'H_REAL_A', 'host_name': 'Real-A', 'host_ip': '10.10.6.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'report_host_id': 'H_REAL_A', 'site_scope': 'local'}, 'standby', now)
    api._upsertState(dual_real_id_pair_id, {'host_id': 'H_REAL_B', 'host_name': 'Real-B', 'host_ip': '10.10.6.2', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'report_host_id': 'H_REAL_B', 'site_scope': 'local'}, 'master', now)
    api._upsertState(dual_real_id_pair_id, {'host_id': 'H_REAL_A', 'host_name': 'Real-A via B', 'host_ip': '10.10.6.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'report_host_id': 'H_REAL_B', 'site_scope': 'local'}, 'standby', now)
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        pair = [x for x in res['data']['list'] if x['pair_id'] == dual_real_id_pair_id][0]
        assert len(pair['hosts']) == 2, pair
        host_a = [x for x in pair['hosts'] if x['ip'] == '10.10.6.1'][0]
        assert host_a['collect_method'] == 'local', host_a
        assert 'ssh_peer' in host_a['host_alias_collect_methods'], host_a

    health_payload = {
        'pair_id': pair_id,
        'hosts': [{
            'host_id': 'H_UI_A',
            'host_name': 'UI-A',
            'host_ip': '10.10.1.1',
            'role': 'master',
            'online_status': 'online',
            'health_status': 'normal',
            'collect_status': 'success',
            'collect_method': 'local',
            'health_detail': {'script_checks': [{'group': 'Web 服务', 'name': 'OpenResty', 'expected': '运行中', 'actual': '运行中', 'status': 'pass'}]}
        }]
    }
    with app.test_request_context('/pub/ha_report_state', method='POST', json=health_payload, headers={}):
        # Directly exercise state persistence without signed wrapper in this UI flow test.
        api._upsertState(pair_id, health_payload['hosts'][0], 'master', api._now())

    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': pair_id, 'target_host_id': 'H_UI_B', 'sync_files': '1', 'run_checksum': '1'}):
        res = _json(api.requestSwitchApi())
        assert res['status']
        switch_run_id = res['data']['switch_run_id']

    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        pair = [x for x in res['data']['list'] if x['pair_id'] == pair_id][0]
        assert pair['status'] == 'switching'
        assert pair['desired_master_host_id'] == 'H_UI_B'
        assert pair['switch_run_id'] == switch_run_id
        assert pair['log'] == ''

    with app.test_request_context('/pub/ha_pull_desired_state', method='POST', json={'pair_id': pair_id, 'host_id': 'H_UI_A'}):
        api._publicPayload = lambda verify=True: (True, {'pair_id': pair_id, 'host_id': 'H_UI_A'}, 'ok')
        pull = _json(api.publicPullDesiredState())
        assert pull['status']
        assert pull['data']['switch_run']['execute_phase'] == 'offline', pull

    prepare_pair_id = pair_id + '_PREPARE_FLOW'
    cleanup_pair_ids.append(prepare_pair_id)
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (prepare_pair_id, 'PrepareFlow', 'H_PREP_A', api_secret, 'normal', '状态正常', now, now))
    api._upsertState(prepare_pair_id, {'host_id': 'H_PREP_A', 'host_name': 'Prep-A', 'host_ip': '10.10.7.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'site_scope': 'local'}, 'master', now)
    api._upsertState(prepare_pair_id, {'host_id': 'H_PREP_B', 'host_name': 'Prep-B', 'host_ip': '10.10.7.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'site_scope': 'local'}, 'standby', now)
    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': prepare_pair_id, 'target_host_id': 'H_PREP_B', 'action': 'prepare', 'sync_files': '1', 'run_checksum': '1'}):
        res = _json(api.requestSwitchApi())
        assert res['status']
        prepare_run_id = res['data']['switch_run_id']
    run_options = json.loads(api._getRun(prepare_run_id)['options_json'])
    assert 'local_ip' not in run_options, run_options
    assert 'remote_ip' not in run_options, run_options
    assert 'remote_ssh_port' not in run_options, run_options
    with app.test_request_context('/pub/ha_pull_desired_state', method='POST', json={'pair_id': prepare_pair_id, 'host_id': 'H_PREP_B'}):
        api._publicPayload = lambda verify=True: (True, {'pair_id': prepare_pair_id, 'host_id': 'H_PREP_B'}, 'ok')
        pull = _json(api.publicPullDesiredState())
        assert pull['status']
        assert pull['data']['switch_run']['execute_phase'] == 'prepare_online', pull
    with app.test_request_context('/pub/ha_ack_switch_phase', method='POST', json={'pair_id': prepare_pair_id, 'switch_run_id': prepare_run_id, 'phase': 'prepare_online', 'phase_status': 'success', 'current_step': '预上线完成'}):
        payload = {'pair_id': prepare_pair_id, 'switch_run_id': prepare_run_id, 'phase': 'prepare_online', 'phase_status': 'success', 'current_step': '预上线完成'}
        api._publicPayload = lambda verify=True: (True, payload, 'ok')
        assert _json(api.publicAckSwitchPhase())['status']
    run = api._getRun(prepare_run_id)
    assert run['status'] == 'prepare_success', run
    pair_after_prepare = api._getPair(prepare_pair_id)
    assert pair_after_prepare['status'] == 'normal', pair_after_prepare

    event_payload = {'switch_run_id': switch_run_id, 'pair_id': pair_id, 'event_id': pair_id + '-ui-event', 'origin_host_id': 'H_UI_A', 'seq': 1, 'phase': 'offline', 'step': '关闭服务', 'status': 'running', 'log_text': '关闭服务'}
    with app.test_request_context('/pub/ha_report_switch_event', method='POST', json=event_payload):
        api._publicPayload = lambda verify=True: (True, event_payload, 'ok')
        assert _json(api.publicReportSwitchEvent())['status']

    with app.test_request_context('/ha/read_log', method='POST', data={'switch_run_id': switch_run_id, 'offset': 0}):
        res = _json(api.readLogApi())
        assert res['status']
        assert '创建切换任务' in res['data']['content']
        assert res['data']['next_offset'] > 0
        assert res['data']['run']['switch_run_id'] == switch_run_id

    with app.test_request_context('/ha/get_detail', method='POST', data={'pair_id': pair_id}):
        res = _json(api.getDetailApi())
        assert res['status']
        detail = res['data']
        host = [x for x in detail['hosts'] if x['host_id'] == 'H_UI_A'][0]
        assert host['script_checks'][0]['name'] == 'OpenResty', host
        assert detail['switch_run']['switch_run_id'] == switch_run_id, detail
        assert detail['switch_events'][0]['origin_host_id'] == 'H_UI_A', detail
        assert '关闭服务' in detail['log'], detail

    finalize_pair_id = pair_id + '_FINALIZE_FLOW'
    cleanup_pair_ids.append(finalize_pair_id)
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (finalize_pair_id, 'FinalizeFlow', 'H_FIN_A', api_secret, 'normal', '状态正常', now, now))
    api._upsertState(finalize_pair_id, {'host_id': 'H_FIN_A', 'host_name': 'Fin-A', 'host_ip': '10.10.8.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'site_scope': 'local'}, 'master', now)
    api._upsertState(finalize_pair_id, {'host_id': 'H_FIN_B', 'host_name': 'Fin-B', 'host_ip': '10.10.8.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'site_scope': 'local'}, 'standby', now)
    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': finalize_pair_id, 'target_host_id': 'H_FIN_B', 'action': 'finalize'}):
        res = _json(api.requestSwitchApi())
        assert res['status']
        finalize_run_id = res['data']['switch_run_id']
    for phase, step in [('offline', '旧主机下线完成'), ('online', '正式上线完成')]:
        payload = {'pair_id': finalize_pair_id, 'switch_run_id': finalize_run_id, 'phase': phase, 'phase_status': 'success', 'current_step': step}
        with app.test_request_context('/pub/ha_ack_switch_phase', method='POST', json=payload):
            api._publicPayload = lambda verify=True, payload=payload: (True, payload, 'ok')
            assert _json(api.publicAckSwitchPhase())['status']
    pair_after_finalize = api._getPair(finalize_pair_id)
    assert pair_after_finalize['current_switch_run_id'] == '', pair_after_finalize
    with app.test_request_context('/ha/read_log', method='POST', data={'switch_run_id': finalize_run_id, 'offset': 0}):
        res = _json(api.readLogApi())
        assert res['status']
        assert res['data']['run']['status'] == 'success', res
        assert '正式上线完成' in res['data']['content'], res

    with app.test_request_context('/ha/cancel_switch', method='POST', data={'switch_run_id': switch_run_id}):
        assert _json(api.cancelSwitchApi())['status']
    with app.test_request_context('/ha/retry_switch', method='POST', data={'switch_run_id': switch_run_id}):
        assert _json(api.retrySwitchApi())['status']

    with app.test_request_context('/ha/save_callback_config', method='POST', data={'pair_id': pair_id, 'callback_url': 'http://127.0.0.1:9/callback', 'callback_enabled': '1'}):
        assert _json(api.saveCallbackConfigApi())['status']

    with app.test_request_context('/ha/delete_pair', method='POST', data={'pair_id': pair_id}):
        assert _json(api.deletePairApi())['status']
    with app.test_request_context('/ha/get_detail', method='POST', data={'pair_id': pair_id}):
        res = _json(api.getDetailApi())
        assert not res['status'], res
    with app.test_request_context('/ha/get_list', method='POST'):
        res = _json(api.getListApi())
        assert res['status']
        assert not [x for x in res['data']['list'] if x['pair_id'] == pair_id], res
    print('ok')


if __name__ == '__main__':
    main()
