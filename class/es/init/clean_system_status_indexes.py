#!/usr/bin/env python3
# coding: utf-8

import argparse
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ES_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(ES_DIR))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if ES_DIR not in sys.path:
    sys.path.insert(0, ES_DIR)

from index_manager import IndexManager


SYSTEM_STATUS_DATA_STREAM_PATTERNS = [
    'host-debian-*-system-status-*',
    'host-pve-*-system-status-*',
]

SYSTEM_STATUS_INDEX_PATTERNS = [
    'host-debian-system-status',
    'host-pve-system-status',
    'host-debian-*-system-status-*',
    'host-pve-*-system-status-*',
]


def normalize_response(response):
    if hasattr(response, 'body'):
        return response.body
    if hasattr(response, 'to_dict'):
        return response.to_dict()
    return response or {}


def _safe_get_data_stream_names(manager, pattern):
    try:
        response = manager.es.getConn().indices.get_data_stream(name=pattern)
        response = normalize_response(response)
    except Exception:
        return []
    data_streams = response.get('data_streams', []) or []
    return [item.get('name', '') for item in data_streams if item.get('name')]


def _safe_get_index_names(manager, pattern):
    try:
        response = manager.es.getConn().indices.get(
            index=pattern,
            expand_wildcards='all',
            allow_no_indices=True,
            ignore_unavailable=True,
        )
        response = normalize_response(response)
    except Exception:
        return []
    return [name for name in response.keys() if name]


def discover_system_status_resources(manager):
    data_stream_names = []
    for pattern in SYSTEM_STATUS_DATA_STREAM_PATTERNS:
        data_stream_names.extend(_safe_get_data_stream_names(manager, pattern))
    data_stream_names = sorted(list(dict.fromkeys(data_stream_names)))

    index_names = []
    for pattern in SYSTEM_STATUS_INDEX_PATTERNS:
        index_names.extend(_safe_get_index_names(manager, pattern))
    index_names = sorted(list(dict.fromkeys([
        name for name in index_names if name not in data_stream_names
    ])))

    return {
        'data_stream_patterns': list(SYSTEM_STATUS_DATA_STREAM_PATTERNS),
        'index_patterns': list(SYSTEM_STATUS_INDEX_PATTERNS),
        'data_streams': data_stream_names,
        'indices': index_names,
    }


def clean_system_status_resources(manager):
    resources = discover_system_status_resources(manager)
    results = {
        'resources': resources,
        'deleted_data_streams': manager.delete_data_streams(resources.get('data_streams', [])),
        'deleted_indices': manager.delete_indices(resources.get('indices', [])),
    }
    return results


def build_args():
    parser = argparse.ArgumentParser(description='清理所有 host-debian/host-pve system-status 索引与数据流')
    parser.add_argument('--check-only', action='store_true', help='只检查，不执行删除')
    return parser.parse_args()


def main():
    args = build_args()
    manager = IndexManager()
    resources = discover_system_status_resources(manager)
    results = {
        'es_config': {
            'hosts': getattr(manager.es, '_es_hosts', []),
            'username': getattr(manager.es, '_username', ''),
            'config_path': getattr(manager.es, '_config_path', ''),
        },
        'check_only': bool(args.check_only),
        'resources': resources,
    }
    if args.check_only:
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    results.update(clean_system_status_resources(manager))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
