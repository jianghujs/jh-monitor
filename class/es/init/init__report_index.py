#!/usr/bin/env python3
# coding: utf-8

import argparse
import copy
import datetime
import fnmatch
import json
import os
import sys
import tempfile
import time

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
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from clean_system_status_indexes import discover_system_status_resources, clean_system_status_resources
from index_manager import IndexManager
from log_tool import LogTool
from report_schema import (
    REPORT_INDEXES,
    REPORT_INDEX_TEMPLATES,
    REPORT_DATA_STREAMS,
    TASK_EVENT_INDEXES,
    TASK_EVENT_INDEX_TEMPLATES,
)


def build_args():
    parser = argparse.ArgumentParser(description='初始化服务器报告相关 ES 索引')
    parser.add_argument('--use-test-index', action='store_true', help='创建 host-report-*-test 测试索引')
    parser.add_argument('--check-only', action='store_true', help='只检查索引是否存在，不执行创建/更新')
    parser.add_argument('--all', action='store_true', help='同时初始化 REPORT_INDEXES 和 REPORT_INDEX_TEMPLATES 中的全部定义')
    parser.add_argument('--overwrite', dest='overwrite', action='store_true', default=True, help='覆盖重建目标索引/模板/数据流：先删除旧资源，再按当前定义重建（默认开启）')
    parser.add_argument('--no-overwrite', dest='overwrite', action='store_false', help='不删除旧资源，只执行创建/更新')
    parser.add_argument('--clean-system-status', dest='clean_system_status', action='store_true', default=None, help='初始化前先清理所有 system-status 索引/数据流')
    parser.add_argument('--skip-clean-system-status', dest='clean_system_status', action='store_false', help='初始化前跳过 system-status 清理')
    parser.add_argument('--sync-existing-indices', action='store_true', help='同步更新已存在的报告普通索引 mapping，可能因历史字段类型冲突失败')
    parser.add_argument('--month', default='', help='指定报告数据流月份，格式 YYYY-MM，默认当前月份')
    parser.add_argument('--task-events', action='store_true', help='仅初始化 host-monitor-task-event 索引/模板')
    return parser.parse_args()


logger = LogTool('es-init')


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
            template_definition['index_patterns'] = [pattern.replace('host-report-', 'host-report-test-') for pattern in template_definition.get('index_patterns', [])]
        definitions[template_name + ('-test' if use_test_index else '')] = template_definition
    return definitions


def normalize_month(month_text=''):
    raw_text = str(month_text or '').strip()
    if raw_text == '':
        return datetime.datetime.now().strftime('%Y-%m')
    return datetime.datetime.strptime(raw_text, '%Y-%m').strftime('%Y-%m')


def build_report_data_stream_names(use_test_index=False, month_text=''):
    month_value = normalize_month(month_text)
    names = [
        '{0}-{1}'.format(REPORT_DATA_STREAMS['single_prefix'], month_value),
        '{0}-{1}'.format(REPORT_DATA_STREAMS['overview_prefix'], month_value),
    ]
    if use_test_index:
        return [name.replace('host-report-', 'host-report-test-') for name in names]
    return names

