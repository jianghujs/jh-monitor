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
sys.path.insert(0, os.path.join(ROOT, 'scripts'))

from route import app
from ha_api import ha_api
from report_analyser import HostReportAnalyser
import jh


def _cleanup(prefix):
    api = ha_api()
    api.ensureHaSchema()
    db = jh.M('ha_pair')
    pairs = db.originExecute('SELECT pair_id FROM ha_pair WHERE pair_id LIKE ?', (prefix + '%',)).fetchall()
    for row in pairs:
        pair_id = row[0]
        runs = jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).field('switch_run_id,log_path').select()
        run_ids = []
        if isinstance(runs, list):
            for run in runs:
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
    db.originExecute('DELETE FROM ha_sync_config WHERE sync_id LIKE ?', (prefix + '%',))
    db.originExecute('DELETE FROM ha_sync_cursor WHERE sync_id LIKE ?', (prefix + '%',))
    db.originExecute('DELETE FROM ha_sync_applied WHERE sync_id LIKE ? OR event_id LIKE ?', (prefix + '%', prefix + '%'))
    db.originExecute('DELETE FROM ha_sync_event WHERE event_id LIKE ?', (prefix + '%',))
    db.originExecute('DELETE FROM ha_sync_nonce WHERE sync_id LIKE ? OR nonce LIKE ?', (prefix + '%', prefix + '%'))


def _sync_headers(secret, payload, nonce):
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    signature = hmac.new(secret.encode('utf-8'), '\n'.join([timestamp, nonce, body_hash]).encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        'Content-Type': 'application/json',
        'X-JHM-Timestamp': timestamp,
        'X-JHM-Nonce': nonce,
        'X-JHM-Body-Hash': body_hash,
        'X-JHM-Signature': signature
    }


def _pair_headers(secret, payload, nonce):
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    signature = hmac.new(secret.encode('utf-8'), '\n'.join([timestamp, nonce, body_hash]).encode('utf-8'), hashlib.sha256).hexdigest()
    return {
        'Content-Type': 'application/json',
        'X-JH-Timestamp': timestamp,
        'X-JH-Nonce': nonce,
        'X-JH-Body-Hash': body_hash,
        'X-JH-Signature': signature
    }


def _add_sync_config(sync_id, secret, peer_monitor_id='MONITOR_PEER', enabled=1):
    now = ha_api()._now()
    jh.M('ha_sync_config').add(
        'sync_id,sync_name,sync_type,peer_monitor_url,peer_monitor_id,peer_monitor_name,sync_secret,enabled,status,addtime,update_time',
        (sync_id, sync_id, 'ha_management', 'http://127.0.0.1:1', peer_monitor_id, 'Peer Monitor', secret, enabled, 'pending', now, now)
    )


def _register_pair(api, pair_id, secret, master='H_A', standby='H_B'):
    payload = {
        'pair_id': pair_id,
        'pair_name': pair_id,
        'api_secret': secret,
        'desired_master_host_id': master,
        'local_host': {'host_id': master, 'host_name': master, 'host_ip': '10.88.0.1', 'role': 'master', 'online_status': 'online'},
        'peer_host': {'host_id': standby, 'host_name': standby, 'host_ip': '10.88.0.2', 'role': 'standby', 'online_status': 'online'}
    }
    with app.test_request_context('/pub/ha_register_pair', method='POST', json=payload):
        res = json.loads(api.publicRegisterPair())
        assert res['status'], res


def _event(event_id, event_type, payload, seq=1, source_monitor_id='MONITOR_PEER'):
    return {
        'event_id': event_id,
        'sync_type': 'ha_management',
        'source_monitor_id': source_monitor_id,
        'source_monitor_name': 'Peer Monitor',
        'event_type': event_type,
        'object_key': event_id,
        'payload': payload,
        'seq': seq,
        'addtime': ha_api()._now()
    }


