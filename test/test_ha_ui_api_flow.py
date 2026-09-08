# coding: utf-8

import json
import os
import sys
import time

ROOT = '/www/server/jh-monitor'
sys.path[:0] = [ROOT, os.path.join(ROOT, 'class/core')]

from route import app
from ha_api import ha_api
import jh


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    pair_id = ''
    try:
        custom_pair_id = 'HA_UI_LOCAL_' + str(int(time.time()))
        with app.test_request_context('/ha/api/local/pair/create', method='POST', json={'pair_name': '本地主备界面', 'pair_id': custom_pair_id}):
            created = json.loads(api.pairCreateApi())
        assert created['status']
        pair_id = created['data']['pair_id']
        assert pair_id == custom_pair_id, created
        assert 'api_secret' not in created['data']
        payload = {
            'pair_id': pair_id, 'host_id': 'H_UI_LOCAL', 'host_name': 'UI Local',
            'host_ip': '10.0.0.10', 'role': 'master', 'online_status': 'online', 'health_status': 'warning',
            'collect_status': 'success', 'collect_method': 'local', 'health_detail': {'summary': '自检提醒'}
        }
        with app.test_request_context('/ha/api/local/register', method='POST', json=payload):
            assert json.loads(api.localRegisterApi())['status']
        second_payload = dict(payload)
        second_payload.update({
            'host_id': 'H_UI_LOCAL_STANDBY', 'host_name': 'UI Local Standby', 'host_ip': '10.0.0.11',
            'role': 'standby', 'online_status': 'offline', 'health_status': 'danger',
        })
        with app.test_request_context('/ha/api/local/register', method='POST', json=second_payload):
            assert json.loads(api.localRegisterApi())['status']
        with app.test_request_context('/ha/api/local/list', method='GET'):
            listed = json.loads(api.localListApi())
        pair = [item for item in listed['data']['list'] if item['pair_id'] == pair_id][0]
        assert pair['pair_name'] == '本地主备界面' and pair['pair_id'] != pair['pair_name'], pair
        assert pair['host']['host_name'] == 'UI Local Standby' and pair['status'] == 'danger', pair
        assert [host['host_id'] for host in pair['hosts']] == ['H_UI_LOCAL_STANDBY', 'H_UI_LOCAL'], pair
        with app.test_request_context('/ha/api/local/detail', method='GET', query_string={'pair_id': pair_id}):
            detail = json.loads(api.localDetailApi())
        assert detail['status'] and detail['data']['pair_id'] == pair_id and detail['data']['pair_name'] == '本地主备界面', detail
        assert detail['data']['tasks'] == [] and len(detail['data']['hosts']) == 2, detail
        updated_pair_id = pair_id + '_EDIT'
        with app.test_request_context('/ha/api/local/pair/update', method='POST', json={
            'original_pair_id': pair_id, 'pair_id': updated_pair_id, 'pair_name': '本地主备界面已修改'
        }):
            updated = json.loads(api.pairUpdateApi())
        assert updated['status'] and updated['data']['pair_id'] == updated_pair_id, updated
        pair_id = updated_pair_id
        with app.test_request_context('/ha/api/local/detail', method='GET', query_string={'pair_id': pair_id}):
            detail = json.loads(api.localDetailApi())
        assert detail['status'] and detail['data']['pair_name'] == '本地主备界面已修改', detail
        with app.test_request_context('/ha/api/local/pair/delete', method='POST', json={'pair_id': pair_id}):
            deleted = json.loads(api.pairDeleteApi())
        assert deleted['status']
        with app.test_request_context('/ha/api/local/detail', method='GET', query_string={'pair_id': pair_id}):
            assert not json.loads(api.localDetailApi())['status']
        pair_id = ''
        print('ok')
    finally:
        jh.M('ha_switch_task').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_host_state').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).delete()


if __name__ == '__main__':
    main()
