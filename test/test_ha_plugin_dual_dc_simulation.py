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


def _headers(secret, payload, nonce):
    timestamp = str(int(time.time()))
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
    signature = hmac.new(secret.encode('utf-8'), '\n'.join([timestamp, nonce, body_hash]).encode('utf-8'), hashlib.sha256).hexdigest()
    return {'X-JH-Timestamp': timestamp, 'X-JH-Nonce': nonce, 'X-JH-Body-Hash': body_hash, 'X-JH-Signature': signature, 'Content-Type': 'application/json'}


def _register(api, pair_id, secret, local_host, peer_host):
    payload = {'pair_id': pair_id, 'pair_name': pair_id, 'api_secret': secret, 'desired_master_host_id': 'H_DC_A', 'local_host': local_host, 'peer_host': peer_host}
    with app.test_request_context('/pub/ha_register_pair', method='POST', json=payload):
        res = json.loads(api.publicRegisterPair())
        assert res['status'], res


def _report_state(api, pair_id, secret, hosts, nonce):
    payload = {'pair_id': pair_id, 'hosts': hosts}
    with app.test_request_context('/pub/ha_report_state', method='POST', json=payload, headers=_headers(secret, payload, nonce)):
        res = json.loads(api.publicReportState())
        assert res['status'], res


def _event(api, pair_id, secret, run_id, origin, report, method, seq, nonce):
    payload = {
        'pair_id': pair_id,
        'switch_run_id': run_id,
        'event_id': pair_id + '-' + origin + '-' + str(seq),
        'origin_host_id': origin,
        'report_host_id': report,
        'collect_method': method,
        'seq': seq,
        'phase': 'peer_log' if method == 'ssh_peer' else 'online',
        'step': 'dual dc event',
        'status': 'running',
        'log_text': method + ' log from ' + origin
    }
    with app.test_request_context('/pub/ha_report_switch_event', method='POST', json=payload, headers=_headers(secret, payload, nonce)):
        res = json.loads(api.publicReportSwitchEvent())
        assert res['status'], res


def _assert_pair(api, pair_id):
    pair = api._normalizePair(api._getPair(pair_id))
    hosts = dict((x['host_id'], x) for x in pair['hosts'])
    assert set(hosts.keys()) == {'H_DC_A', 'H_DC_B'}
    assert hosts['H_DC_A']['collect_method'] in ('local', 'ssh_peer')
    assert hosts['H_DC_B']['collect_method'] in ('local', 'ssh_peer')
    assert hosts['H_DC_A']['collect_status'] == 'success'
    assert hosts['H_DC_B']['collect_status'] == 'success'


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    suffix = str(int(time.time()))
    secret = 'dual-secret-' + suffix
    host_a = {'host_id': 'H_DC_A', 'host_name': 'DC-A', 'host_ip': '10.20.1.1', 'role': 'master', 'online_status': 'online'}
    host_b = {'host_id': 'H_DC_B', 'host_name': 'DC-B', 'host_ip': '10.20.2.1', 'role': 'standby', 'online_status': 'online'}
    pair_a = 'HA_DUAL_A_' + suffix
    pair_b = 'HA_DUAL_B_' + suffix
    _register(api, pair_a, secret, host_a, host_b)
    _register(api, pair_b, secret, host_b, host_a)

    _report_state(api, pair_a, secret, [dict(host_a, collect_status='success', collect_method='local', report_host_id='H_DC_A', health_status='normal'), dict(host_b, collect_status='success', collect_method='ssh_peer', report_host_id='H_DC_A', health_status='normal')], pair_a + '-state')
    _report_state(api, pair_b, secret, [dict(host_b, collect_status='success', collect_method='local', report_host_id='H_DC_B', health_status='normal'), dict(host_a, collect_status='success', collect_method='ssh_peer', report_host_id='H_DC_B', health_status='normal')], pair_b + '-state')

    for pair_id, reporter in ((pair_a, 'H_DC_A'), (pair_b, 'H_DC_B')):
        with app.test_request_context('/ha/request_switch', method='POST', data={'pair_id': pair_id, 'target_host_id': 'H_DC_B'}):
            res = json.loads(api.requestSwitchApi())
            assert res['status'], res
            run_id = res['data']['switch_run_id']
        _event(api, pair_id, secret, run_id, reporter, reporter, 'local', 1, pair_id + '-event-local')
        peer_origin = 'H_DC_B' if reporter == 'H_DC_A' else 'H_DC_A'
        _event(api, pair_id, secret, run_id, peer_origin, reporter, 'ssh_peer', 2, pair_id + '-event-peer')
        run = api._getRun(run_id)
        with open(run['log_path'], 'r', encoding='utf-8') as fp:
            content = fp.read()
        assert 'local log from ' + reporter in content
        assert 'ssh_peer log from ' + peer_origin in content
        _assert_pair(api, pair_id)

    print('ok')


if __name__ == '__main__':
    main()