def _test_signature_and_nonce(api, prefix):
    sync_id = prefix + '_SIG'
    secret = 'secret-' + sync_id
    _add_sync_config(sync_id, secret)
    payload = {'sync_id': sync_id, 'sync_type': 'ha_management', 'monitor_id': 'MONITOR_PEER', 'monitor_name': 'Peer', 'sync_version': '1.0'}
    with app.test_request_context('/pub/ha_monitor_sync_handshake', method='POST', json=payload, headers=_sync_headers('bad-secret', payload, prefix + '_bad_nonce')):
        res = json.loads(api.publicMonitorSyncHandshake())
        assert not res['status'] and '签名' in res['msg'], res
    headers = _sync_headers(secret, payload, prefix + '_nonce_ok')
    with app.test_request_context('/pub/ha_monitor_sync_handshake', method='POST', json=payload, headers=headers):
        res = json.loads(api.publicMonitorSyncHandshake())
        assert res['status'] and res['data']['monitor_id'], res
    with app.test_request_context('/pub/ha_monitor_sync_handshake', method='POST', json=payload, headers=headers):
        res = json.loads(api.publicMonitorSyncHandshake())
        assert not res['status'] and 'nonce' in res['msg'], res


def _test_idempotent_event_and_cursor(api, prefix):
    sync_id = prefix + '_CURSOR'
    secret = 'secret-' + sync_id
    _add_sync_config(sync_id, secret)
    sync_config = api._getSyncConfig(sync_id)
    pair_id = prefix + '_PAIR_CURSOR'
    pair_event = _event(prefix + '_EVT_PAIR', 'ha_pair', {'pair': {'pair_id': pair_id, 'pair_name': 'CursorPair', 'desired_master_host_id': 'H_A', 'actual_master_host_id': 'H_A', 'status': 'normal', 'status_text': '状态正常'}}, 3)
    calls = []

    def fake_post(_sync_config, path, payload, timeout=10):
        calls.append(path)
        if path.endswith('/ha_monitor_sync_pull'):
            return {'status': True, 'data': {'monitor_id': 'MONITOR_PEER', 'monitor_name': 'Peer Monitor', 'events': [pair_event], 'max_seq': 3}}
        return {'status': True, 'data': {}}

    original_post = api._postSyncJson
    api._postSyncJson = fake_post
    try:
        result = api._runOneMonitorSync(sync_config)
    finally:
        api._postSyncJson = original_post
    assert result['status'] == 'ok', result
    assert api._getPair(pair_id).get('pair_name') == 'CursorPair'
    cursor = jh.M('ha_sync_cursor').where('sync_id=? AND sync_type=?', (sync_id, 'ha_management')).field('last_seq,last_event_id,last_error').find()
    assert cursor['last_seq'] == 3 and cursor['last_event_id'] == pair_event['event_id'], cursor
    applied_count = jh.M('ha_sync_applied').where('event_id=?', (pair_event['event_id'],)).count()
    api._applySyncEvent(sync_config, pair_event)
    assert jh.M('ha_sync_applied').where('event_id=?', (pair_event['event_id'],)).count() == applied_count
    assert '/pub/ha_monitor_sync_ack' in calls, calls

    failed_event = _event(prefix + '_EVT_BAD', 'bad_type', {}, 4)

    def fake_fail_post(_sync_config, path, payload, timeout=10):
        if path.endswith('/ha_monitor_sync_pull'):
            return {'status': True, 'data': {'monitor_id': 'MONITOR_PEER', 'monitor_name': 'Peer Monitor', 'events': [failed_event], 'max_seq': 4}}
        return {'status': True, 'data': {}}

    sync_config = api._getSyncConfig(sync_id)
    api._postSyncJson = fake_fail_post
    try:
        result = api._runOneMonitorSync(sync_config)
    finally:
        api._postSyncJson = original_post
    assert result['status'] == 'failed', result
    cursor = jh.M('ha_sync_cursor').where('sync_id=? AND sync_type=?', (sync_id, 'ha_management')).field('last_seq,last_error').find()
    assert cursor['last_seq'] == 3 and '不支持的同步事件类型' in cursor['last_error'], cursor


