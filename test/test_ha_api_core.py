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


def call(api, method, path, payload=None, query=None):
    with app.test_request_context(path, method=method, json=payload, query_string=query):
        handler = {
            'create': api.pairCreateApi,
            'delete': api.pairDeleteApi,
            'update': api.pairUpdateApi,
            'sort': api.pairSortApi,
            'register': api.localRegisterApi,
            'report': api.localReportApi,
            'log': api.switchLogApi,
        }[path]
        return json.loads(handler())


def clean(api, pair_ids, task_ids):
    for pair_id in pair_ids:
        jh.M('ha_switch_task').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_host_state').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).delete()
    for task_id in task_ids:
        for suffix in ('.log', '.seq.json', '.lock'):
            path = os.path.join(api.LOG_ROOT, 'TASK_{0}{1}'.format(task_id, suffix))
            if os.path.exists(path):
                os.remove(path)


def host_payload(pair_id, host_id='H_LOCAL_TEST'):
    return {
        'pair_id': pair_id, 'host_id': host_id,
        'host_name': 'Local Test', 'host_ip': '127.0.0.1', 'role': 'standby',
        'online_status': 'online', 'health_status': 'normal', 'collect_status': 'success',
        'collect_method': 'local', 'health_detail': {'summary': '正常'},
    }


