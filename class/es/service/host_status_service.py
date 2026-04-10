# coding: utf-8

import os
import sys
import traceback

import jh

sys.path.append(os.getcwd() + "/class/plugin")
sys.path.append(os.getcwd() + "/class/es/mapper")
sys.path.append(os.getcwd() + "/class/es/query")
import value_tool as value_utils
import host_status_mapper as host_status_mapper_utils
import host_query as host_query_utils


def _debug(debug_fn, stage, payload=None):
    if debug_fn is None:
        return
    debug_fn(stage, payload)


def getLatestStatusDocs(host_rows, debug_fn=None, host_status_indexes=None):
    try:
        if host_status_indexes is None:
            host_status_indexes = host_query_utils.HOST_STATUS_INDEXES

        if not host_rows:
            _debug(debug_fn, 'getLatestStatusDocsFromES.empty_host_rows', {})
            return {}

        es = jh.getES()
        conn = es.getConn()
        if conn is None:
            _debug(debug_fn, 'getLatestStatusDocsFromES.no_conn', {
                'error': str(es.getError())
            })
            return {}

        index_status = {}
        for index_name in host_status_indexes.split(','):
            index_name = index_name.strip()
            if index_name == '':
                continue
            index_status[index_name] = es.indexExists(index_name)

        _debug(debug_fn, 'getLatestStatusDocsFromES.start', {
            'host_count': len(host_rows),
            'sample_hosts': [
                {
                    'host_id': row.get('host_id', ''),
                    'ip': row.get('ip', '')
                } for row in host_rows[:5]
            ],
            'index_status': index_status
        })

        msearch_body = []
        query_preview = []
        for row in host_rows:
            query_body = host_query_utils.buildLatestStatusQuery(row)
            msearch_body.append({
                "index": host_status_indexes,
                "expand_wildcards": "all",
                "ignore_unavailable": True,
                "allow_no_indices": True
            })
            msearch_body.append(host_query_utils.buildLatestStatusSearchBody(row))
            if len(query_preview) < 5:
                query_preview.append({
                    'host_id': row.get('host_id', ''),
                    'ip': row.get('ip', ''),
                    'query': query_body
                })

        _debug(debug_fn, 'getLatestStatusDocsFromES.query_preview', {
            'queries': query_preview
        })

        response = conn.msearch(body=msearch_body)
        parse_result = host_status_mapper_utils.buildLatestStatusMapFromMsearch(host_rows, response)
        status_map = parse_result.get('status_map', {})
        miss_hosts = parse_result.get('miss_hosts', [])

        _debug(debug_fn, 'getLatestStatusDocsFromES.result', {
            'response_count': parse_result.get('response_count', 0),
            'hit_count': len(status_map),
            'miss_sample': miss_hosts,
            'hit_sample': host_status_mapper_utils.buildStatusDocHitSample(status_map)
        })
        return status_map
    except Exception as ex:
        _debug(debug_fn, 'getLatestStatusDocsFromES.exception', {
            'error': str(ex),
            'traceback': traceback.format_exc()
        })
        traceback.print_exc()
        return {}


def getLatestHostDetailMap(host_rows, debug_fn=None, host_status_indexes=None):
    status_docs = getLatestStatusDocs(
        host_rows,
        debug_fn=debug_fn,
        host_status_indexes=host_status_indexes
    )
    return host_status_mapper_utils.buildHostDetailMapFromStatusDocs(host_rows, status_docs)


def getHostStatusHistory(host_id='', start=None, end=None, debug_fn=None, host_status_indexes=None):
    try:
        if host_status_indexes is None:
            host_status_indexes = host_query_utils.HOST_STATUS_INDEXES

        es = jh.getES()
        start_ts = None if start in (None, '') else value_utils.safeFloat(start, 0)
        end_ts = None if end in (None, '') else value_utils.safeFloat(end, 0)

        host_id = str(host_id or '').strip()
        query = host_query_utils.buildHostStatusHistoryQuery(host_id, start_ts, end_ts)
        search_body = host_query_utils.buildHostStatusHistorySearchBody(host_id, start_ts, end_ts)

        _debug(debug_fn, 'getHostStatusHistoryFromES.start', {
            'host_id': host_id,
            'start': start,
            'end': end,
            'start_ts': start_ts,
            'end_ts': end_ts,
            'query': query
        })

        docs = es.searchAll(
            index=host_status_indexes,
            body=search_body,
            source_fields=host_query_utils.HOST_STATUS_SOURCE_FIELDS
        )
        if not docs:
            _debug(debug_fn, 'getHostStatusHistoryFromES.empty_docs', {
                'host_id': host_id,
                'start_ts': start_ts,
                'end_ts': end_ts
            })
            return []

        history = host_status_mapper_utils.buildHistoryDetailsFromStatusDocs(docs)

        _debug(debug_fn, 'getHostStatusHistoryFromES.result', {
            'host_id': host_id,
            'doc_count': len(docs),
            'first_doc': {
                'host': (docs[0].get('host') or {}),
                'add_time': docs[0].get('add_time', ''),
                'add_timestamp': docs[0].get('add_timestamp', 0)
            },
            'last_doc': {
                'host': (docs[-1].get('host') or {}),
                'add_time': docs[-1].get('add_time', ''),
                'add_timestamp': docs[-1].get('add_timestamp', 0)
            }
        })
        return history
    except Exception as ex:
        _debug(debug_fn, 'getHostStatusHistoryFromES.exception', {
            'host_id': host_id,
            'error': str(ex),
            'traceback': traceback.format_exc()
        })
        traceback.print_exc()
        return []
