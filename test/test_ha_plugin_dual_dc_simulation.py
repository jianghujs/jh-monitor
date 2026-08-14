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
    hosts = dict((x['name'], x) for x in pair['hosts'])
    assert set(hosts.keys()) == {'DC-A', 'DC-B'}, pair
    assert hosts['DC-A']['collect_method'] in ('local', 'ssh_peer'), hosts
    assert hosts['DC-B']['collect_method'] in ('local', 'ssh_peer'), hosts
    assert hosts['DC-A']['collect_status'] == 'success', hosts
    assert hosts['DC-B']['collect_status'] == 'success', hosts


def _assert_latest_plugin_view(api, pair_id, expected_roles, expected_methods):
    pair = api._normalizePair(api._getPair(pair_id))
    hosts = dict((x['name'], x) for x in pair['hosts'])
    assert len(hosts) == 2, pair
    for name, role in expected_roles.items():
        assert hosts[name]['role'] == role, (name, hosts[name], pair)
    for name, method in expected_methods.items():
        assert hosts[name]['collect_method'] == method, (name, hosts[name], pair)
    assert pair['status'] == 'normal', pair


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    cleanup_pair_ids = []
    atexit.register(_cleanup_pairs, cleanup_pair_ids)
    suffix = str(int(time.time()))
    secret = 'dual-secret-' + suffix
    host_a = {'host_id': 'H_DC_A', 'host_name': 'DC-A', 'host_ip': '10.20.1.1', 'role': 'master', 'online_status': 'online'}
    host_b = {'host_id': 'H_DC_B', 'host_name': 'DC-B', 'host_ip': '10.20.2.1', 'role': 'standby', 'online_status': 'online'}
    pair_a = 'HA_DUAL_A_' + suffix
    pair_b = 'HA_DUAL_B_' + suffix
    cleanup_pair_ids.extend([pair_a, pair_b])
    _register(api, pair_a, secret, host_a, host_b)
    _register(api, pair_b, secret, host_b, host_a)

    _report_state(api, pair_a, secret, [dict(host_a, collect_status='success', collect_method='local', report_host_id='H_DC_A', health_status='normal'), dict(host_b, collect_status='success', collect_method='ssh_peer', report_host_id='H_DC_A', health_status='normal')], pair_a + '-state')
    _report_state(api, pair_b, secret, [dict(host_b, collect_status='success', collect_method='local', report_host_id='H_DC_B', health_status='normal'), dict(host_a, collect_status='success', collect_method='ssh_peer', report_host_id='H_DC_B', health_status='normal')], pair_b + '-state')

    switched_host_a = dict(host_a, role='standby')
    switched_host_b = dict(host_b, role='master')
    _report_state(api, pair_a, secret, [
        dict(switched_host_b, collect_status='success', collect_method='local', report_host_id='H_DC_B', health_status='normal'),
        dict(switched_host_a, collect_status='success', collect_method='ssh_peer', report_host_id='H_DC_B', health_status='normal')
    ], pair_a + '-state-latest')
    _assert_latest_plugin_view(api, pair_a, {'DC-A': 'standby', 'DC-B': 'master'}, {'DC-A': 'ssh_peer', 'DC-B': 'local'})

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