def _test_export_only_local_host_state(api, prefix):
    sync_id = prefix + '_LOCAL_ONLY'
    secret = 'secret-' + sync_id
    _add_sync_config(sync_id, secret)
    pair_id = prefix + '_PAIR_LOCAL_ONLY'
    pair_secret = 'pair-secret-local-only-' + prefix
    _register_pair(api, pair_id, pair_secret)
    payload = {
        'pair_id': pair_id,
        'hosts': [
            {'host_id': 'H_A', 'host_name': 'Local A', 'host_ip': '10.88.6.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local'},
            {'host_id': 'H_B', 'host_name': 'Peer B', 'host_ip': '10.88.6.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'report_host_id': 'H_A'}
        ]
    }
    with app.test_request_context('/pub/ha_report_state', method='POST', json=payload, headers=_pair_headers(pair_secret, payload, prefix + '_report_local_only')):
        res = json.loads(api.publicReportState())
        assert res['status'], res
    rows = jh.M('ha_sync_event').where('sync_type=? AND event_type=? AND object_key LIKE ?', ('ha_management', 'ha_host_state', pair_id + ':%')).field(api.sync_event_fields).select()
    payloads = [api._jsonLoads(row.get('payload_json'), {}) for row in rows]
    exported_methods = sorted([(item.get('state') or {}).get('collect_method') for item in payloads if isinstance(item, dict)])
    assert exported_methods == ['local'], exported_methods

    peer_event_id = prefix + '_EVT_EXPORT_PEER'
    local_event_id = prefix + '_EVT_EXPORT_LOCAL'
    now = api._now()
    jh.M('ha_sync_event').add(
        'event_id,sync_type,source_monitor_id,source_monitor_name,event_type,object_key,payload_json,seq,addtime',
        (peer_event_id, 'ha_management', 'MONITOR_LOCAL_ONLY', 'Local Only', 'ha_host_state', peer_event_id, json.dumps({'state': {'pair_id': pair_id, 'host_id': 'H_PEER_SKIP', 'collect_method': 'ssh_peer'}}, ensure_ascii=False), 9001, now)
    )
    jh.M('ha_sync_event').add(
        'event_id,sync_type,source_monitor_id,source_monitor_name,event_type,object_key,payload_json,seq,addtime',
        (local_event_id, 'ha_management', 'MONITOR_LOCAL_ONLY', 'Local Only', 'ha_host_state', local_event_id, json.dumps({'state': {'pair_id': pair_id, 'host_id': 'H_LOCAL_EXPORT', 'collect_method': 'local'}}, ensure_ascii=False), 9002, now)
    )
    pull_payload = {'sync_id': sync_id, 'sync_type': 'ha_management', 'monitor_id': 'MONITOR_PEER_PULL', 'after_seq': 9000, 'limit': 10}
    with app.test_request_context('/pub/ha_monitor_sync_pull', method='POST', json=pull_payload, headers=_sync_headers(secret, pull_payload, prefix + '_pull_local_only')):
        res = json.loads(api.publicMonitorSyncPull())
        assert res['status'], res
        event_ids = [event['event_id'] for event in res['data']['events']]
        assert local_event_id in event_ids and peer_event_id not in event_ids, res
        assert res['data']['max_seq'] >= 9002, res


def _test_host_state_merge(api, prefix):
    sync_id = prefix + '_MERGE'
    secret = 'secret-' + sync_id
    _add_sync_config(sync_id, secret)
    sync_config = api._getSyncConfig(sync_id)
    pair_id = prefix + '_PAIR_MERGE'
    _register_pair(api, pair_id, 'pair-secret-' + prefix)
    older = '2026-01-01 00:00:00'
    newer = '2026-01-01 00:01:00'
    api._upsertState(pair_id, {'host_id': 'H_A', 'host_name': 'Local A', 'host_ip': '10.88.1.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'last_report_at': older}, 'master', api._now())
    same_time_peer = _event(prefix + '_EVT_SAME_TIME', 'ha_host_state', {'state': {'pair_id': pair_id, 'host_id': 'H_A', 'host_name': 'Peer A', 'host_ip': '10.88.1.1', 'role': 'standby', 'online_status': 'offline', 'health_status': 'failed', 'collect_status': 'failed', 'collect_method': 'ssh_peer', 'last_report_at': older}}, 11)
    api._applySyncEvent(sync_config, same_time_peer)
    state = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, 'H_A')).field(api.state_fields).find()
    assert state['host_name'] == 'Local A' and state['role'] == 'master', state
    newer_peer = _event(prefix + '_EVT_NEWER', 'ha_host_state', {'state': {'pair_id': pair_id, 'host_id': 'H_A', 'host_name': 'Peer A Newer', 'host_ip': '10.88.1.1', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'last_report_at': newer}}, 12)
    api._applySyncEvent(sync_config, newer_peer)
    state = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, 'H_A')).field(api.state_fields).find()
    assert state['host_name'] == 'Peer A Newer' and state['role'] == 'standby', state
    stale_peer = _event(prefix + '_EVT_STALE', 'ha_host_state', {'state': {'pair_id': pair_id, 'host_id': 'H_A', 'host_name': 'Stale A', 'host_ip': '10.88.1.1', 'role': 'master', 'online_status': 'unknown', 'health_status': 'unknown', 'collect_status': 'failed', 'collect_method': 'ssh_peer', 'last_report_at': older}}, 13)
    api._applySyncEvent(sync_config, stale_peer)
    state = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, 'H_A')).field(api.state_fields).find()
    assert state['host_name'] == 'Peer A Newer' and state['collect_status'] == 'success', state


