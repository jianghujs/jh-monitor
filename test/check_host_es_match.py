#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORE_DIR = os.path.join(ROOT_DIR, 'class', 'core')
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
QUERY_DIR = os.path.join(ROOT_DIR, 'class', 'es', 'query')

for path in (ROOT_DIR, CORE_DIR, PLUGIN_DIR, QUERY_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(ROOT_DIR)

import jh
from es import ES
import host_query as host_query_utils


HOST_FIELDS = 'id,host_id,host_name,ip,is_pve,is_jhpanel,host_group_id,host_group_name'


def parse_args():
    parser = argparse.ArgumentParser(description='检查 host_api 为什么没有读到 ES 最新主机状态')
    parser.add_argument('--host-id', default='', help='只检查指定 host_id')
    parser.add_argument('--ip', default='', help='只检查指定 IP')
    parser.add_argument('--limit', type=int, default=20, help='默认最多检查多少条主机记录')
    return parser.parse_args()


def normalize_response(response):
    if hasattr(response, 'body'):
        return response.body
    if hasattr(response, 'to_dict'):
        return response.to_dict()
    return response or {}


def fetch_panel_rows(host_id='', ip='', limit=20):
    host_m = jh.M('host')
    if host_id:
        host_m.where('host_id=?', (host_id,))
    if ip:
        host_m.where('ip=?', (ip,))
    rows = host_m.field(HOST_FIELDS).order('id desc').limit(str(limit)).select()
    if isinstance(rows, str) or rows is None:
        return []
    return rows


def build_single_should_query(host_id='', ip=''):
    should_filters = []
    host_id = str(host_id or '').strip()
    ip = str(ip or '').strip()
    if host_id:
        should_filters.append({"term": {"host.host_id": host_id}})
    if ip:
        should_filters.append({"term": {"host.host_ip": ip}})
    if len(should_filters) == 0:
        return {"match_none": {}}
    return {
        "bool": {
            "filter": [
                {
                    "bool": {
                        "should": should_filters,
                        "minimum_should_match": 1
                    }
                }
            ]
        }
    }


def search_latest(es, query):
    response = es.search(
        index=host_query_utils.HOST_STATUS_INDEXES,
        body={
            "size": 1,
            "query": query,
            "sort": [
                {
                    "add_timestamp": {
                        "order": "desc",
                        "unmapped_type": "double"
                    }
                }
            ],
            "_source": [
                "host",
                "add_time",
                "add_timestamp",
                "collector"
            ]
        }
    )
    response = normalize_response(response)
    hits = ((response.get('hits') or {}).get('hits') or [])
    if not hits:
        return None
    hit = hits[0]
    return {
        "index": hit.get('_index', ''),
        "source": hit.get('_source', {})
    }


def build_result_for_row(es, row):
    panel_host_id = str(row.get('host_id', '') or '').strip()
    panel_ip = str(row.get('ip', '') or '').strip()

    host_api_hit = search_latest(es, host_query_utils.buildLatestStatusQuery(row))
    host_id_hit = search_latest(es, build_single_should_query(host_id=panel_host_id))
    ip_hit = search_latest(es, build_single_should_query(ip=panel_ip))

    reasons = []
    if host_api_hit is None:
        reasons.append('host_api_query_no_hit')
    if panel_host_id == '':
        reasons.append('panel_host_id_empty')
    if panel_ip == '':
        reasons.append('panel_ip_empty')
    if host_api_hit is None and host_id_hit is not None and ip_hit is None:
        reasons.append('host_id_can_hit_but_ip_cannot')
    if host_api_hit is None and host_id_hit is None and ip_hit is not None:
        reasons.append('ip_can_hit_but_host_id_cannot')
    if host_api_hit is None and host_id_hit is None and ip_hit is None:
        reasons.append('no_es_status_doc_found_for_host_id_or_ip')

    return {
        "panel_row": row,
        "host_api_query": host_query_utils.buildLatestStatusQuery(row),
        "host_api_hit": host_api_hit,
        "host_id_hit": host_id_hit,
        "ip_hit": ip_hit,
        "reasons": reasons
    }


def main():
    args = parse_args()
    es = ES()
    rows = fetch_panel_rows(host_id=args.host_id, ip=args.ip, limit=args.limit)
    if len(rows) == 0:
        print(json.dumps({
            "status": "error",
            "message": "未找到匹配的面板主机记录",
            "host_id": args.host_id,
            "ip": args.ip
        }, ensure_ascii=False, indent=2))
        return 1

    results = [build_result_for_row(es, row) for row in rows]
    print(json.dumps({
        "indexes": host_query_utils.HOST_STATUS_INDEXES,
        "host_count": len(results),
        "results": results
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
