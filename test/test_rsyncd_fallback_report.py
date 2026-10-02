#!/usr/bin/env python3
# coding: utf-8
"""Offline rsyncd log/collector/report checks; never runs a real sync or notification."""
import ast
import importlib.util
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import time
import types
import unittest
import warnings
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PANEL = Path(os.environ.get('JH_PANEL_TEST_ROOT', '/www/server/jh-panel'))
for path in ('class/core', 'class/plugin', 'class/es/model', 'scripts', 'scripts/client'):
    sys.path.insert(0, str(ROOT / path))
os.chdir(ROOT)
import report_analyser
import report_collector
from report_analyser import HostReportAnalyser
from report_sender import HostReportSender


def load_check():
    spec = importlib.util.spec_from_file_location('rsyncd_check_under_test', PANEL / 'plugins/rsyncd/tool_check.py')
    module = importlib.util.module_from_spec(spec)
    fake_mw = types.SimpleNamespace(
        toTime=lambda ts: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)),
        readFile=lambda path: Path(path).read_text())
    with patch.dict(sys.modules, {'mw': fake_mw}):
        spec.loader.exec_module(module)
    return module


SUCCESS = 'sending incremental file list\nsent 100 bytes  received 20 bytes\ntotal size is 200 speedup is 2\n'
ABORT = 'abort: delete ratio exceeds threshold, real rsync skipped\n'
END = 'JH_RSYNC_RUN_END exit_code=0\n'
CHECK = load_check()