def build_task_event_definitions(use_test_index=False):
    index_definitions = copy.deepcopy(TASK_EVENT_INDEXES)
    template_definitions = copy.deepcopy(TASK_EVENT_INDEX_TEMPLATES)
    if use_test_index:
        for index_name in list(index_definitions.keys()):
            renamed = index_name + '-test'
            index_definitions[renamed] = index_definitions.pop(index_name)
        for template_name in list(template_definitions.keys()):
            body = template_definitions[template_name]
            renamed = template_name + '-test'
            body['index_patterns'] = [pattern.replace('host-monitor-task-event', 'host-monitor-task-event-test') for pattern in body.get('index_patterns', [])]
            body['priority'] = max(int(body.get('priority', 500)) + 1, 100)
            template_definitions[renamed] = template_definitions.pop(template_name)
    return index_definitions, template_definitions


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
                logger.info('|--- 索引已存在跳过', index=index_name, action='exists_skipped')
                results.append({
                    'index': index_name,
                    'action': 'exists_skipped',
                    'note': '已存在，默认不更新 mapping，避免历史字段类型冲突影响数据流初始化'
                })
                continue
            response = manager.es.putMapping(index_name, index_body.get('mappings', {}))
            if response is None:
                logger.detail_fail('索引 mapping 同步失败', index=index_name, error=manager.es.getError())
                raise Exception('failed to sync index {0}: {1}'.format(
                    index_name,
                    manager.es.getError()
                ))
            logger.detail_ok('索引 mapping 同步完成', index=index_name, action='updated')
            results.append({'index': index_name, 'action': 'updated'})
            continue

        response = manager.es.createIndex(index_name, index_body)
        if response is None:
            logger.detail_fail('索引创建失败', index=index_name, error=manager.es.getError())
            raise Exception('failed to create index {0}: {1}'.format(
                index_name,
                manager.es.getError()
            ))
        logger.detail_ok('索引创建完成', index=index_name, action='created')
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


def _safe_get_all_data_streams(manager):
    try:
        response = manager.es.getConn().indices.get_data_stream(name='*')
        response = normalize_response(response)
    except Exception:
        return []
    return response.get('data_streams', []) or []


def _safe_get_index_template(manager, template_name):
    try:
        response = manager.es.getConn().indices.get_index_template(name=template_name)
        response = normalize_response(response)
    except Exception:
        return {}
    templates = response.get('index_templates', []) or []
    if len(templates) == 0:
        return {}
    return (templates[0].get('index_template') or {})


def resolve_overwrite_data_streams(manager, template_definitions, target_data_streams):
    resolved_names = list(target_data_streams or [])
    template_names = list(template_definitions.keys())
    template_patterns = []

    for template_body in template_definitions.values():
        template_patterns.extend(template_body.get('index_patterns', []) or [])

    for template_name in template_names:
        existing_template = _safe_get_index_template(manager, template_name)
        template_patterns.extend(existing_template.get('index_patterns', []) or [])

    all_data_streams = _safe_get_all_data_streams(manager)
    for data_stream in all_data_streams:
        data_stream_name = data_stream.get('name', '')
        data_stream_template = data_stream.get('template', '')
        if data_stream_name == '':
            continue
        if data_stream_template in template_names:
            resolved_names.append(data_stream_name)
            continue
        for pattern in template_patterns:
            if fnmatch.fnmatch(data_stream_name, pattern):
                resolved_names.append(data_stream_name)
                break

    for pattern in template_patterns:
        resolved_names.extend(_safe_get_data_stream_names(manager, pattern))

    return sorted(list(dict.fromkeys([name for name in resolved_names if name])))


def resolve_data_stream_conflict_indices(manager, data_stream_names):
    conflict_indices = []
    for data_stream_name in data_stream_names:
        if manager.es.dataStreamExists(data_stream_name):
            continue
        conflict_indices.extend(_safe_get_index_names(manager, data_stream_name))
    return sorted(list(dict.fromkeys([name for name in conflict_indices if name])))


def overwrite_targets(manager, target_indices, template_definitions, target_data_streams):
    overwrite_data_streams = resolve_overwrite_data_streams(manager, template_definitions, target_data_streams)
    conflict_indices = resolve_data_stream_conflict_indices(manager, overwrite_data_streams)
    results = {
        'resolved_data_streams': overwrite_data_streams,
        'deleted_data_streams': manager.delete_data_streams(overwrite_data_streams),
        'resolved_conflict_indices': conflict_indices,
        'deleted_indices': manager.delete_indices(list(target_indices) + conflict_indices),
        'deleted_templates': manager.delete_index_templates(list(template_definitions.keys())),
    }
    return results


def should_clean_system_status(args, resources):
    if args.check_only:
        return False
    if args.clean_system_status is not None:
        return bool(args.clean_system_status)
    if len(resources.get('data_streams', [])) == 0 and len(resources.get('indices', [])) == 0:
        return False
    if not sys.stdin.isatty():
        return False

    print('检测到以下 system-status 资源:')
    print(json.dumps(resources, ensure_ascii=False, indent=2))
    answer = input('初始化前是否清理全部 system-status 索引/数据流？[y/N]: ').strip().lower()
    return answer in ['y', 'yes']