def _test_cross_monitor_dispatch(api, prefix):
    local_monitor_id = api._localMonitor().get('monitor_id')
    peer_monitor_id = prefix + '_PEER_MONITOR'
    sync_id = prefix + '_DISPATCH'
    _add_sync_config(sync_id, 'secret-' + sync_id, peer_monitor_id=peer_monitor_id)
    pair_id = prefix + '_PAIR_DISPATCH'
    pair_secret = 'pair-secret-' + prefix
    now = api._now()
    jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,actual_master_host_id,api_secret,status,status_text,addtime,update_time', (pair_id, 'DispatchPair', 'H_A', 'H_A', pair_secret, 'normal', '状态正常', now, now))
    api._upsertState(pair_id, {'host_id': 'H_A', 'host_name': 'A', 'host_ip': '10.88.2.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'source_monitor_id': local_monitor_id}, 'master', now)
    api._upsertState(pair_id, {'host_id': 'H_B', 'host_name': 'B', 'host_ip': '10.88.2.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'source_monitor_id': peer_monitor_id}, 'standby', now)
    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': pair_id, 'target_host_id': 'H_B', 'action': 'prepare'}):
        res = json.loads(api.requestSwitchApi())
        assert res['status'], res
        run = api._getRun(res['data']['switch_run_id'])
        assert run['origin_monitor_id'] == local_monitor_id, run
        assert run['execution_monitor_id'] == peer_monitor_id, run
    pull_payload = {'pair_id': pair_id, 'host_id': 'H_A'}
    with app.test_request_context('/pub/ha_pull_desired_state', method='POST', json=pull_payload, headers=_pair_headers(pair_secret, pull_payload, prefix + '_pull_remote')):
        res = json.loads(api.publicPullDesiredState())
        assert res['status'], res
        assert res['data']['switch_run']['execute_phase'] == '', res
        assert '不是该任务执行方' in res['data']['switch_run']['dispatch_reason'], res

    local_pair_id = prefix + '_PAIR_CLAIM'
    _register_pair(api, local_pair_id, pair_secret, master='H_C', standby='H_D')
    api._upsertState(local_pair_id, {'host_id': 'H_C', 'host_name': 'H_C', 'host_ip': '10.88.3.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local'}, 'master', api._now())
    api._upsertState(local_pair_id, {'host_id': 'H_D', 'host_name': 'H_D', 'host_ip': '10.88.3.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local'}, 'standby', api._now())
    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': local_pair_id, 'target_host_id': 'H_D', 'action': 'prepare'}):
        res = json.loads(api.requestSwitchApi())
        assert res['status'], res
        switch_run_id = res['data']['switch_run_id']
    future = int(time.time()) + 120
    jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save('claimed_by_host_id,claim_token,claim_expire_at', ('H_OTHER', 'token-other', future))
    pull_payload = {'pair_id': local_pair_id, 'host_id': 'H_D'}
    with app.test_request_context('/pub/ha_pull_desired_state', method='POST', json=pull_payload, headers=_pair_headers(pair_secret, pull_payload, prefix + '_pull_claim')):
        res = json.loads(api.publicPullDesiredState())
        assert res['status'], res
        run = res['data']['switch_run']
        assert run['execute_phase'] == '', run
        assert '已由主机 H_OTHER 领取' in run['dispatch_reason'], run


def _test_report_reads_synced_ha_tables(api, prefix):
    sync_id = prefix + '_REPORT'
    _add_sync_config(sync_id, 'secret-' + sync_id)
    sync_config = api._getSyncConfig(sync_id)
    warning_pair_id = prefix + '_PAIR_REPORT_WARNING'
    danger_pair_id = prefix + '_PAIR_REPORT_DANGER'
    api._applySyncEvent(sync_config, _event(prefix + '_EVT_REPORT_PAIR_W', 'ha_pair', {'pair': {'pair_id': warning_pair_id, 'pair_name': '同步提醒主备', 'desired_master_host_id': 'H_W_A', 'actual_master_host_id': 'H_W_A', 'status': 'normal', 'status_text': '状态正常'}}, 21))
    api._applySyncEvent(sync_config, _event(prefix + '_EVT_REPORT_STATE_W1', 'ha_host_state', {'state': {'pair_id': warning_pair_id, 'host_id': 'H_W_A', 'host_name': 'Warn-A', 'host_ip': '10.88.4.1', 'role': 'master', 'online_status': 'online', 'health_status': 'warning', 'collect_status': 'success', 'collect_method': 'local', 'last_report_at': api._now(), 'health_detail': {'summary': '同步过来的自检提醒'}}}, 22))
    api._applySyncEvent(sync_config, _event(prefix + '_EVT_REPORT_STATE_W2', 'ha_host_state', {'state': {'pair_id': warning_pair_id, 'host_id': 'H_W_B', 'host_name': 'Warn-B', 'host_ip': '10.88.4.2', 'role': 'standby', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'last_report_at': api._now()}}, 23))
    api._applySyncEvent(sync_config, _event(prefix + '_EVT_REPORT_PAIR_D', 'ha_pair', {'pair': {'pair_id': danger_pair_id, 'pair_name': '同步异常主备', 'desired_master_host_id': 'H_D_A', 'actual_master_host_id': 'H_D_A', 'status': 'normal', 'status_text': '状态正常'}}, 24))
    api._applySyncEvent(sync_config, _event(prefix + '_EVT_REPORT_STATE_D1', 'ha_host_state', {'state': {'pair_id': danger_pair_id, 'host_id': 'H_D_A', 'host_name': 'Danger-A', 'host_ip': '10.88.5.1', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'local', 'last_report_at': api._now()}}, 25))
    api._applySyncEvent(sync_config, _event(prefix + '_EVT_REPORT_STATE_D2', 'ha_host_state', {'state': {'pair_id': danger_pair_id, 'host_id': 'H_D_B', 'host_name': 'Danger-B', 'host_ip': '10.88.5.2', 'role': 'master', 'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success', 'collect_method': 'ssh_peer', 'last_report_at': api._now()}}, 26))
    analyser = HostReportAnalyser(now_ts=int(time.time()), logger=lambda msg: None)
    overview = analyser._build_ha_management_overview()
    danger_names = [x['pair_name'] for x in overview.get('danger_items') or []]
    warning_names = [x['pair_name'] for x in overview.get('warning_items') or []]
    assert '同步异常主备' in danger_names, overview
    assert '同步提醒主备' in warning_names, overview


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    prefix = 'HA_SYNC_TEST_' + str(int(time.time()))
    atexit.register(_cleanup, prefix)
    _cleanup(prefix)
    _test_signature_and_nonce(api, prefix)
    _test_idempotent_event_and_cursor(api, prefix)
    _test_export_only_local_host_state(api, prefix)
    _test_host_state_merge(api, prefix)
    _test_cross_monitor_dispatch(api, prefix)
    _test_report_reads_synced_ha_tables(api, prefix)
    print('ok')


if __name__ == '__main__':
    main()