class PluginChecks(unittest.TestCase):
    def test_results(self):
        for content, status in [(SUCCESS, 'success'), (SUCCESS + END, 'success'),
                                (ABORT, 'failed'), ('Permission denied', 'failed'),
                                ('rsync preflight failed for task example, exit_code=1', 'failed'),
                                ('rsync preflight parse failed for task example', 'failed'),
                                ('Connection refused', 'failed'), ('', 'unknown'),
                                ('sending incremental file list', 'unknown'),
                                ('sending incremental file list\n' + END, 'failed'),
                                (SUCCESS + 'JH_RSYNC_RUN_END exit_code=12\n', 'failed')]:
            with self.subTest(content=content):
                self.assertEqual(CHECK._fallback_run_status(content)[0], status)
        for code in (23, 24):
            self.assertEqual(CHECK._fallback_run_status(SUCCESS + 'rsync warning ignored: exit %s\n' % code + END)[0], 'success')
        self.assertEqual(CHECK._fallback_run_status('JH_RSYNC_RUN_START pid=%s\n' % os.getpid())[0], 'running')
        with patch.object(CHECK.os, 'kill', side_effect=ProcessLookupError):
            self.assertEqual(CHECK._fallback_run_status('JH_RSYNC_RUN_START pid=123\n')[0], 'failed')

    def test_scan_and_config(self):
        now = int(time.time())
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory) / 'send/example/logs'
            logs.mkdir(parents=True)
            for age, content in [(200, ABORT), (100, SUCCESS), (90000, SUCCESS)]:
                name = time.strftime('run_%Y%m%d_%H%M%S.log', time.localtime(now - age))
                path = logs / name
                path.write_text(content)
                os.utime(path, (now - age, now - age))
            (logs / 'preflight_ignored.log').write_text(ABORT)
            config = Path(directory) / 'config.json'
            config.write_text(json.dumps({'send': {'list': [
                {'name': 'example', 'realtime': 'true'},
                {'name': 'disabled', 'realtime': 'true', 'status': 'disabled'}]}}))
            with patch.multiple(CHECK, RSYNCD_SERVER_DIR=directory, RSYNCD_CONFIG_FILE=str(config),
                                LSYNCD_STATUS_FILE=str(Path(directory) / 'absent')):
                result = CHECK.getRsyncdInfo()
                self.assertEqual(len(result['fallback_runs']), 2)
                self.assertTrue(result['fallback_scan_complete'])
                self.assertEqual(result['fixtime_abnormal_tasks'], [])
                self.assertTrue(result['send_open_realtime_list'][0]['log_format_ok'])
                runs, errors = CHECK._scan_fallback_task({'name': 'missing'}, now - 86400, now)
                self.assertEqual((runs, errors), ([], []))
                with patch('builtins.open', side_effect=PermissionError):
                    runs, errors = CHECK._scan_fallback_task({'name': 'example'}, now - 86400, now)
                    self.assertTrue(errors)
                    self.assertTrue(all(run['status'] == 'unknown' for run in runs))
                # 长任务开始于窗口前，但文件仍在更新，应保留当前状态。
                old_path = logs / time.strftime('run_%Y%m%d_%H%M%S.log', time.localtime(now - 90000))
                os.utime(old_path, (now, now))
                runs, errors = CHECK._scan_fallback_task({'name': 'example'}, now - 86400, now)
                self.assertEqual(len(runs), 3)
                # 普通定时任务仍使用既有检查规则。
                scheduled = {'name': 'example', 'realtime': 'false'}
                self.assertIsNone(CHECK._inspect_sync_task(scheduled))
                self.assertTrue(scheduled['log_format_ok'])
        item = {'name': 'example', 'realtime': 'true'}
        failure = CHECK._inspect_sync_task(item, [{'run_timestamp': now, 'log_file': 'run_a.log', 'status': 'failed', 'reason': '超阈值'}])
        self.assertEqual(failure['task_type'], 'realtime_fallback')
        self.assertFalse(item['log_format_ok'])

    def test_scan_size_limit_is_explicit(self):
        now = int(time.time())
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory) / 'send/example/logs'
            logs.mkdir(parents=True)
            (logs / time.strftime('run_%Y%m%d_%H%M%S.log', time.localtime(now))).write_text('x' * (8 * 1024 * 1024 + 1))
            with patch.object(CHECK, 'RSYNCD_SERVER_DIR', directory):
                runs, errors = CHECK._scan_fallback_task({'name': 'example'}, now - 86400, now)
            self.assertTrue(errors)
            self.assertEqual(runs[0]['status'], 'unknown')
            self.assertIn('检查不完整', runs[0]['reason'])

    def test_logged_command_with_fake_sync(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            tree = ast.parse((PANEL / 'plugins/rsyncd/index.py').read_text())
        tree.body = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == '_realtime_run_command']
        scope = {'shlex': shlex}
        exec(compile(tree, '<rsyncd command>', 'exec'), scope)
        with tempfile.TemporaryDirectory(prefix='rsync test ') as directory:
            (Path(directory) / 'logs').mkdir()
            (Path(directory) / 'cmd').write_text('echo "Connection refused" >&2\nexit 12\n')
            result = subprocess.run(scope['_realtime_run_command'](directory), shell=True, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)  # Existing tee pipeline semantics.
            logs = list((Path(directory) / 'logs').glob('run_*.log'))
            self.assertEqual(len(logs), 1)
            content = logs[0].read_text()
            self.assertIn('JH_RSYNC_RUN_START pid=', content)
            self.assertIn('JH_RSYNC_RUN_END exit_code=12', content)
            self.assertIn('Connection refused', content)
            self.assertEqual(CHECK._fallback_run_status(content)[0], 'failed')


