# coding: utf-8

import hashlib
import hmac
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


def _headers(secret, payload, nonce='nonce-test'):
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    signature = hmac.new(secret.encode('utf-8'), '\n'.join([timestamp, nonce, body_hash]).encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        'X-JH-Timestamp': timestamp,
        'X-JH-Nonce': nonce,
        'X-JH-Body-Hash': body_hash,
        'X-JH-Signature': signature,
        'Content-Type': 'application/json'
    }


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    cleanup_pair_ids = []
    atexit.register(_cleanup_pairs, cleanup_pair_ids)
    pair_id = 'HA_TEST_' + str(int(time.time()))
    cleanup_pair_ids.append(pair_id)
    secret = 'secret-' + pair_id
    register_payload = {
        'pair_id': pair_id,
        'pair_name': 'HA Core Test',
        'api_secret': secret,
        'local_host': {'host_id': 'H_A', 'host_name': 'A', 'host_ip': '10.0.0.1', 'role': 'master', 'online_status': 'online'},
        'peer_host': {'host_id': 'H_B', 'host_name': 'B', 'host_ip': '10.0.0.2', 'role': 'standby', 'online_status': 'online'}
    }
    with app.test_request_context('/pub/ha_register_pair', method='POST', json=register_payload):
        res = json.loads(api.publicRegisterPair())
        assert res['status'], res

    states = api._getStates(pair_id)
    pair = api._getPair(pair_id)
    status, text = api.deriveStatus(pair, states)
    assert status == 'normal', (status, text)

    report_payload = {'pair_id': pair_id, 'hosts': [{'host_id': 'H_A', 'host_name': 'A', 'host_ip': '10.0.0.1', 'role': 'master', 'online_status': 'offline', 'health_status': 'normal'}]}
    with app.test_request_context('/pub/ha_report_state', method='POST', json=report_payload, headers=_headers(secret, report_payload, pair_id + '-nonce-report')):
        res = json.loads(api.publicReportState())
        assert res['status'], res
    with app.test_request_context('/pub/ha_report_state', method='POST', json=report_payload, headers=_headers(secret, report_payload, pair_id + '-nonce-report')):
        res = json.loads(api.publicReportState())
        assert not res['status'] and 'nonce' in res['msg'], res

    pair = api._getPair(pair_id)
    states = api._getStates(pair_id)
    status, text = api.deriveStatus(pair, states)
    assert status == 'danger', (status, text)

    stale_pair_id = pair_id + '_STALE_PEER'
    cleanup_pair_ids.append(stale_pair_id)
    stale_now = api._now()
    stale_old = '2000-01-01 00:00:00'
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (stale_pair_id, 'Stale Peer', 'H_PEER_ONLY', secret, 'unknown', '等待插件上报', stale_now, stale_now))
    jh.M('ha_host_state').add(
        'pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,health_detail,last_report_at,addtime,update_time',
        (stale_pair_id, 'H_PEER_ONLY', '对端 10.0.9.9', '10.0.9.9', 'master', 'unknown', 'unknown', 'unknown', '', '', '{}', stale_old, stale_now, stale_now)
    )
    stale_pair = api._getPair(stale_pair_id)
    stale_states = api._getStates(stale_pair_id)
    stale_status, stale_text = api.deriveStatus(stale_pair, stale_states)
    assert '插件失联' not in stale_text, (stale_status, stale_text)

    checks_payload = {
        'pair_id': pair_id,
        'hosts': [{
            'host_id': 'H_A',
            'host_name': 'A',
            'host_ip': '10.0.0.1',
            'role': 'master',
            'online_status': 'online',
            'health_status': 'warning',
            'collect_status': 'success',
            'collect_method': 'local',
            'switch_phase': 'prepare_online',
            'switch_status': 'prepare_online_running',
            'current_step': '同步文件',
            'next_step': 'checksum 检查',
            'health_detail': {
                'summary': '存在自检提醒',
                'script_checks': [
                    {'group': '数据库', 'name': 'MySQL 主从状态', 'expected': '无主从配置', 'actual': '复制延迟 38s', 'status': 'warning', 'message': '延迟偏高'}
                ]
            }
        }]
    }
    with app.test_request_context('/pub/ha_report_state', method='POST', json=checks_payload, headers=_headers(secret, checks_payload, pair_id + '-nonce-checks')):
        res = json.loads(api.publicReportState())
        assert res['status'], res
    normalized = api._normalizeHost(api._getStates(pair_id)[0])
    assert normalized['script_checks'][0]['name'] == 'MySQL 主从状态', normalized
    assert normalized['script_checks'][0]['status'] == 'warning', normalized
    assert normalized['switch_phase'] == 'prepare_online', normalized

    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': pair_id, 'target_host_id': 'H_B'}):
        res = json.loads(api.requestSwitchApi())
        assert res['status'], res
        switch_run_id = res['data']['switch_run_id']
    event_payload = {'pair_id': pair_id, 'switch_run_id': switch_run_id, 'event_id': pair_id + '-evt-1', 'origin_host_id': 'H_A', 'report_host_id': 'H_A', 'collect_method': 'local', 'seq': 1, 'phase': 'offline', 'step': 'stop service', 'status': 'running', 'log_text': 'stopping'}
    with app.test_request_context('/pub/ha_report_switch_event', method='POST', json=event_payload, headers=_headers(secret, event_payload, pair_id + '-nonce-event-1')):
        res = json.loads(api.publicReportSwitchEvent())
        assert res['status'], res
    detail = api._normalizePair(api._getPair(pair_id), include_log=True, include_events=True)
    assert detail['switch_run']['switch_run_id'] == switch_run_id, detail
    assert detail['switch_events'][0]['origin_host_id'] == 'H_A', detail
    assert 'stopping' in detail['log'], detail
    run = api._getRun(switch_run_id)
    before = os.path.getsize(run['log_path'])
    with app.test_request_context('/pub/ha_report_switch_event', method='POST', json=event_payload, headers=_headers(secret, event_payload, pair_id + '-nonce-event-2')):
        res = json.loads(api.publicReportSwitchEvent())
        assert res['status'] and res['data']['duplicate'], res
    after = os.path.getsize(run['log_path'])
    assert before == after, (before, after)
    with app.test_request_context('/ha/read_log', method='POST', data={'switch_run_id': switch_run_id, 'offset': 0}):
        res = json.loads(api.readLogApi())
        assert res['status'] and 'stopping' in res['data']['content'], res
    print('ok')


if __name__ == '__main__':
    main()
