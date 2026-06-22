# coding: utf-8

import os
import sys

import jh

sys.path.append(os.getcwd() + '/class/es/query')
import monitor_task_query as monitor_task_query_utils


def _get_source_from_response(response):
    if not isinstance(response, dict):
        return {}
    hits = response.get('hits', {}).get('hits', []) or []
    if len(hits) == 0:
        return {}
    source = hits[0].get('_source', {}) or {}
    source['_index'] = hits[0].get('_index', '')
    source['_id'] = hits[0].get('_id', '')
    return source


def getLatestTaskEvent(task_id, host_id, es_client=None):
    task_id = str(task_id or '').strip()
    host_id = str(host_id or '').strip()
    if task_id == '' or host_id == '':
        return {}
    es = es_client or jh.getES()
    body = monitor_task_query_utils.buildLatestTaskEventQuery(task_id, host_id)
    response = es.search(index=monitor_task_query_utils.TASK_EVENT_INDEX_PATTERN, body=body)
    return _get_source_from_response(response)


def getLatestTaskEventsBatch(task_host_pairs, es_client=None):
    """Fetch latest events for multiple (task_id, host_id) pairs in one msearch call.

    task_host_pairs: list of (task_id, host_id) tuples.
    Returns: dict mapping task_id -> latest event source dict (empty dict if no event found).
    """
    if not task_host_pairs:
        return {}
    body = monitor_task_query_utils.buildLatestTaskEventsMsearchBody(task_host_pairs)
    if not body:
        return {}
    es = es_client or jh.getES()
    try:
        response = es.msearch(body=body)
    except Exception:
        return {}
    result = {}
    if not isinstance(response, dict) or 'responses' not in response:
        return result
    responses = response.get('responses', []) or []
    # Build ordered pairs list (same order as msearch body, skipping empty ones)
    valid_pairs = []
    for task_id, host_id in task_host_pairs:
        task_id = str(task_id or '').strip()
        host_id = str(host_id or '').strip()
        if task_id and host_id:
            valid_pairs.append((task_id, host_id))
    for i, resp in enumerate(responses):
        if i >= len(valid_pairs):
            break
        task_id = valid_pairs[i][0]
        source = _get_source_from_response(resp) if isinstance(resp, dict) else {}
        result[task_id] = source
    return result
