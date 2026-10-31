# coding: utf-8

import json
import os
import sys


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'class', 'es', 'mapper'))
sys.path.insert(0, os.path.join(ROOT_DIR, 'class', 'plugin'))

import host_status_mapper


def main():
    host_row = {
        'host_id': 'H_TEST',
        'host_name': '机房入口机',
        'ip': '10.0.0.10'
    }
    status_doc = {
        'host': {
            'host_id': 'H_TEST',
            'host_name': 'system-hostname',
            'panel_title': 'prod-gateway-01',
            'host_ip': '10.0.0.10',
            'host_status': 'running',
            'system_type': 'debian'
        },
        'add_time': '2026-09-19 12:00:00',
        'add_timestamp': 1789790400
    }

    detail = host_status_mapper.buildHostDetailFromStatusDoc(host_row, status_doc, reference_time=1789790400 + 86399)
    host_info = json.loads(detail['host_info'])

    assert detail['host_name'] == 'prod-gateway-01', detail
    assert detail['host_remark'] == '机房入口机', detail
    assert host_info['hostName'] == 'prod-gateway-01', host_info
    assert detail['reporting_freshness'] == 'fresh', detail

    stale_detail = host_status_mapper.buildHostDetailFromStatusDoc(
        host_row, status_doc, reference_time=1789790400 + 86400
    )
    assert stale_detail['host_status'] == 'Running', stale_detail
    assert stale_detail['reporting_freshness'] == 'stale', stale_detail
    assert stale_detail['reporting_abnormal'], stale_detail

    stopped_doc = dict(status_doc)
    stopped_doc['host'] = dict(status_doc['host'], host_status='stopped')
    stale_stopped = host_status_mapper.buildHostDetailFromStatusDoc(
        host_row, stopped_doc, reference_time=1789790400 + 86400
    )
    assert stale_stopped['host_status'] == 'Stopped', stale_stopped
    assert stale_stopped['reporting_freshness'] == 'stale', stale_stopped

    recovered = host_status_mapper.buildHostDetailFromStatusDoc(
        host_row, status_doc, reference_time=1789790400 + 60
    )
    assert recovered['reporting_freshness'] == 'fresh', recovered

    host_row['addtime'] = 200000 - 86399
    empty_detail = host_status_mapper.buildHostDetailFromStatusDoc(host_row, None, reference_time=200000)
    assert empty_detail['host_name'] == '', empty_detail
    assert empty_detail['host_remark'] == '机房入口机', empty_detail
    assert empty_detail['reporting_freshness'] == 'pending', empty_detail

    host_row['addtime'] = 200000 - 86400
    never_detail = host_status_mapper.buildHostDetailFromStatusDoc(host_row, None, reference_time=200000)
    assert never_detail['reporting_freshness'] == 'never_reported', never_detail

    unavailable = host_status_mapper.buildHostDetailFromStatusDoc(
        host_row, None, reference_time=200000, storage_available=False
    )
    assert unavailable['reporting_freshness'] == 'unavailable', unavailable
    assert not unavailable['reporting_abnormal'], unavailable

    print('host status name mapping: ok')


if __name__ == '__main__':
    main()
