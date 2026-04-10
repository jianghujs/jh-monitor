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
from report_schema import REPORT_INDEXES, REPORT_INDEX_TEMPLATES, REPORT_DATA_STREAMS


def build_args():
    parser = argparse.ArgumentParser(description='初始化服务器报告相关 ES 索引')
    parser.add_argument('--use-test-index', action='store_true', help='创建 host-report-*-test 测试索引')
    parser.add_argument('--check-only', action='store_true', help='只检查索引是否存在，不执行创建/更新')
    parser.add_argument('--all', action='store_true', help='同时初始化 REPORT_INDEXES 和 REPORT_INDEX_TEMPLATES 中的全部定义')
    parser.add_argument('--sync-existing-indices', action='store_true', help='同步更新已存在的报告普通索引 mapping，可能因历史字段类型冲突失败')
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


def build_report_data_stream_templates(use_test_index=False):
    template_names = ['host-report-single-ds-template', 'host-report-overview-ds-template']
    definitions = {}
    for template_name in template_names:
        template_definition = copy.deepcopy(REPORT_INDEX_TEMPLATES[template_name])
        if use_test_index:
            template_definition['index_patterns'] = [pattern + '-test' for pattern in template_definition.get('index_patterns', [])]
        definitions[template_name + ('-test' if use_test_index else '')] = template_definition
    return definitions


def build_report_data_stream_names(use_test_index=False):
    names = [REPORT_DATA_STREAMS['single'], REPORT_DATA_STREAMS['overview']]
    if use_test_index:
        return [name + '-test' for name in names]
    return names


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


def ensure_report_indices(manager, index_definitions, sync_existing_indices=False):
    results = []
    for index_name, index_body in index_definitions.items():
        exists = manager.es.indexExists(index_name)
        if exists:
            if not sync_existing_indices:
                results.append({
                    'index': index_name,
                    'action': 'exists_skipped',
                    'note': '已存在，默认不更新 mapping，避免历史字段类型冲突影响数据流初始化'
                })
                continue
            response = manager.es.putMapping(index_name, index_body.get('mappings', {}))
            if response is None:
                raise Exception('failed to sync index {0}: {1}'.format(
                    index_name,
                    manager.es.getError()
                ))
            results.append({'index': index_name, 'action': 'updated'})
            continue

        response = manager.es.createIndex(index_name, index_body)
        if response is None:
            raise Exception('failed to create index {0}: {1}'.format(
                index_name,
                manager.es.getError()
            ))
        results.append({'index': index_name, 'action': 'created'})
    return results


def fetch_data_stream_summary(manager, data_stream_name):
    summary = {
        'data_stream': data_stream_name,
        'exists': bool(manager.es.dataStreamExists(data_stream_name)),
    }
    if not summary['exists']:
        return summary

    response = manager.es.getConn().indices.get_data_stream(name=data_stream_name)
    response = normalize_response(response)
    current = (response.get('data_streams') or [{}])[0]
    summary['backing_indices'] = [item.get('index_name', '') for item in current.get('indices', [])]
    summary['template'] = current.get('template', '')
    return summary


def main():
    args = build_args()
    manager = IndexManager()

    if args.all:
        index_definitions = copy.deepcopy(REPORT_INDEXES)
        template_definitions = copy.deepcopy(REPORT_INDEX_TEMPLATES)
        target_indices = list(index_definitions.keys())
        data_stream_templates = build_report_data_stream_templates(False)
        template_definitions.update(data_stream_templates)
        target_data_streams = build_report_data_stream_names(False)
    else:
        index_definitions = build_report_index_definitions(use_test_index=args.use_test_index)
        template_definitions = build_report_data_stream_templates(use_test_index=args.use_test_index)
        target_indices = list(index_definitions.keys())
        target_data_streams = build_report_data_stream_names(use_test_index=args.use_test_index)

    results = {
        'es_config': {
            'hosts': getattr(manager.es, '_es_hosts', []),
            'username': getattr(manager.es, '_username', ''),
            'config_path': getattr(manager.es, '_config_path', ''),
        },
        'target_indices': target_indices,
        'target_templates': list(template_definitions.keys()),
        'target_data_streams': target_data_streams,
        'mode': 'check_only' if args.check_only else 'ensure',
        'scope': 'all' if args.all else ('report_test' if args.use_test_index else 'report'),
    }

    if args.check_only:
        results['indices'] = [fetch_index_summary(manager, index_name) for index_name in target_indices]
        results['data_streams'] = [fetch_data_stream_summary(manager, data_stream_name) for data_stream_name in target_data_streams]
        print(json.dumps(results, ensure_ascii=False, indent=2))
        return 0

    if args.all:
        results['indices'] = manager.ensure_indices(index_definitions)
    else:
        results['indices'] = ensure_report_indices(
            manager,
            index_definitions,
            sync_existing_indices=args.sync_existing_indices
        )
    results['templates'] = manager.ensure_index_templates(template_definitions) if len(template_definitions) > 0 else []
    results['data_streams'] = manager.ensure_data_streams(target_data_streams)
    results['index_summaries'] = [fetch_index_summary(manager, index_name) for index_name in target_indices]
    results['data_stream_summaries'] = [fetch_data_stream_summary(manager, data_stream_name) for data_stream_name in target_data_streams]
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
