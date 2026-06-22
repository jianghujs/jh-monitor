# coding: utf-8

TASK_EVENT_INDEX = 'host-monitor-task-event'
TASK_EVENT_INDEX_PATTERN = 'host-monitor-task-event*'

_SOURCE_FIELDS = ['task_id', 'task_name', 'host_id', 'host_ip', 'status', 'msg', 'run_at', 'log_path', 'collector_source', '@timestamp']


def buildLatestTaskEventQuery(task_id, host_id):
    return {
        'size': 1,
        'query': {
            'bool': {
                'filter': [
                    {'term': {'task_id': task_id}},
                    {'term': {'host_id': host_id}},
                ]
            }
        },
        'sort': [
            {'run_at': {'order': 'desc', 'unmapped_type': 'date'}},
            {'@timestamp': {'order': 'desc'}},
        ],
        '_source': _SOURCE_FIELDS,
    }


def buildLatestTaskEventsMsearchBody(task_host_pairs):
    """Build an msearch body for fetching the latest event of multiple (task_id, host_id) pairs.

    Returns a list of dicts: alternating header/body items for es.msearch().
    """
    items = []
    for task_id, host_id in task_host_pairs:
        task_id = str(task_id or '').strip()
        host_id = str(host_id or '').strip()
        if not task_id or not host_id:
            continue
        items.append({'index': TASK_EVENT_INDEX_PATTERN})
        items.append(buildLatestTaskEventQuery(task_id, host_id))
    return items
