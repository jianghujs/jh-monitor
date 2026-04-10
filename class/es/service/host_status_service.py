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


def getLatestHostReportMap(host_rows, debug_fn=None, report_single_indexes=None, report_data_stream_indexes=None):
    try:
        if report_single_indexes is None:
            report_single_indexes = host_query_utils.HOST_REPORT_SINGLE_INDEXES
        if report_data_stream_indexes is None:
            report_data_stream_indexes = host_query_utils.HOST_REPORT_SINGLE_DATA_STREAM_INDEXES

        host_report = {}
        host_report_sort_key_map = {}
        if not host_rows:
            _debug(debug_fn, 'getLatestHostReportMap.empty_host_rows', {})
            return host_report

        host_ids = []
        for row in host_rows:
            host_id = str(row.get('host_id', '') or '').strip()
            if host_id != '' and host_id not in host_ids:
                host_ids.append(host_id)

        if len(host_ids) == 0:
            _debug(debug_fn, 'getLatestHostReportMap.empty_host_ids', {})
            return host_report

        es = jh.getES()

        def normalize_report_sort_text(value):
            raw_text = str(value or '').strip()
            if raw_text == '':
                return ''
            if len(raw_text) == 10 and raw_text.count('-') == 2:
                return raw_text + 'T00:00:00'
            if ' ' in raw_text and 'T' not in raw_text:
                return raw_text.replace(' ', 'T')
            return raw_text

        def build_report_sort_key(hit, doc, source_name):
            hit_sort_values = []
            for item in (hit.get('sort', []) if isinstance(hit, dict) else []):
                if isinstance(item, (int, float)):
                    hit_sort_values.append(str(item).rjust(20, '0'))
                else:
                    hit_sort_values.append(normalize_report_sort_text(item))

            report_time = normalize_report_sort_text(
                doc.get('report_time') or doc.get('report_time_text') or doc.get('@timestamp')
            )
            event_time = normalize_report_sort_text(doc.get('@timestamp') or doc.get('report_time'))
            report_date = normalize_report_sort_text(doc.get('report_date'))
            source_priority = 2 if source_name == 'data_stream' else 1

            return (
                report_time,
                event_time,
                report_date,
                source_priority,
                tuple(hit_sort_values)
            )

        def search_hits(index_name, body, source_name):
            try:
                response = es.search(index=index_name, body=body)
                if not isinstance(response, dict):
                    return []
                return response.get('hits', {}).get('hits', []) or []
            except Exception as ex:
                _debug(debug_fn, 'getLatestHostReportMap.search_exception', {
                    'source_name': source_name,
                    'index_name': index_name,
                    'error': str(ex)
                })
                return []

        def append_latest_docs(hits, source_name):
            for hit in hits:
                doc = hit.get('_source', {}) if isinstance(hit, dict) else {}
                host_id = str(doc.get('host_id', '') or '').strip()
                if host_id == '':
                    continue
                report_sort_key = build_report_sort_key(hit, doc, source_name)
                current_sort_key = host_report_sort_key_map.get(host_id)
                if current_sort_key is not None and report_sort_key <= current_sort_key:
                    continue
                host_report[host_id] = doc
                host_report_sort_key_map[host_id] = report_sort_key

        _debug(debug_fn, 'getLatestHostReportMap.start', {
            'host_count': len(host_rows),
            'host_ids': host_ids[:10],
            'report_single_indexes': report_single_indexes,
            'report_data_stream_indexes': report_data_stream_indexes
        })

        data_stream_hits = search_hits(
            report_data_stream_indexes,
            host_query_utils.buildLatestSingleHostReportDataStreamSearchBody(host_ids),
            'data_stream'
        )
        append_latest_docs(data_stream_hits, 'data_stream')

        legacy_hits = search_hits(
            report_single_indexes,
            host_query_utils.buildLatestSingleHostReportLegacySearchBody(host_ids),
            'legacy'
        )
        append_latest_docs(legacy_hits, 'legacy')

        _debug(debug_fn, 'getLatestHostReportMap.result', {
            'host_ids_requested': host_ids,
            'host_ids_found': list(host_report.keys()),
            'data_stream_hit_count': len(data_stream_hits),
            'legacy_hit_count': len(legacy_hits),
        })
        return host_report
    except Exception as ex:
        _debug(debug_fn, 'getLatestHostReportMap.exception', {
            'error': str(ex),
            'traceback': traceback.format_exc()
        })
        traceback.print_exc()
        return {}
