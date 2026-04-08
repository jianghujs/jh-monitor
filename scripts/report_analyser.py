# coding: utf-8

import datetime
import os
import sys
import time

from jinja2 import Environment, FileSystemLoader

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
CORE_DIR = os.path.join(ROOT_DIR, 'class', 'core')
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
ES_MODEL_DIR = os.path.join(ROOT_DIR, 'class', 'es', 'model')

if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if CORE_DIR not in sys.path:
    sys.path.insert(0, CORE_DIR)
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)
if ES_MODEL_DIR not in sys.path:
    sys.path.insert(0, ES_MODEL_DIR)

import jh
import value_tool
from config_api import config_api
from host_api import host_api
from report_state import build_delivery_state, build_validation_state

h_api = host_api()
c_api = config_api()

REPORT_CONFIG_PATH = os.path.join(ROOT_DIR, 'data', 'report_config.json')
OVERVIEW_TEMPLATE_DIR = os.path.join(ROOT_DIR, 'route', 'templates', 'report')

DEFAULT_REPORT_THRESHOLDS = {
    'cpu': 80,
    'memory': 80,
    'disk': 80,
    'ssl_cert': 14,
}

RAW_STATUS_INDEX = 'host-system-status'
RAW_XTRABACKUP_INDEX = 'host-xtrabackup'
RAW_XTRABACKUP_INC_INDEX = 'host-xtrabackup-inc'
RAW_BACKUP_INDEX = 'host-backup'
SINGLE_REPORT_INDEX = 'host-report-single'
OVERVIEW_REPORT_INDEX = 'host-report-overview'

ANALYSIS_STALE_SECONDS = 15 * 60
PAGE_SIZE = 500


