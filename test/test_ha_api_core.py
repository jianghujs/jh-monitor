# coding: utf-8

import hashlib
import hmac
import json
import os
import sys
import time

ROOT = '/www/server/jh-monitor'
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'class/core'))

from route import app
from ha_api import ha_api


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
    pair_id = 'HA_TEST_' + str(int(time.time()))
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

    with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': pair_id, 'target_host_id': 'H_B'}):
        res = json.loads(api.requestSwitchApi())
        assert res['status'], res
        switch_run_id = res['data']['switch_run_id']
    event_payload = {'pair_id': pair_id, 'switch_run_id': switch_run_id, 'event_id': pair_id + '-evt-1', 'origin_host_id': 'H_A', 'report_host_id': 'H_A', 'collect_method': 'local', 'seq': 1, 'phase': 'offline', 'step': 'stop service', 'status': 'running', 'log_text': 'stopping'}
    with app.test_request_context('/pub/ha_report_switch_event', method='POST', json=event_payload, headers=_headers(secret, event_payload, pair_id + '-nonce-event-1')):
        res = json.loads(api.publicReportSwitchEvent())
        assert res['status'], res
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