class ReportChecks(unittest.TestCase):
    def setUp(self):
        self.now = 1790900000
        self.analyser = HostReportAnalyser.__new__(HostReportAnalyser)
        self.analyser.now_ts = self.now
        self.window = self.analyser.get_report_window()
        self.task = 'storage<script>'

    def run_row(self, offset, status, name=None):
        return {'task_name': name or self.task, 'log_file': 'run_%s.log' % offset,
                'run_timestamp': self.now + offset, 'observed_timestamp': self.now,
                'status': status, 'reason': '删除比例超过阈值 <30%' if status == 'failed' else ''}

    def doc(self, runs):
        return {'host_id': 'H_FIXTURE', 'add_timestamp': self.now, 'execute_ok': True,
                'status': 'normal', 'collector_source': 'jh-panel-rsyncd-tool-check',
                'result': {'fallback_check_version': 1, 'fallback_scan_complete': True,
                           'fallback_runs': runs, 'send_open_realtime_list': [{'name': self.task}],
                           'realtime_format_ok': True, 'send_count': 1, 'send_open_count': 1}}

    def section(self, docs):
        return self.analyser._build_rsyncd_check_section(docs, self.window, [])

    def test_recovery_dedup_and_repeat_failure(self):
        failed, success = self.run_row(-300, 'failed'), self.run_row(-100, 'success')
        docs = [self.doc([failed]), self.doc([failed, success])]
        result = self.section(docs)
        self.assertEqual(len(result['error_tips']), 1)
        self.assertIn('窗口内失败 1 次', result['error_tips'][0])
        self.assertIn('已恢复', result['error_tips'][0])
        self.assertNotIn('<script>', str(result))
        docs.append(self.doc([self.run_row(-10, 'failed')]))
        result = self.section(docs)
        self.assertIn('窗口内失败 2 次', result['error_tips'][0])
        self.assertIn('异常未恢复', result['error_tips'][0])

    def test_window_updates_and_cleared_logs(self):
        start = self.run_row(-86400, 'failed')
        old = self.run_row(-86401, 'failed')
        end = self.run_row(0, 'success')
        result = self.section([self.doc([start, old]), self.doc([end])])
        self.assertIn('窗口内失败 1 次', result['error_tips'][0])
        running = self.run_row(-100, 'running')
        running['observed_timestamp'] -= 1
        done = self.run_row(-100, 'success')
        result = self.section([self.doc([done]), self.doc([running])])
        self.assertFalse(result['error_tips'])
        self.assertIn('正常；窗口内失败 0 次', result['tips'][0]['desc'])
        result = self.section([self.doc([old])])
        self.assertIn('窗口前最近运行异常', result['error_tips'][0])
        self.assertIn('窗口内失败 0 次', result['tips'][0]['desc'])

    def test_no_false_recovery(self):
        for status, name in [('success', 'another-task'), ('running', self.task), ('unknown', self.task)]:
            result = self.section([self.doc([self.run_row(-300, 'failed'), self.run_row(-10, status, name)])])
            self.assertIn('异常未恢复', result['error_tips'][0])

    def test_compatibility(self):
        doc = self.doc([])
        result = self.section([doc])
        self.assertIn('窗口内无兜底运行记录', result['tips'][0]['desc'])
        self.assertFalse(result['error_tips'])
        del doc['result']['fallback_check_version']
        self.assertIn('请更新插件', str(self.section([doc])['summary_tips']))
        doc['result']['send_open_realtime_list'] = []
        self.assertNotIn('请更新插件', str(self.section([doc])))
        doc = self.doc([])
        doc['result']['fallback_scan_complete'] = False
        self.assertIn('检查不完整', str(self.section([doc])['summary_tips']))
        doc = self.doc([self.run_row(-100, 'failed')])
        doc['result']['fixtime_abnormal_tasks'] = [{'name': self.task, 'task_type': 'realtime_fallback'},
                                                 {'name': 'scheduled', 'reason': '连接失败'}]
        result = self.section([doc])
        self.assertEqual(sum('实时任务兜底同步' in item for item in result['error_tips']), 1)
        self.assertIn('scheduled', str(result))
        doc['result']['send_open_realtime_list'][0]['status'] = 'disabled'
        self.assertNotIn('实时任务兜底同步', str(self.section([doc])))

    def test_collector_preserves_large_structured_result(self):
        payload = self.doc([self.run_row(-index, 'success') for index in range(150)])['result']
        process = types.SimpleNamespace(returncode=0, stdout=json.dumps(payload), stderr='')
        self.assertGreater(len(process.stdout), 8000)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(report_collector.os.path, 'isdir', return_value=True), \
                    patch.object(report_collector.os.path, 'isfile', return_value=True), \
                    patch.object(report_collector.subprocess, 'run', return_value=process):
                path = report_collector.export_rsyncd_tool_check(directory, {'host_id': 'H_FIXTURE', 'host_name': 'fixture', 'host_ip': '127.0.0.1'})
            saved = json.loads(Path(path).read_text())
            self.assertEqual(len(saved['result']['fallback_runs']), 150)
            self.assertEqual(len(saved['stdout']), 8000)

    def test_collector_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(report_collector.os.path, 'isdir', return_value=True), \
                    patch.object(report_collector.os.path, 'isfile', return_value=True), \
                    patch.object(report_collector.subprocess, 'run', side_effect=subprocess.TimeoutExpired('fixture', 120)):
                path = report_collector.export_rsyncd_tool_check(directory, {'host_id': 'H_FIXTURE', 'host_name': 'fixture', 'host_ip': '127.0.0.1'})
            saved = json.loads(Path(path).read_text())
            self.assertEqual(saved['status'], 'abnormal')
            self.assertFalse(saved['execute_ok'])
            self.assertIn('超时', saved['message'])

    def test_full_reports_and_mock_delivery(self):
        from jinja2 import Environment, FileSystemLoader
        analyser = self.analyser
        analyser.es_available = True
        analyser.es_skip_reason = ''
        analyser._es = types.SimpleNamespace(get=lambda *args: {}, index=lambda *args, **kwargs: {})
        analyser.thresholds = dict(report_analyser.DEFAULT_REPORT_THRESHOLDS)
        analyser._overview_env = Environment(loader=FileSystemLoader(str(ROOT / 'route/templates/report')), autoescape=False)
        analyser._build_monitor_task_section = lambda *args: {}
        analyser._build_monitor_task_overview = lambda *args: []
        analyser.is_ha_report_enabled = lambda: False
        host = {'host_id': 'H_FIXTURE', 'host_name': 'Rsyncd 验证主机', 'ip': '127.0.0.1',
                '_collected_host_name_resolved': True, 'status': 'online', 'is_pve': 0}
        group = {'status': [{'add_timestamp': self.now, 'add_time': self.window['end_time'], 'system': {}}],
                 'backup': [self.doc([self.run_row(-300, 'failed'), self.run_row(-100, 'success')])]}
        with patch.object(report_analyser.jh, 'getConfig', return_value='测试报告'):
            _, single = analyser.build_single_host_report(host, group, self.window)
            _, overview = analyser.build_overview_report([host], [single], self.window)
        self.assertTrue(single['is_abnormal'])
        self.assertIn('已恢复', single['html_content'])
        self.assertIn('已恢复', overview['html_content'])
        self.assertNotIn('<script>', single['html_content'])
        self.assertNotIn('<script>', overview['html_content'])
        sender = HostReportSender(es_client=analyser._es)
        self.assertEqual(sender._validate_report_for_delivery(single, 'single', self.window['report_date']), [])
        with patch.object(report_analyser.jh, 'notifyMessage', return_value=True) as notify, \
                patch.object(sender, '_get_email_recipients', return_value=['fixture@example.invalid']):
            sent, error = sender._send_report_document('host-report-single-test', 'fixture', single)
            self.assertTrue(sent, error)
            notify.assert_called_once()
        output = os.environ.get('RSYNCD_REPORT_SAMPLE_DIR')
        if output:
            Path(output).mkdir(parents=True, exist_ok=True)
            (Path(output) / 'single-recovered.html').write_text(single['html_content'])
            (Path(output) / 'overview-recovered.html').write_text(overview['html_content'])


if __name__ == '__main__':
    unittest.main()