class HostReportAnalyser(object):
    def __init__(self, now_ts=None, logger=None, es_client=None):
        """初始化流水线运行上下文与可注入依赖。"""
        self.now_ts = int(now_ts or time.time())
        self.logger = logger
        self._es = es_client or jh.getES()
        self._last_schedule_debug_rows = []
        self._overview_env = Environment(
            loader=FileSystemLoader(OVERVIEW_TEMPLATE_DIR),
            autoescape=False
        )
        self.thresholds = self.load_thresholds()

    def log(self, message):
        if self.logger:
            try:
                self.logger(message)
                return
            except Exception:
                pass
        print(message)

    def load_thresholds(self):
        """读取报告阈值配置，并补齐默认值。"""
        data = jh.readJsonFile(REPORT_CONFIG_PATH, DEFAULT_REPORT_THRESHOLDS, auto_create=True)
        if not isinstance(data, dict):
            data = dict(DEFAULT_REPORT_THRESHOLDS)
        thresholds = dict(DEFAULT_REPORT_THRESHOLDS)
        for key in thresholds.keys():
            try:
                thresholds[key] = int(data.get(key, thresholds[key]))
            except Exception:
                thresholds[key] = DEFAULT_REPORT_THRESHOLDS[key]
        return thresholds

    def get_schedule_state(self):
        """计算已启用主机、到期主机以及对应的发送配置。"""
        dispatch_config = c_api.getReportDispatchConfigData() or {}
        report_enabled = bool(dispatch_config.get('enabled'))
        report_cron = dispatch_config.get('cron', c_api.getDefaultReportCronData())
        report_host_ids = dispatch_config.get('report_host_ids', []) or []
        report_config = {}
        for host_id in report_host_ids:
            report_config[host_id] = {
                'enabled': report_enabled,
                'cron': dict(report_cron)
            }
        self._last_schedule_debug_rows = []
        enabled_host_ids = []
        for host_id, cfg in report_config.items():
            if isinstance(cfg, dict) and cfg.get('enabled'):
                enabled_host_ids.append(host_id)

        if len(enabled_host_ids) == 0:
            return report_config, [], []

        host_rows = jh.M('view01_host').field(h_api.host_field).select()
        if isinstance(host_rows, str) or host_rows is None:
            host_rows = []

        enabled_rows = []
        for row in host_rows:
            host_id = row.get('host_id')
            if host_id in enabled_host_ids:
                enabled_rows.append(row)

        due_rows = []
        for row in enabled_rows:
            host_id = row.get('host_id')
            cfg = report_config.get(host_id, {})
            cron = dict(report_cron)
            host_due = jh.cronShouldRun(cron, 0, self.now_ts)
            self._last_schedule_debug_rows.append({
                'host_id': host_id,
                'host_name': row.get('host_name', ''),
                'is_due': host_due,
                'cron': cron,
                'reason': 'due' if host_due else 'cron_not_due'
            })
            if host_due:
                due_rows.append(row)
        return report_config, enabled_rows, due_rows

    def get_schedule_debug_rows(self):
        """返回最近一次排期计算的调试信息。"""
        return list(self._last_schedule_debug_rows)

    def get_report_window(self, report_date=None):
        """生成报告时间窗口，默认取上一自然日。"""
        now_dt = datetime.datetime.fromtimestamp(self.now_ts)
        if report_date:
            if isinstance(report_date, datetime.date):
                target_date = report_date
            else:
                target_date = datetime.datetime.strptime(str(report_date), '%Y-%m-%d').date()
        else:
            target_date = (now_dt - datetime.timedelta(days=1)).date()

        start_dt = datetime.datetime.combine(target_date, datetime.time(0, 0, 0))
        end_dt = datetime.datetime.combine(target_date, datetime.time(23, 59, 59))
        return {
            'report_date': target_date.strftime('%Y-%m-%d'),
            'report_time': now_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'start_date': target_date.strftime('%Y-%m-%d'),
            'end_date': target_date.strftime('%Y-%m-%d'),
            'start_time': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'start_timestamp': int(start_dt.timestamp()),
            'end_timestamp': int(end_dt.timestamp()),
        }

    def _get_doc(self, index_name, doc_id):
        """兼容旧脚本：统一读取并返回 ES 文档的 _source。"""
        document = self._es.get(index_name, doc_id)
        if isinstance(document, dict):
            return document.get('_source', document)
        return document

    def _update_doc(self, index_name, doc_id, document):
        """兼容旧脚本：统一回写 ES 文档。"""
        self._es.index(index_name, doc_id, document=document, refresh='wait_for')
        return True

    def _analyze_series(self, docs, extractor, threshold):
        """统计监控序列的平均值、当前值和超阈次数。"""
        values = []
        for doc in sorted(docs, key=lambda item: value_tool.safeInt(item.get('add_timestamp', 0), value_tool.parseTime(item.get('add_time', '')))):
            timestamp = value_tool.safeInt(doc.get('add_timestamp', 0), value_tool.parseTime(doc.get('add_time', '')))
            metric_value = value_tool.safeFloat(extractor(doc), 0.0)
            values.append({'value': metric_value, 'timestamp': timestamp})

        if len(values) == 0:
            return {'average': 0.0, 'over_count': 0, 'current': 0.0}

        last_alarm_ts = None
        over_count = 0
        total = 0.0
        for item in values:
            total += item['value']
            if threshold != -1 and item['value'] > threshold:
                if last_alarm_ts is None or (item['timestamp'] - last_alarm_ts) >= 300:
                    over_count += 1
                    last_alarm_ts = item['timestamp']

        return {
            'average': round(total / float(len(values)), 2),
            'over_count': over_count,
            'current': round(values[-1]['value'], 2)
        }

    def _build_percent_span(self, value, threshold, suffix='%'):
        """根据阈值生成带颜色的百分比 HTML。"""
        color = 'auto'
        if threshold != -1 and value > threshold:
            color = 'red'
        elif threshold != -1 and value > (threshold * 0.8):
            color = 'orange'
        if isinstance(value, float):
            value_text = '{0:.2f}'.format(value).rstrip('0').rstrip('.')
        else:
            value_text = str(value)
        return "<span style='color: {0}'>{1}{2}</span>".format(color, value_text, suffix)

    def _build_status_window_query(self, host_ids, window):
        """构造系统状态索引的窗口查询条件。"""
        return {
            'bool': {
                'filter': [
                    {
                        'bool': {
                            'should': [
                                {'terms': {'host.host_id.keyword': host_ids}},
                                {'terms': {'host.host_id': host_ids}},
                                {'terms': {'host_id.keyword': host_ids}},
                                {'terms': {'host_id': host_ids}},
                            ],
                            'minimum_should_match': 1
                        }
                    },
                    {'range': {'add_timestamp': {'gte': window['start_timestamp'], 'lte': window['end_timestamp']}}}
                ]
            }
        }

    def _build_simple_window_query(self, host_ids, window):
        """构造按 host_id + 时间窗口过滤的通用查询。"""
        return {
            'bool': {
                'filter': [
                    {
                        'bool': {
                            'should': [
                                {'terms': {'host_id.keyword': host_ids}},
                                {'terms': {'host_id': host_ids}},
                                {'terms': {'host.host_id.keyword': host_ids}},
                                {'terms': {'host.host_id': host_ids}},
                            ],
                            'minimum_should_match': 1
                        }
                    },
                    {'range': {'add_timestamp': {'gte': window['start_timestamp'], 'lte': window['end_timestamp']}}}
                ]
            }
        }

    def _build_host_only_query(self, host_ids, field_name='host_id'):
        """构造只按主机过滤的查询条件。"""
        keyword_field_name = '{0}.keyword'.format(field_name)
        return {
            'bool': {
                'filter': [
                    {
                        'bool': {
                            'should': [
                                {'terms': {keyword_field_name: host_ids}},
                                {'terms': {field_name: host_ids}}
                            ],
                            'minimum_should_match': 1
                        }
                    }
                ]
            }
        }

    def _is_doc_in_window(self, doc, window):
        """判断文档时间是否落在报告窗口内。"""
        timestamp = value_tool.safeInt(doc.get('add_timestamp', 0))
        if timestamp <= 0:
            timestamp = value_tool.parseTime(doc.get('add_time', ''))
        if timestamp <= 0:
            return False
        return window['start_timestamp'] <= timestamp <= window['end_timestamp']

    def load_raw_groups(self, host_rows, window):
        """加载并按 host_id 聚合原始监控与备份数据。"""
        host_ids = [row.get('host_id') for row in host_rows if row.get('host_id')]
        if len(host_ids) == 0:
            return {}

        status_docs = self._es.searchAll(
            index=RAW_STATUS_INDEX,
            body={'query': self._build_status_window_query(host_ids, window)},
            page_size=PAGE_SIZE,
            scroll='1m'
        )
        xtrabackup_docs = self._es.searchAll(
            index=RAW_XTRABACKUP_INDEX,
            body={'query': self._build_simple_window_query(host_ids, window)},
            page_size=PAGE_SIZE,
            scroll='1m'
        )
        xtrabackup_inc_docs = self._es.searchAll(
            index=RAW_XTRABACKUP_INC_INDEX,
            body={'query': self._build_simple_window_query(host_ids, window)},
            page_size=PAGE_SIZE,
            scroll='1m'
        )
        backup_docs = self._es.searchAll(
            index=RAW_BACKUP_INDEX,
            body={'query': self._build_host_only_query(host_ids)},
            page_size=PAGE_SIZE,
            scroll='1m'
        )
        backup_docs = [doc for doc in backup_docs if self._is_doc_in_window(doc, window)]

        grouped = {}
        for row in host_rows:
            host_id = row.get('host_id')
            grouped[host_id] = {
                'status': [],
                'xtrabackup': [],
                'xtrabackup_inc': [],
                'backup': []
            }

        for doc in status_docs:
            host_id = value_tool.getNested(doc, ['host', 'host_id'], '')
            if host_id in grouped:
                grouped[host_id]['status'].append(doc)

        for doc in xtrabackup_docs:
            host_id = doc.get('host_id', '')
            if host_id in grouped:
                grouped[host_id]['xtrabackup'].append(doc)

        for doc in xtrabackup_inc_docs:
            host_id = doc.get('host_id', '')
            if host_id in grouped:
                grouped[host_id]['xtrabackup_inc'].append(doc)

        for doc in backup_docs:
            host_id = doc.get('host_id', '')
            if host_id in grouped:
                grouped[host_id]['backup'].append(doc)

        return grouped

    def _summarize_backup_rows(self, rows):
        """从备份原始记录中提炼最新时间与统计信息。"""
        if len(rows) == 0:
            return {
                'last_backup_time': None,
                'last_backup_timestamp': 0,
                'count_in_timeframe': 0,
                'last_backup_size': '无',
                'last_backup_size_bytes': 0
            }

        rows = sorted(rows, key=lambda item: value_tool.safeInt(item.get('add_timestamp', 0), value_tool.parseTime(item.get('add_time', ''))))
        last_row = rows[-1]
        return {
            'last_backup_time': last_row.get('add_time'),
            'last_backup_timestamp': value_tool.safeInt(last_row.get('add_timestamp', 0), value_tool.parseTime(last_row.get('add_time', ''))),
            'count_in_timeframe': len(rows),
            'last_backup_size': last_row.get('size', '无'),
            'last_backup_size_bytes': value_tool.safeInt(last_row.get('size_bytes', 0)),
        }

    def _merge_backup_summary(self, runtime_summary, raw_summary):
        """合并运行时备份摘要与 ES 原始备份摘要。"""
        runtime_summary = runtime_summary or {}
        merged = dict(runtime_summary)
        if not merged.get('last_backup_time') and raw_summary.get('last_backup_time'):
            merged['last_backup_time'] = raw_summary.get('last_backup_time')
        if value_tool.safeInt(merged.get('last_backup_timestamp', 0)) <= 0:
            merged['last_backup_timestamp'] = raw_summary.get('last_backup_timestamp', 0)
        if value_tool.safeInt(merged.get('count_in_timeframe', 0)) <= 0:
            merged['count_in_timeframe'] = raw_summary.get('count_in_timeframe', 0)
        if not merged.get('last_backup_size'):
            merged['last_backup_size'] = raw_summary.get('last_backup_size', '无')
        if value_tool.safeInt(merged.get('last_backup_size_bytes', 0)) <= 0:
            merged['last_backup_size_bytes'] = raw_summary.get('last_backup_size_bytes', 0)
        return merged

    def _build_system_section(self, status_docs, window, validation_errors):
        """生成 CPU、内存、磁盘等系统资源报告段落。"""
        sysinfo_tips = []
        summary_error_keys = []
        error_tips = []
        latest_doc = status_docs[-1] if status_docs else {}
        latest_ts = value_tool.safeInt(latest_doc.get('add_timestamp', 0), value_tool.parseTime(latest_doc.get('add_time', '')))

        cpu_stats = self._analyze_series(status_docs, lambda doc: value_tool.getNested(doc, ['system', 'cpu'], 0), self.thresholds['cpu'])
        mem_stats = self._analyze_series(status_docs, lambda doc: value_tool.getNested(doc, ['system', 'memory'], 0), self.thresholds['memory'])
        load_stats = self._analyze_series(status_docs, lambda doc: value_tool.getNested(doc, ['system', 'load', 'pro'], 0), self.thresholds['cpu'])

        cpu_desc = '平均使用率{0}<br/>当前CPU使用率：{1}'.format(
            self._build_percent_span(cpu_stats['average'], self.thresholds['cpu']),
            self._build_percent_span(cpu_stats['current'], self.thresholds['cpu'])
        )
        if self.thresholds['cpu'] != -1 and cpu_stats['over_count'] > 0:
            cpu_desc += '，<span style="color: red">异常（使用率超过{0}%）{1}次</span>'.format(self.thresholds['cpu'], cpu_stats['over_count'])
        sysinfo_tips.append({'name': 'CPU', 'desc': cpu_desc})
        if self.thresholds['cpu'] != -1 and cpu_stats['average'] > self.thresholds['cpu']:
            summary_error_keys.append('CPU')

        mem_desc = '平均使用率{0}<br/>当前内存使用率：{1}'.format(
            self._build_percent_span(mem_stats['average'], self.thresholds['memory']),
            self._build_percent_span(mem_stats['current'], self.thresholds['memory'])
        )
        if self.thresholds['memory'] != -1 and mem_stats['over_count'] > 0:
            mem_desc += '，<span style="color: red">异常（使用率超过{0}%）{1}次</span>'.format(self.thresholds['memory'], mem_stats['over_count'])
        sysinfo_tips.append({'name': '内存', 'desc': mem_desc})
        if self.thresholds['memory'] != -1 and mem_stats['average'] > self.thresholds['memory']:
            summary_error_keys.append('内存')

        load_desc = '平均使用率{0}'.format(self._build_percent_span(load_stats['average'], self.thresholds['cpu']))
        if self.thresholds['cpu'] != -1 and load_stats['over_count'] > 0:
            load_desc += '，<span style="color: red">异常（使用率超过{0}%）{1}次</span>'.format(self.thresholds['cpu'], load_stats['over_count'])
        sysinfo_tips.append({'name': '资源使用率', 'desc': load_desc})
        if self.thresholds['cpu'] != -1 and load_stats['average'] > self.thresholds['cpu']:
            summary_error_keys.append('资源使用率')

        latest_disks = value_tool.getNested(latest_doc, ['system', 'disks'], []) or []
        for disk in latest_disks:
            size_info = disk.get('size', []) or []
            used_percent_text = ''
            used_text = ''
            total_text = ''
            if len(size_info) >= 4:
                total_text = size_info[0]
                used_text = size_info[1]
                used_percent_text = size_info[3]
            used_percent = value_tool.safeInt(str(used_percent_text).replace('%', ''), 0)
            sysinfo_tips.append({
                'name': '磁盘（{0}）'.format(disk.get('path', '未知路径')),
                'desc': '已使用{0}（{1}/{2}）'.format(
                    self._build_percent_span(used_percent, self.thresholds['disk']),
                    used_text or '0B',
                    total_text or '0B'
                )
            })
            if self.thresholds['disk'] != -1 and used_percent > self.thresholds['disk']:
                disk_name = '磁盘（{0}）'.format(disk.get('path', '未知路径'))
                summary_error_keys.append(disk_name)
                error_tips.append(disk_name + '使用率过高')

        last_monitor_text = latest_doc.get('add_time', '')
        last_monitor_desc = value_tool.escapeHtml(last_monitor_text or '无数据')
        if latest_ts and latest_ts < (window['end_timestamp'] - ANALYSIS_STALE_SECONDS):
            validation_errors.append('stale_system_status')
            last_monitor_desc = "<span style='color: red'>{0}</span>".format(last_monitor_desc)
        else:
            last_monitor_desc = "<span style='color: auto'>{0}</span>".format(last_monitor_desc)
        sysinfo_tips.append({'name': '最后监控时间', 'desc': last_monitor_desc})

        summary_tips = []
        if len(summary_error_keys) > 0:
            summary_text = '、'.join(summary_error_keys) + '平均使用率过高，有服务中断停机风险'
            summary_tips.append("<span style='color: red;'>{0}</span>".format(summary_text))
            error_tips.append(summary_text)
        if latest_ts and latest_ts < (window['end_timestamp'] - ANALYSIS_STALE_SECONDS):
            summary_tips.append("<span style='color: red;'>系统异常监控状态异常，异常情况通知可能不及时</span>")
            error_tips.append('系统监控状态异常')

        return {
            'tips': sysinfo_tips,
            'summary_tips': summary_tips,
            'error_tips': error_tips,
            'latest_doc': latest_doc,
            'latest_timestamp': latest_ts,
            'cpu_stats': cpu_stats,
            'mem_stats': mem_stats,
            'load_stats': load_stats,
        }

    def _build_backup_section(self, latest_doc, xtrabackup_docs, xtrabackup_inc_docs, backup_docs, window, validation_errors):
        """生成备份状态段落，并校验备份证据是否完整。"""
        backup_tips = []
        summary_names = []
        error_tips = []
        runtime_backup = latest_doc.get('backup', {}) if isinstance(latest_doc, dict) else {}

        xtrabackup_runtime = runtime_backup.get('xtrabackup', {}) if isinstance(runtime_backup, dict) else {}
        xtrabackup_summary = self._merge_backup_summary(xtrabackup_runtime, self._summarize_backup_rows(xtrabackup_docs))
        xtrabackup_enabled = bool(xtrabackup_runtime.get('enabled')) or len(xtrabackup_docs) > 0
        if xtrabackup_enabled:
            last_time = xtrabackup_summary.get('last_backup_time') or '无'
            count_in_window = value_tool.safeInt(xtrabackup_summary.get('count_in_timeframe', 0))
            desc = '最后成功时间：{0}<br/>窗口内备份次数：{1}'.format(last_time, count_in_window)
            backup_tips.append({'name': 'Xtrabackup', 'desc': desc})
            last_ts = value_tool.safeInt(xtrabackup_summary.get('last_backup_timestamp', 0), value_tool.parseTime(last_time))
            if count_in_window <= 0 or last_ts < window['start_timestamp']:
                summary_names.append('Xtrabackup')
                validation_errors.append('missing_xtrabackup_evidence')

        inc_full_docs = []
        inc_inc_docs = []
        for doc in xtrabackup_inc_docs:
            backup_type = str(doc.get('backup_type', '')).lower()
            if backup_type == 'full':
                inc_full_docs.append(doc)
            else:
                inc_inc_docs.append(doc)
        xtrabackup_inc_runtime = runtime_backup.get('xtrabackup_inc', {}) if isinstance(runtime_backup, dict) else {}
        inc_full_runtime = xtrabackup_inc_runtime.get('full', {}) if isinstance(xtrabackup_inc_runtime, dict) else {}
        inc_inc_runtime = xtrabackup_inc_runtime.get('inc', {}) if isinstance(xtrabackup_inc_runtime, dict) else {}
        inc_full_summary = self._merge_backup_summary(inc_full_runtime, self._summarize_backup_rows(inc_full_docs))
        inc_inc_summary = self._merge_backup_summary(inc_inc_runtime, self._summarize_backup_rows(inc_inc_docs))
        xtrabackup_inc_enabled = bool(xtrabackup_inc_runtime.get('enabled')) or len(xtrabackup_inc_docs) > 0
        if xtrabackup_inc_enabled:
            full_time = inc_full_summary.get('last_backup_time') or '无'
            inc_time = inc_inc_summary.get('last_backup_time') or '无'
            desc = '全量：{0}<br/>增量：{1}<br/>窗口内全量/增量次数：{2}/{3}'.format(
                full_time,
                inc_time,
                value_tool.safeInt(inc_full_summary.get('count_in_timeframe', 0)),
                value_tool.safeInt(inc_inc_summary.get('count_in_timeframe', 0))
            )
            backup_tips.append({'name': 'Xtrabackup增量', 'desc': desc})
            full_ok = value_tool.safeInt(inc_full_summary.get('count_in_timeframe', 0)) > 0 and value_tool.safeInt(inc_full_summary.get('last_backup_timestamp', 0), value_tool.parseTime(full_time)) >= window['start_timestamp']
            inc_ok = value_tool.safeInt(inc_inc_summary.get('count_in_timeframe', 0)) > 0 and value_tool.safeInt(inc_inc_summary.get('last_backup_timestamp', 0), value_tool.parseTime(inc_time)) >= window['start_timestamp']
            if not (full_ok and inc_ok):
                summary_names.append('Xtrabackup增量')
                validation_errors.append('missing_xtrabackup_inc_evidence')

        mysql_dump_runtime = runtime_backup.get('mysql_dump', {}) if isinstance(runtime_backup, dict) else {}
        mysql_dump_enabled = bool(mysql_dump_runtime.get('enabled'))
        if mysql_dump_enabled:
            last_dump_time = mysql_dump_runtime.get('last_backup_time') or '无'
            dump_count = value_tool.safeInt(mysql_dump_runtime.get('count_in_timeframe', 0))
            abnormal_dump_files = value_tool.safeInt(mysql_dump_runtime.get('abnormal_files_in_timeframe', 0))
            desc = '最后成功时间：{0}<br/>窗口内备份次数：{1}'.format(last_dump_time, dump_count)
            if abnormal_dump_files > 0:
                desc += '<br/><span style="color: orange">异常备份文件：{0}个</span>'.format(abnormal_dump_files)
            backup_tips.append({'name': 'MySQL Dump', 'desc': desc})
            if dump_count <= 0:
                summary_names.append('MySQL Dump')
                validation_errors.append('missing_mysql_dump_evidence')

        if len(backup_docs) > 0:
            latest_backup_event = sorted(backup_docs, key=lambda item: value_tool.parseTime(item.get('add_time', '')))[-1]
            event_message = latest_backup_event.get('message', '') or latest_backup_event.get('filename', '') or latest_backup_event.get('path', '') or '存在备份事件记录'
            backup_tips.append({
                'name': '备份事件',
                'desc': '窗口内事件数：{0}<br/>{1}'.format(len(backup_docs), value_tool.escapeHtml(event_message))
            })

        summary_tips = []
        if len(summary_names) > 0:
            summary_text = '、'.join(summary_names) + '备份状态异常'
            summary_tips.append("<span style='color: red;'>{0}</span>".format(summary_text))
            error_tips.append(summary_text)

        return {
            'tips': backup_tips,
            'summary_tips': summary_tips,
            'error_tips': error_tips,
            'runtime_backup': runtime_backup,
        }

    def _build_site_section(self, latest_doc):
        """生成站点运行状态与证书有效期段落。"""
        site_tips = []
        summary_tips = []
        error_tips = []
        site_warning_names = []
        site_rows = latest_doc.get('site', []) if isinstance(latest_doc, dict) else []
        for site in site_rows:
            site_name = site.get('name', '') or '未命名站点'
            site_status = '<span>运行中</span>' if str(site.get('status', '')) == '1' else '<span style="color: orange">已停止</span>'
            cert_data = site.get('ssl_data') or {}
            ssl_type = site.get('ssl_type') or ''
            cert_status = '未配置'
            if cert_data:
                cert_not_after = cert_data.get('notAfter', '0000-00-00')
                cert_endtime = value_tool.safeInt(cert_data.get('endtime', 0))
                if cert_endtime < 0:
                    cert_status = '{0}到期，已过期<span style="color: red">{1}</span>天'.format(cert_not_after, abs(cert_endtime))
                else:
                    color = 'auto'
                    if cert_endtime < 3:
                        color = 'red'
                    elif cert_endtime < self.thresholds['ssl_cert']:
                        color = 'orange'
                    cert_status = '将于{0}到期，还有<span style="color: {1}">{2}</span>天{3}'.format(
                        cert_not_after,
                        color,
                        cert_endtime,
                        '，到期后将自动续签' if ssl_type in ('lets', 'acme') else ''
                    )
                    if ssl_type not in ('lets', 'acme') and cert_endtime < self.thresholds['ssl_cert']:
                        site_warning_names.append(site_name)
            site_tips.append({'name': site_name, 'desc': '{0}（SSL证书{1}）'.format(site_status, cert_status)})
        if len(site_warning_names) > 0:
            summary_text = '、'.join(site_warning_names) + '域名证书需要及时更新'
            summary_tips.append("<span style='color: red;'>{0}</span>".format(summary_text))
            error_tips.append(summary_text)
        return {
            'tips': site_tips,
            'summary_tips': summary_tips,
            'error_tips': error_tips,
        }

    def _build_runtime_service_section(self, latest_doc, key_name, section_title, stop_color):
        """生成 JianghuJS、Docker 等运行服务状态段落。"""
        tips = []
        rows = latest_doc.get(key_name, []) if isinstance(latest_doc, dict) else []
        for item in rows:
            status_text = '<span>已启动</span>' if str(item.get('status', '')) == 'start' else '<span style="color: {0}">已停止</span>'.format(stop_color)
            tips.append({'name': item.get('name', '') or section_title, 'desc': status_text})
        return tips

    def _build_mysql_section(self, status_docs):
        """生成数据库容量变化与 Top 表信息段落。"""
        mysqlinfo_tips = []
        if len(status_docs) == 0:
            return mysqlinfo_tips
        first_doc = status_docs[0]
        latest_doc = status_docs[-1]
        first_mysql = first_doc.get('mysql', {}) if isinstance(first_doc, dict) else {}
        latest_mysql = latest_doc.get('mysql', {}) if isinstance(latest_doc, dict) else {}

        total_size = latest_mysql.get('total_size', '0B')
        total_size_bytes = value_tool.safeInt(latest_mysql.get('total_size_bytes', 0))
        first_total_size_bytes = value_tool.safeInt(first_mysql.get('total_size_bytes', 0))
        total_change = total_size_bytes - first_total_size_bytes
        total_change_text = jh.toSize(abs(total_change))
        if total_change > 0:
            total_change_text = '+{0}'.format(total_change_text)
        elif total_change == 0:
            total_change_text = '0B'
        mysqlinfo_tips.append({
            'name': '数据库总大小',
            'desc': '变化：{0}<br/>总大小：{1}'.format(total_change_text, total_size)
        })

        first_table_map = {}
        for item in first_mysql.get('tables', []) or []:
            first_table_map[item.get('table_name', '')] = value_tool.safeInt(item.get('size_bytes', 0))

        latest_tables = latest_mysql.get('tables', []) or []
        latest_tables = sorted(latest_tables, key=lambda item: value_tool.safeInt(item.get('size_bytes', 0)), reverse=True)
        for item in latest_tables[:20]:
            table_name = item.get('table_name', '')
            size_bytes = value_tool.safeInt(item.get('size_bytes', 0))
            change_bytes = size_bytes - value_tool.safeInt(first_table_map.get(table_name, 0))
            change_text = jh.toSize(abs(change_bytes))
            if change_bytes > 0:
                change_text = '+{0}'.format(change_text)
            elif change_bytes == 0:
                change_text = '0B'
            mysqlinfo_tips.append({
                'name': table_name,
                'desc': '变化：{0}<br/>总大小：{1}'.format(change_text, item.get('size', jh.toSize(size_bytes)))
            })
        return mysqlinfo_tips

    def build_single_host_report(self, host_row, host_group, window):
        """基于单台主机原始数据生成单机报告文档。"""
        host_id = host_row.get('host_id', '')
        host_name = host_row.get('host_name', '')
        host_ip = host_row.get('ip', '')
        status_docs = sorted(host_group.get('status', []) or [], key=lambda item: value_tool.safeInt(item.get('add_timestamp', 0), value_tool.parseTime(item.get('add_time', ''))))
        xtrabackup_docs = host_group.get('xtrabackup', []) or []
        xtrabackup_inc_docs = host_group.get('xtrabackup_inc', []) or []
        backup_docs = host_group.get('backup', []) or []

        validation_errors = []
        if len(status_docs) == 0:
            validation_errors.append('missing_system_status')

        system_section = self._build_system_section(status_docs, window, validation_errors)
        latest_doc = system_section.get('latest_doc', {})
        backup_section = self._build_backup_section(latest_doc, xtrabackup_docs, xtrabackup_inc_docs, backup_docs, window, validation_errors)
        site_section = self._build_site_section(latest_doc)
        jianghujsinfo_tips = self._build_runtime_service_section(latest_doc, 'jianghujs', 'JianghuJS', 'orange')
        dockerinfo_tips = self._build_runtime_service_section(latest_doc, 'docker', 'Docker', 'red')
        mysqlinfo_tips = self._build_mysql_section(status_docs)

        summary_tips = []
        error_tips = []
        summary_tips.extend(system_section.get('summary_tips', []))
        summary_tips.extend(backup_section.get('summary_tips', []))
        summary_tips.extend(site_section.get('summary_tips', []))
        error_tips.extend(system_section.get('error_tips', []))
        error_tips.extend(backup_section.get('error_tips', []))
        error_tips.extend(site_section.get('error_tips', []))

        if len(status_docs) == 0:
            summary_tips.append("<span style='color: red;'>系统监控原始数据缺失，报告未生成完整</span>")
            error_tips.append('系统监控原始数据缺失')

        if len(summary_tips) == 0:
            summary_tips.append("<span style='color: green;'>服务运行正常，继续保持！</span>")

        title = jh.getConfig('title')
        report_payload = {
            'title': title,
            'ip': host_ip,
            'report_time': window['report_time'],
            'start_time': window['start_time'],
            'end_time': window['end_time'],
            'start_date': window['start_date'],
            'end_date': window['end_date'],
            'summary_tips': summary_tips,
            'error_tips': error_tips,
            'sysinfo_tips': system_section.get('tips', []),
            'backup_tips': backup_section.get('tips', []),
            'siteinfo_tips': site_section.get('tips', []),
            'jianghujsinfo_tips': jianghujsinfo_tips,
            'dockerinfo_tips': dockerinfo_tips,
            'mysqlinfo_tips': mysqlinfo_tips,
        }

        html_content = h_api.renderHostReportHtml(host_row, report_payload)
        if not html_content or '暂无报告内容' in html_content:
            validation_errors.append('empty_html_content')

        validation_errors = sorted(list(set(validation_errors)))
        validation = build_validation_state(
            is_complete=len(validation_errors) == 0,
            status='ready' if len(validation_errors) == 0 else 'incomplete',
            errors=validation_errors
        )

        doc_id = '{0}:{1}'.format(window['report_date'], host_id)
        existing_doc = self._es.get(SINGLE_REPORT_INDEX, doc_id)
        if isinstance(existing_doc, dict):
            existing_doc = existing_doc.get('_source', {})
        delivery_state = existing_doc.get('delivery') if isinstance(existing_doc, dict) and existing_doc.get('delivery') else build_delivery_state()

        document = {
            'report_type': 'single',
            'title': '{0}({1})-服务器运行报告'.format(host_name, host_ip),
            'report_date': window['report_date'],
            'report_time': window['report_time'],
            'start_time': window['start_time'],
            'end_time': window['end_time'],
            'start_date': window['start_date'],
            'end_date': window['end_date'],
            'host_id': host_id,
            'host_name': host_name,
            'host_ip': host_ip,
            'summary_tips': summary_tips,
            'error_tips': error_tips,
            'html_content': html_content,
            'sysinfo_tips': system_section.get('tips', []),
            'backup_tips': backup_section.get('tips', []),
            'siteinfo_tips': site_section.get('tips', []),
            'jianghujsinfo_tips': jianghujsinfo_tips,
            'dockerinfo_tips': dockerinfo_tips,
            'mysqlinfo_tips': mysqlinfo_tips,
            'validation': validation,
            'delivery': delivery_state,
            'is_abnormal': len(error_tips) > 0,
            'extra_info': {
                'raw_counts': {
                    'status': len(status_docs),
                    'xtrabackup': len(xtrabackup_docs),
                    'xtrabackup_inc': len(xtrabackup_inc_docs),
                    'backup': len(backup_docs),
                },
                'latest_status_time': latest_doc.get('add_time', '') if isinstance(latest_doc, dict) else '',
            }
        }
        return doc_id, document

    def _build_host_label(self, document):
        """生成用于总览展示的主机标签文本。"""
        host_ip = document.get('host_ip', '')
        host_name = document.get('host_name', '')
        if host_ip and host_name:
            return '{0}（{1}）'.format(host_ip, host_name)
        return host_ip or host_name or '未知主机'

    def _format_host_summary(self, documents):
        """把多台主机摘要压缩成适合邮件展示的短文本。"""
        labels = [self._build_host_label(doc) for doc in documents]
        if len(labels) == 0:
            return '无'
        if len(labels) <= 3:
            return '、'.join(labels)
        return '{0}等 {1} 台'.format('、'.join(labels[:3]), len(labels))

    def build_overview_report(self, host_rows, single_documents, window):
        """汇总所有单机报告，生成全局概览文档。"""
        online_count = 0
        abnormal_documents = []
        normal_documents = []
        offline_documents = []

        doc_map = {}
        for doc in single_documents:
            doc_map[doc.get('host_id')] = doc

        for row in host_rows:
            current_doc = doc_map.get(row.get('host_id'))
            if not current_doc:
                offline_documents.append({
                    'host_id': row.get('host_id'),
                    'host_name': row.get('host_name'),
                    'host_ip': row.get('ip'),
                    'summary_tips': ['缺少单机报告'],
                    'validation': {'errors': ['missing_single_report']},
                    'html_content': ''
                })
                continue
            validation = current_doc.get('validation', {}) or {}
            latest_status_time = value_tool.getNested(current_doc, ['extra_info', 'latest_status_time'], '')
            if latest_status_time:
                online_count += 1
            if current_doc.get('is_abnormal') or not validation.get('is_complete', False):
                abnormal_documents.append(current_doc)
            else:
                normal_documents.append(current_doc)

        host_total = len(host_rows)
        host_offline = max(host_total - online_count, 0)
        host_error = len(abnormal_documents)

        host_overview_tips = [
            {
                'name': '正常主机',
                'desc': self._format_host_summary(normal_documents)
            },
            {
                'name': '异常主机',
                'desc': self._format_host_summary(abnormal_documents) if abnormal_documents else '无'
            }
        ]
        if host_offline > 0:
            host_overview_tips.append({
                'name': '离线主机',
                'desc': self._format_host_summary(offline_documents)
            })

        exception_host_summary_tips = []
        for doc in abnormal_documents + offline_documents:
            summary_text = '；'.join(doc.get('error_tips', []) or [])
            if summary_text == '':
                validation_errors = value_tool.getNested(doc, ['validation', 'errors'], []) or []
                summary_text = '；'.join(validation_errors) if validation_errors else '报告不完整'
            exception_host_summary_tips.append({
                'name': self._build_host_label(doc),
                'desc': summary_text
            })

        single_host_report_list = []
        for doc in single_documents:
            single_host_report_list.append({
                'host_id': doc.get('host_id', ''),
                'host_name': doc.get('host_name', ''),
                'host_ip': doc.get('host_ip', ''),
                'is_error': bool(doc.get('is_abnormal')),
                'summary_tips': doc.get('summary_tips', []),
                'html_content': doc.get('html_content', ''),
            })

        title = '{0}-全部主机概览报告'.format(jh.getConfig('title'))
        overview_payload = {
            'title': title,
            'report_time': window['report_time'],
            'start_time': window['start_time'],
            'end_time': window['end_time'],
            'report_date': window['report_date'],
            'host_overview_info': {
                'host_total': host_total,
                'host_online': online_count,
                'host_offline': host_offline,
                'host_error': host_error,
            },
            'host_overview_tips': host_overview_tips,
            'exception_host_summary_tips': exception_host_summary_tips,
            'single_host_report_list': single_host_report_list,
        }

        template = self._overview_env.get_template('host_overview_report.html')
        html_content = template.render(**overview_payload)

        validation_errors = []
        if host_total == 0:
            validation_errors.append('missing_enabled_hosts')
        if len(single_documents) == 0:
            validation_errors.append('missing_single_reports')
        if not html_content:
            validation_errors.append('empty_html_content')

        validation = build_validation_state(
            is_complete=len(validation_errors) == 0,
            status='ready' if len(validation_errors) == 0 else 'incomplete',
            errors=validation_errors
        )

        doc_id = window['report_date']
        existing_doc = self._es.get(OVERVIEW_REPORT_INDEX, doc_id)
        if isinstance(existing_doc, dict):
            existing_doc = existing_doc.get('_source', {})
        delivery_state = existing_doc.get('delivery') if isinstance(existing_doc, dict) and existing_doc.get('delivery') else build_delivery_state()

        document = {
            'report_type': 'overview',
            'title': title,
            'report_date': window['report_date'],
            'report_time': window['report_time'],
            'start_time': window['start_time'],
            'end_time': window['end_time'],
            'html_content': html_content,
            'host_overview_info': overview_payload['host_overview_info'],
            'host_overview_tips': host_overview_tips,
            'exception_host_summary_tips': exception_host_summary_tips,
            'single_host_report_list': single_host_report_list,
            'validation': validation,
            'delivery': delivery_state,
            'extra_info': {
                'normal_host_count': len(normal_documents),
                'offline_host_count': host_offline,
                'error_host_ids': [doc.get('host_id') for doc in abnormal_documents],
            }
        }
        return doc_id, document

    def run_analysis(self, host_rows=None, report_date=None):
        """执行分析阶段：生成并落库单机与总览报告。"""
        window = self.get_report_window(report_date)
        if host_rows is None:
            _, host_rows, _ = self.get_schedule_state()
        if len(host_rows) == 0:
            self.log('[report-analysis] skipped no enabled hosts for report_date={0}'.format(window['report_date']))
            return {'status': 'skipped', 'reason': 'no_enabled_hosts', 'report_date': window['report_date']}

        self.log('[report-analysis] start report_date={0} host_total={1}'.format(window['report_date'], len(host_rows)))
        raw_groups = self.load_raw_groups(host_rows, window)
        single_documents = []
        for row in host_rows:
            host_id = row.get('host_id')
            host_group = raw_groups.get(host_id, {'status': [], 'xtrabackup': [], 'xtrabackup_inc': [], 'backup': []})
            doc_id, document = self.build_single_host_report(row, host_group, window)
            self._es.index(SINGLE_REPORT_INDEX, doc_id, document=document, refresh='wait_for')
            single_documents.append(document)
            self.log(
                '[report-analysis] single report saved doc_id={0} host_id={1} validation={2} abnormal={3} raw_counts={4}'.format(
                    doc_id,
                    host_id,
                    value_tool.getNested(document, ['validation', 'status'], ''),
                    bool(document.get('is_abnormal')),
                    value_tool.getNested(document, ['extra_info', 'raw_counts'], {})
                )
            )

        overview_doc_id, overview_document = self.build_overview_report(host_rows, single_documents, window)
        self._es.index(OVERVIEW_REPORT_INDEX, overview_doc_id, document=overview_document, refresh='wait_for')

        ready_count = len([doc for doc in single_documents if value_tool.getNested(doc, ['validation', 'is_complete'], False)])
        abnormal_count = len([doc for doc in single_documents if doc.get('is_abnormal')])
        self.log(
            '[report-analysis] overview saved doc_id={0} validation={1} host_total={2} ready={3} abnormal={4}'.format(
                overview_doc_id,
                value_tool.getNested(overview_document, ['validation', 'status'], ''),
                len(host_rows),
                ready_count,
                abnormal_count
            )
        )
        return {
            'status': 'ok',
            'report_date': window['report_date'],
            'single_total': len(single_documents),
            'single_ready': ready_count,
            'single_abnormal': abnormal_count,
            'overview_ready': bool(value_tool.getNested(overview_document, ['validation', 'is_complete'], False)),
        }



__all__ = [
    'HostReportAnalyser',
    'HostReportAnalysePipeline',
    'build_validation_state',
    'build_delivery_state',
    'DEFAULT_REPORT_THRESHOLDS',
    'RAW_STATUS_INDEX',
    'RAW_XTRABACKUP_INDEX',
    'RAW_XTRABACKUP_INC_INDEX',
    'RAW_BACKUP_INDEX',
    'SINGLE_REPORT_INDEX',
    'OVERVIEW_REPORT_INDEX',
    'ANALYSIS_STALE_SECONDS',
    'PAGE_SIZE',
]


HostReportAnalysePipeline = HostReportAnalyser
