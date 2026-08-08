# coding: utf-8

import json
import os
import sys
import time

ROOT = '/www/server/jh-monitor'
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, 'class/core'))

from route import app
from ha_api import ha_api


def _json(text):
    return json.loads(text)


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    pair_id = 'HA_UI_' + str(int(time.time()))
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

    with app.test_request_context('/ha/read_log', method='POST', data={'switch_run_id': switch_run_id, 'offset': 0}):
        res = _json(api.readLogApi())
        assert res['status']
        assert '创建切换任务' in res['data']['content']
        assert res['data']['next_offset'] > 0

    with app.test_request_context('/ha/cancel_switch', method='POST', data={'switch_run_id': switch_run_id}):
        assert _json(api.cancelSwitchApi())['status']
    with app.test_request_context('/ha/retry_switch', method='POST', data={'switch_run_id': switch_run_id}):
        assert _json(api.retrySwitchApi())['status']

    with app.test_request_context('/ha/save_callback_config', method='POST', data={'pair_id': pair_id, 'callback_url': 'http://127.0.0.1:9/callback', 'callback_enabled': '1'}):
        assert _json(api.saveCallbackConfigApi())['status']
    print('ok')


if __name__ == '__main__':
    main()