def main():
    start_time = time.time()
    args = build_args()
    manager = IndexManager()
    logger.separator(long=True)
    logger.start('开始初始化ES报告相关索引',
             scope='task_events' if args.task_events else ('all' if args.all else ('report_test' if args.use_test_index else 'report')),
             mode='check_only' if args.check_only else 'ensure',
             overwrite=bool(args.overwrite),
             month=normalize_month(args.month),
             use_test_index=bool(args.use_test_index))

    if args.task_events:
        index_definitions, template_definitions = build_task_event_definitions(use_test_index=args.use_test_index)
        target_indices = list(index_definitions.keys())
        target_data_streams = []
    elif args.all:
        index_definitions = copy.deepcopy(REPORT_INDEXES)
        template_definitions = copy.deepcopy(REPORT_INDEX_TEMPLATES)
        task_index_definitions, task_template_definitions = build_task_event_definitions(False)
        index_definitions.update(task_index_definitions)
        template_definitions.update(task_template_definitions)
        target_indices = list(index_definitions.keys())
        data_stream_templates = build_report_data_stream_templates(False)
        template_definitions.update(data_stream_templates)
        target_data_streams = build_report_data_stream_names(False, args.month)
    else:
        index_definitions = build_report_index_definitions(use_test_index=args.use_test_index)
        template_definitions = build_report_data_stream_templates(use_test_index=args.use_test_index)
        target_indices = list(index_definitions.keys())
        target_data_streams = build_report_data_stream_names(use_test_index=args.use_test_index, month_text=args.month)

    results = {
        'es_config': {
            'hosts': getattr(manager.es, '_es_hosts', []),
            'username': getattr(manager.es, '_username', ''),
            'config_path': getattr(manager.es, '_config_path', ''),
        },
        'target_indices': target_indices,
        'target_templates': list(template_definitions.keys()),
        'target_data_streams': target_data_streams,
        'month': normalize_month(args.month),
        'mode': 'check_only' if args.check_only else 'ensure',
        'overwrite': bool(args.overwrite),
        'clean_system_status': args.clean_system_status,
        'scope': 'task_events' if args.task_events else ('all' if args.all else ('report_test' if args.use_test_index else 'report')),
    }

    logger.detail_ok('解析初始化目标完成',
             indices=len(target_indices),
             templates=len(template_definitions),
             data_streams=len(target_data_streams))
    logger.info('|--- 目标索引列表', items=target_indices)
    logger.info('|--- 目标模板列表', items=list(template_definitions.keys()))
    logger.info('|--- 目标数据流列表', items=target_data_streams)

    logger.info('|- 开始扫描 system-status 历史资源')
    system_status_resources = discover_system_status_resources(manager)
    results['system_status_resources'] = system_status_resources
    logger.detail_ok('system-status 资源扫描完成',
             indices=len((system_status_resources or {}).get('indices', []) or []),
             data_streams=len((system_status_resources or {}).get('data_streams', []) or []))

    if args.check_only:
        logger.info('|- 进入只读检查模式，跳过任何写操作')
        results['indices'] = [fetch_index_summary(manager, index_name) for index_name in target_indices]
        results['data_streams'] = [fetch_data_stream_summary(manager, data_stream_name) for data_stream_name in target_data_streams]
        logger.detail_ok('索引存在性检查完成', count=len(results['indices']))
        logger.detail_ok('数据流存在性检查完成', count=len(results['data_streams']))
        logger.done('ES索引检查完成', useTime='{0:.2f}s'.format(time.time() - start_time))
        logger.separator(long=True)
        _tmp = tempfile.NamedTemporaryFile(
            prefix='es-init-check-', suffix='.json',
            delete=False, mode='w', encoding='utf-8',
            dir='/tmp',
        )
        try:
            _tmp.write(json.dumps(results, ensure_ascii=False, indent=2))
            _tmp.close()
            logger.info('完整运行结果已写入', file=_tmp.name)
        except Exception:
            _tmp.close()
            raise
        return 0

    if should_clean_system_status(args, system_status_resources):
        logger.info('|- 开始清理 system-status 历史资源')
        results['system_status_cleanup'] = clean_system_status_resources(manager)
        logger.detail_ok('system-status 历史资源清理完成',
                 deleted_data_streams=len((results['system_status_cleanup'] or {}).get('deleted_data_streams', []) or []),
                 deleted_indices=len((results['system_status_cleanup'] or {}).get('deleted_indices', []) or []))
    else:
        logger.info('|--- 跳过 system-status 清理', reason='check_only/未确认/无资源')
        results['system_status_cleanup'] = {
            'skipped': True,
            'resources': system_status_resources,
        }

    if args.overwrite:
        logger.info('|- 开始覆盖重建：删除旧索引/模板/数据流')
        results['overwrite_deleted'] = overwrite_targets(
            manager,
            target_indices,
            template_definitions,
            target_data_streams
        )
        _overwrite_info = results['overwrite_deleted'] or {}
        logger.detail_ok('覆盖重建删除完成',
                 deleted_data_streams=len(_overwrite_info.get('deleted_data_streams', []) or []),
                 deleted_indices=len(_overwrite_info.get('deleted_indices', []) or []),
                 deleted_templates=len(_overwrite_info.get('deleted_templates', []) or []))
    else:
        logger.info('|--- 跳过覆盖重建', reason='--no-overwrite')

    logger.info('|- 开始创建/检查目标索引', count=len(index_definitions))
    try:
        results['indices'] = ensure_report_indices(
            manager,
            index_definitions,
            sync_existing_indices=args.sync_existing_indices
        )
    except Exception as ex:
        logger.fail('索引创建/检查失败', error=str(ex), useTime='{0:.2f}s'.format(time.time() - start_time))
        logger.separator(long=True)
        raise
    logger.detail_ok('索引创建/检查完成', count=len(results['indices']))

    logger.info('|- 开始更新索引模板', count=len(template_definitions))
    try:
        results['templates'] = manager.ensure_index_templates(template_definitions) if len(template_definitions) > 0 else []
    except Exception as ex:
        logger.fail('索引模板更新失败', error=str(ex), useTime='{0:.2f}s'.format(time.time() - start_time))
        logger.separator(long=True)
        raise
    for _tpl in results['templates']:
        logger.info('|--- 索引模板处理', template=_tpl.get('template'), action=_tpl.get('action'))
    logger.detail_ok('索引模板更新完成', count=len(results['templates']))

    logger.info('|- 开始确保数据流', count=len(target_data_streams))
    try:
        results['data_streams'] = manager.ensure_data_streams(target_data_streams)
    except Exception as ex:
        logger.fail('数据流初始化失败', error=str(ex), useTime='{0:.2f}s'.format(time.time() - start_time))
        logger.separator(long=True)
        raise
    for _ds in results['data_streams']:
        logger.info('|--- 数据流处理', data_stream=_ds.get('data_stream'), action=_ds.get('action'))
    logger.detail_ok('数据流确保完成', count=len(results['data_streams']))

    results['index_summaries'] = [fetch_index_summary(manager, index_name) for index_name in target_indices]
    results['data_stream_summaries'] = [fetch_data_stream_summary(manager, data_stream_name) for data_stream_name in target_data_streams]

    logger.done('ES索引初始化完成',
             indices=len(results['indices']),
             templates=len(results['templates']),
             data_streams=len(results['data_streams']),
             useTime='{0:.2f}s'.format(time.time() - start_time))
    logger.separator(long=True)
    _tmp = tempfile.NamedTemporaryFile(
        prefix='es-init-result-', suffix='.json',
        delete=False, mode='w', encoding='utf-8',
        dir='/tmp',
    )
    try:
        _tmp.write(json.dumps(results, ensure_ascii=False, indent=2))
        _tmp.close()
        logger.info('完整结果已写入', file=_tmp.name)
    except Exception:
        _tmp.close()
        raise
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