def main():
    api = ha_api()
    assert api.ensureHaSchema()
    suffix = str(int(time.time()))
    pair_id = ''
    other_pair_id = ''
    sort_pair_id = ''
    task_id = 'TASK_LOCAL_' + suffix
    clean(api, [], [task_id])
    try:
        custom_pair_id = 'HA_CUSTOM_' + suffix
        created = call(api, 'POST', 'create', {'pair_name': '本地主备接口', 'pair_id': custom_pair_id})
        assert created['status'], created
        pair_id = created['data']['pair_id']
        assert pair_id == custom_pair_id, created
        assert created['data']['pair_name'] == '本地主备接口'
        assert set(created['data']) == {'pair_id', 'pair_name'}, created
        assert api._getPair(pair_id)['status'] == 'unknown'
        assert not call(api, 'POST', 'create', {'pair_name': ''})['status']
        assert not call(api, 'POST', 'create', {'pair_name': '重复 ID', 'pair_id': custom_pair_id})['status']
        assert not call(api, 'POST', 'create', {'pair_name': '无效 ID', 'pair_id': 'invalid id'})['status']
        unknown = host_payload(pair_id + '_UNKNOWN')
        assert not call(api, 'POST', 'register', unknown)['status']
        registered = call(api, 'POST', 'register', host_payload(pair_id))
        assert registered['status'] and registered['data']['pair']['host']['host_id'] == 'H_LOCAL_TEST', registered

        heartbeat = call(api, 'POST', 'report', host_payload(pair_id))
        assert heartbeat['status'] and heartbeat['data']['switch_task_id'] == '', heartbeat
        invalid = host_payload(pair_id)
        invalid['role'] = 'invalid'
        assert not call(api, 'POST', 'report', invalid)['status']

        task_report = host_payload(pair_id)
        task_report['switch_task'] = {
            'switch_task_id': task_id, 'target_role': 'master', 'status': 'running',
            'status_text': '正在切换', 'current_step': '停止入口', 'next_step': '切换角色', 'step_summary': []
        }
        task_report['logs'] = [
            {'seq': 2, 'level': 'info', 'stage': 'switch', 'step': 'role', 'message': 'second'},
            {'seq': 1, 'level': 'info', 'stage': 'switch', 'step': 'start', 'message': 'first'},
        ]
        running = call(api, 'POST', 'report', task_report)
        assert running['status'] and running['data']['accepted_log_count'] == 2, running
        assert api._getPair(pair_id)['status'] == 'switching'

        updated_pair_id = pair_id + '_RENAMED'
        updated = call(api, 'POST', 'update', {
            'original_pair_id': pair_id, 'pair_id': updated_pair_id, 'pair_name': '本地主备接口已修改'
        })
        assert updated['status'] and updated['data']['pair_id'] == updated_pair_id, updated
        assert not api._getPair(pair_id)
        assert api._getPair(updated_pair_id)['pair_name'] == '本地主备接口已修改'
        assert api._getHost(updated_pair_id, 'H_LOCAL_TEST')
        assert api._getTask(task_id)['pair_id'] == updated_pair_id
        pair_id = updated_pair_id
        task_report['pair_id'] = pair_id

        duplicated = call(api, 'POST', 'report', task_report)
        assert duplicated['status'] and duplicated['data']['accepted_log_count'] == 0, duplicated
        log = call(api, 'GET', 'log', query={'switch_task_id': task_id, 'offset': '0'})
        assert log['status'] and log['data']['content'].find('first') < log['data']['content'].find('second'), log
        offset = log['data']['next_offset']
        log_next = call(api, 'GET', 'log', query={'switch_task_id': task_id, 'offset': str(offset)})
        assert log_next['status'] and log_next['data']['content'] == '', log_next
        assert not call(api, 'GET', 'log', query={'switch_task_id': task_id, 'offset': '-1'})['status']
        assert os.path.exists(os.path.join(api.LOG_ROOT, 'TASK_{0}.log'.format(task_id)))

        other = call(api, 'POST', 'create', {'pair_name': '本地主备接口二'})
        assert other['status']
        other_pair_id = other['data']['pair_id']
        assert other_pair_id != pair_id
        assert call(api, 'POST', 'register', host_payload(other_pair_id, 'H_OTHER'))['status']
        assert not call(api, 'POST', 'update', {
            'original_pair_id': pair_id, 'pair_id': other_pair_id, 'pair_name': '重复 ID'
        })['status']
        cross = host_payload(other_pair_id, 'H_OTHER')
        cross['switch_task'] = dict(task_report['switch_task'])
        assert not call(api, 'POST', 'report', cross)['status']

        sortable = call(api, 'POST', 'create', {'pair_name': '本地主备排序'})
        assert sortable['status']
        sort_pair_id = sortable['data']['pair_id']
        sorted_result = call(api, 'POST', 'sort', {'pair_ids': [sort_pair_id, other_pair_id, pair_id]})
        assert sorted_result['status'], sorted_result
        listed = json.loads(api.localListApi())['data']['list']
        sorted_ids = [item['pair_id'] for item in listed if item['pair_id'] in (pair_id, other_pair_id, sort_pair_id)]
        assert sorted_ids == [sort_pair_id, other_pair_id, pair_id], sorted_ids
        rejected_sort = call(api, 'POST', 'sort', {'pair_ids': [pair_id, 'UNKNOWN_PAIR_ID']})
        assert not rejected_sort['status'], rejected_sort

        cases = [
            ({'task_status': 'success', 'role': 'master', 'health_status': 'normal'}, 'normal'),
            ({'task_status': 'running'}, 'switching'),
            ({'task_status': 'failed'}, 'danger'),
            ({'task_status': 'success', 'online_status': 'offline'}, 'danger'),
            ({'task_status': 'success', 'health_status': 'danger'}, 'danger'),
            ({'task_status': 'success', 'health_status': 'warning'}, 'warning'),
            ({'task_status': 'success', 'role': 'standby', 'health_status': 'normal'}, 'normal'),
        ]
        for changes, expected in cases:
            task = dict(task_report['switch_task'])
            task['status'] = changes.get('task_status', 'success')
            body = host_payload(pair_id)
            body['switch_task'] = task
            body.update({key: value for key, value in changes.items() if key != 'task_status'})
            assert call(api, 'POST', 'report', body)['status']
            assert api._getPair(pair_id)['status'] == expected, (changes, api._getPair(pair_id))

        switching_with_transient_issue = host_payload(pair_id)
        switching_with_transient_issue.update({'online_status': 'offline', 'health_status': 'danger'})
        switching_with_transient_issue['switch_task'] = dict(task_report['switch_task'])
        switching_with_transient_issue['switch_task'].update({'status': 'running', 'current_step': '切换角色'})
        assert call(api, 'POST', 'report', switching_with_transient_issue)['status']
        pair = api._getPair(pair_id)
        assert pair['status'] == 'switching' and '切换角色' in pair['status_text'], pair
        completed_after_switch = host_payload(pair_id)
        completed_after_switch['switch_task'] = dict(task_report['switch_task'])
        completed_after_switch['switch_task']['status'] = 'success'
        assert call(api, 'POST', 'report', completed_after_switch)['status']

        second_host = host_payload(pair_id, 'H_LOCAL_SECOND')
        second_host.update({'host_name': 'Second Local', 'host_ip': '127.0.0.2', 'role': 'master'})
        assert call(api, 'POST', 'register', second_host)['status']
        pair = api._getPair(pair_id)
        assert pair['status'] == 'normal' and '2 台机器状态正常' in pair['status_text'], pair
        second_host.update({'health_status': 'warning', 'health_detail': {'summary': '磁盘空间不足'}})
        assert call(api, 'POST', 'report', second_host)['status']
        pair = api._getPair(pair_id)
        assert pair['status'] == 'warning' and 'Second Local：磁盘空间不足' in pair['status_text'], pair
        second_host.update({'online_status': 'offline', 'health_status': 'normal', 'health_detail': {'summary': '正常'}})
        assert call(api, 'POST', 'report', second_host)['status']
        pair = api._getPair(pair_id)
        assert pair['status'] == 'danger' and 'Second Local 已离线' in pair['status_text'], pair
        second_host.update({'online_status': 'online', 'role': 'standby'})
        assert call(api, 'POST', 'report', second_host)['status']
        pair = api._getPair(pair_id)
        assert pair['status'] == 'normal' and all(name in pair['status_text'] for name in ('Local Test', 'Second Local')), pair

        deleted = call(api, 'POST', 'delete', {'pair_id': pair_id})
        assert deleted['status'] and deleted['data']['pair_id'] == pair_id, deleted
        assert not api._getPair(pair_id)
        assert not jh.M('ha_host_state').where('pair_id=?', (pair_id,)).count()
        assert not jh.M('ha_switch_task').where('pair_id=?', (pair_id,)).count()
        assert not os.path.exists(os.path.join(api.LOG_ROOT, 'TASK_{0}.log'.format(task_id)))
        assert not call(api, 'POST', 'report', host_payload(pair_id))['status']
        pair_id = ''
        print('ok')
    finally:
        clean(api, [pair_id, other_pair_id, sort_pair_id], [task_id])


if __name__ == '__main__':
    main()
