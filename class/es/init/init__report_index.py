#!/usr/bin/env python3
# coding: utf-8

import argparse
import copy
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ES_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(ES_DIR))
ES_MODEL_DIR = os.path.join(ES_DIR, 'model')
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if ES_DIR not in sys.path:
    sys.path.insert(0, ES_DIR)
if ES_MODEL_DIR not in sys.path:
    sys.path.insert(0, ES_MODEL_DIR)

from index_manager import IndexManager
from report_schema import REPORT_INDEXES, REPORT_INDEX_TEMPLATES


def build_args():
    parser = argparse.ArgumentParser(description='初始化服务器报告相关 ES 索引')
    parser.add_argument('--use-test-index', action='store_true', help='创建 host-report-*-test 测试索引')
    parser.add_argument('--check-only', action='store_true', help='只检查索引是否存在，不执行创建/更新')
    parser.add_argument('--all', action='store_true', help='同时初始化 REPORT_INDEXES 和 REPORT_INDEX_TEMPLATES 中的全部定义')
    return parser.parse_args()


def normalize_response(response):
    if hasattr(response, 'body'):
        return response.body
    if hasattr(response, 'to_dict'):
        return response.to_dict()
    return response or {}


def build_report_index_definitions(use_test_index=False):
    index_names = ['host-report-single', 'host-report-overview']
    definitions = {}
    for index_name in index_names:
        target_name = index_name + '-test' if use_test_index else index_name
        definitions[target_name] = copy.deepcopy(REPORT_INDEXES[index_name])
    return definitions


def fetch_index_summary(manager, index_name):
    exists = manager.es.indexExists(index_name)
    summary = {
        'index': index_name,
        'exists': bool(exists),
    }
    if not exists:
        return summary

    mapping_response = manager.es.getConn().indices.get_mapping(index=index_name)
    mapping_response = normalize_response(mapping_response)
    index_mapping = mapping_response.get(index_name, {})
    summary['mapping_fields'] = sorted(list((((index_mapping.get('mappings') or {}).get('properties') or {}).keys())))
    return summary


def main():
    args = build_args()
    manager = IndexManager()

    if args.all:
        index_definitions = copy.deepcopy(REPORT_INDEXES)
        template_definitions = copy.deepcopy(REPORT_INDEX_TEMPLATES)
        target_indices = list(index_definitions.keys())
    else:
        index_definitions = build_report_index_definitions(use_test_index=args.use_test_index)
        template_definitions = {}
        target_indices = list(index_definitions.keys())

    results = {
        'es_config': {
            'hosts': getattr(manager.es, '_es_hosts', []),
            'username': getattr(manager.es, '_username', ''),
            'config_path': getattr(manager.es, '_config_path', ''),
        },
        'target_indices': target_indices,
        'target_templates': list(template_definitions.keys()),
        'mode': 'check_only' if args.check_only else 'ensure',
        'scope': 'all' if args.all else ('report_test' if args.use_test_index else 'report'),
    }

    if args.check_only:
        results['indices'] = [fetch_index_summary(manager, index_name) for index_name in target_indices]
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    results['indices'] = manager.ensure_indices(index_definitions)
    if len(template_definitions) > 0:
        results['templates'] = manager.ensure_index_templates(template_definitions)
    else:
        results['templates'] = []
    results['index_summaries'] = [fetch_index_summary(manager, index_name) for index_name in target_indices]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
