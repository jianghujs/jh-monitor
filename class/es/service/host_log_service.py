# coding: utf-8

import datetime
import os
import sys
import traceback

import pytz

import jh

sys.path.append(os.getcwd() + "/class/es/query")
import host_query as host_query_utils


LOCAL_TIMEZONE = pytz.timezone('Asia/Singapore')


def _normalize_hits_total(total):
    if isinstance(total, dict):
        return int(total.get('value', 0) or 0)
    try:
        return int(total or 0)
    except Exception:
        return 0


def _format_timestamp(value, time_format='%Y-%m-%d %H:%M:%S'):
    raw_value = str(value or '').strip()
    if raw_value == '':
        return ''

    try:
        return jh.convertToLocalTime(raw_value, time_format=time_format)
    except Exception:
        pass

    formats = [
        '%Y-%m-%dT%H:%M:%S.%fZ',
        '%Y-%m-%dT%H:%M:%SZ',
        '%Y-%m-%dT%H:%M:%S.%f%z',
        '%Y-%m-%dT%H:%M:%S%z'
    ]
    for fmt in formats:
        try:
            dt = datetime.datetime.strptime(raw_value, fmt)
            if dt.tzinfo is None:
                dt = pytz.utc.localize(dt)
            return dt.astimezone(LOCAL_TIMEZONE).strftime(time_format)
        except Exception:
            continue
    return raw_value


def getLogPathList(host_ip):
    try:
        es = jh.getES()
        path_map = {}
        after_key = None

        while True:
            query = host_query_utils.buildLogPathCompositeSearchBody(
                host_ip,
                after_key=after_key,
                page_size=500
            )
            response = es.search(index=host_query_utils.LOG_MONITOR_INDEXES, body=query)
            if not isinstance(response, dict):
                break

            agg_data = response.get("aggregations", {}).get("unique_paths", {}) or {}
            buckets = agg_data.get("buckets", []) or []
            if len(buckets) == 0:
                break

            for bucket in buckets:
                bucket_key = bucket.get("key", {}) or {}
                path = str(bucket_key.get("path", "") or "").strip()
                if path == '':
                    continue

                latest_hits = bucket.get("latest_update", {}).get("hits", {}).get("hits", []) or []
                latest_hit = latest_hits[0] if latest_hits else {}
                latest_source = latest_hit.get("_source", {}) if latest_hit else {}
                latest_timestamp = str(latest_source.get("@timestamp", "") or "").strip()
                if path not in path_map or latest_timestamp > path_map[path].get("last_updated_raw", ""):
                    path_map[path] = {
                        "path": path,
                        "last_updated_raw": latest_timestamp,
                        "last_updated": _format_timestamp(latest_timestamp),
                        "source_index": str(latest_hit.get("_index", "") or "").strip()
                    }

            after_key = agg_data.get("after_key")
            if not after_key:
                break

        path_list = sorted(
            path_map.values(),
            key=lambda item: item.get("last_updated_raw", ""),
            reverse=True
        )
        for item in path_list:
            item.pop("last_updated_raw", None)
        return path_list
    except Exception:
        traceback.print_exc()
        return []


def searchLogDetail(host_ip, log_file_path, keyword='', page=1, limit=50):
    try:
        try:
            page = int(page)
        except Exception:
            page = 1
        if page < 1:
            page = 1

        try:
            limit = int(limit)
        except Exception:
            limit = 50
        if limit < 1:
            limit = 1
        if limit > 200:
            limit = 200

        es = jh.getES()
        query = host_query_utils.buildLogDetailSearchBody(
            host_ip,
            log_file_path,
            keyword=keyword,
            page=page,
            limit=limit
        )
        response = es.search(index=host_query_utils.LOG_MONITOR_INDEXES, body=query)
        if not isinstance(response, dict):
            return {
                "last_updated": "",
                "source_index": "",
                "keyword": str(keyword or '').strip(),
                "p": page,
                "limit": limit,
                "total": 0,
                "page": "<div><span class='Pcount'>共0条数据</span></div>",
                "log_content": []
            }

        hits = response.get("hits", {}).get("hits", []) or []
        total = _normalize_hits_total(response.get("hits", {}).get("total", 0))
        result = {
            "last_updated": "",
            "source_index": "",
            "keyword": str(keyword or '').strip(),
            "p": page,
            "limit": limit,
            "total": total,
            "page": "<div><span class='Pcount'>共0条数据</span></div>",
            "log_content": []
        }

        if hits:
            latest_source = hits[0].get("_source", {}) or {}
            result["last_updated"] = _format_timestamp(latest_source.get("@timestamp"))
            result["source_index"] = str(hits[0].get("_index", "") or "").strip()

        for hit in hits:
            source = hit.get("_source", {}) or {}
            result["log_content"].append({
                "create_time": _format_timestamp(source.get("@timestamp")),
                "content": source.get("message", "")
            })

        if total > 0:
            page_args = {
                'count': total,
                'tojs': 'getDetailHostLogMonitorPage',
                'p': page,
                'row': limit
            }
            result["page"] = jh.getPage(page_args)

        return result
    except Exception:
        traceback.print_exc()
        return {
            "last_updated": "",
            "source_index": "",
            "keyword": str(keyword or '').strip(),
            "p": 1,
            "limit": 50,
            "total": 0,
            "page": "<div><span class='Pcount'>共0条数据</span></div>",
            "log_content": []
        }
