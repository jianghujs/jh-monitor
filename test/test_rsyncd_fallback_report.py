#!/usr/bin/env python3
# coding: utf-8
"""Offline latest-log checks for both rsyncd task types."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PANEL = Path(os.environ.get('JH_PANEL_TEST_ROOT', '/www/server/jh-panel'))
for path in ('class/core', 'class/plugin', 'class/es/model', 'scripts', 'scripts/client'):
    sys.path.insert(0, str(ROOT / path))
os.chdir(ROOT)
import report_analyser
from report_analyser import HostReportAnalyser
from report_sender import HostReportSender

spec = importlib.util.spec_from_file_location('rsyncd_check_under_test', PANEL / 'plugins/rsyncd/tool_check.py')
CHECK = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, {'mw': types.SimpleNamespace(
        toTime=lambda ts: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts)),
        readFile=lambda path: Path(path).read_text())}):
    spec.loader.exec_module(CHECK)
SUCCESS = 'sending incremental file list\nsent 100 bytes  received 20 bytes\ntotal size is 200 speedup is 2\n'


class LatestLogChecks(unittest.TestCase):
    def setUp(self):
        self.now = 1790900000
        self.analyser = HostReportAnalyser.__new__(HostReportAnalyser)
        self.analyser.now_ts = self.now
        self.window = self.analyser.get_report_window()
        self.task = 'storage<script>'

    def doc(self, content, realtime='true', age=100):
        with tempfile.TemporaryDirectory() as directory:
            logs = Path(directory) / 'send' / self.task / 'logs'
            logs.mkdir(parents=True)
            if content is not None:
                path = logs / 'run_latest.log'
                path.write_text(content)
                os.utime(path, (self.now - age, self.now - age))
            config = Path(directory) / 'config.json'
            config.write_text(json.dumps({'send': {'list': [
                {'name': self.task, 'realtime': realtime},
                {'name': 'disabled', 'realtime': realtime, 'status': 'disabled'}]}}))
            status = Path(directory) / 'lsyncd.status'
            status.write_text('Lsyncd status report at Fri Oct  2 08:13:20 2026\nSync1 source=/tmp\nThere are 0 delays\nFiltering: nothing.')
            with patch.multiple(CHECK, RSYNCD_SERVER_DIR=directory, RSYNCD_CONFIG_FILE=str(config), LSYNCD_STATUS_FILE=str(status)), patch.object(CHECK.time, 'time', return_value=self.now):
                result = CHECK.getRsyncdInfo()
        return {'host_id': 'H_FIXTURE', 'add_timestamp': self.now, 'execute_ok': True,
                'status': 'normal', 'collector_source': 'jh-panel-rsyncd-tool-check', 'result': result}

    def test_both_task_types_share_rules(self):
        cases = [(SUCCESS, 100, False), (None, 100, True), (SUCCESS, 86401, True),
                 (SUCCESS, 86400, False), ('', 100, True), ('Permission denied', 100, True),
                 ('abort: delete ratio exceeds threshold', 100, True)]
        for realtime in ('true', 'false'):
            for content, age, abnormal in cases:
                with self.subTest(realtime=realtime, content=content, age=age):
                    result = self.doc(content, realtime, age)['result']
                    self.assertEqual(bool(result['fixtime_abnormal_tasks']), abnormal)
                    self.assertEqual(len([item for item in result['send_list'] if item.get('status') == 'disabled']), 1)
                    self.assertFalse(any(key.startswith('fallback_') for key in result))
                    self.assertEqual(result['send_open_list'][0]['log_format_ok'], not abnormal)

    def test_missing_directory_and_read_error(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(CHECK, 'RSYNCD_SERVER_DIR', directory):
            item = {'name': 'example', 'realtime': 'true'}
            self.assertIn('未找到', CHECK._inspect_sync_task(item)['reason'])
            logs = Path(directory) / 'send/example/logs'
            logs.mkdir(parents=True)
            (logs / 'run_latest.log').write_text(SUCCESS)
            with patch.object(CHECK.mw, 'readFile', side_effect=PermissionError):
                self.assertIn('读取', CHECK._inspect_sync_task(item)['reason'])

    def test_tolerated_warnings(self):
        for code in (23, 24):
            self.assertFalse(self.doc(SUCCESS + 'rsync warning ignored: exit %s' % code)['result']['fixtime_abnormal_tasks'])

    def test_latest_snapshot_only(self):
        failed = self.doc('abort: delete ratio exceeds threshold')
        failed['add_timestamp'] -= 60
        success = self.doc(SUCCESS)
        result = self.analyser._build_rsyncd_check_section([failed, success], self.window, [])
        self.assertFalse(result['error_tips'])
        self.assertIn('storage&lt;script&gt;', result['tips'][0]['desc'])
        self.assertNotIn('兜底', str(result))

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
                 'backup': [self.doc('abort: delete ratio exceeds threshold')]}
        with patch.object(report_analyser.jh, 'getConfig', return_value='测试报告'):
            _, single = analyser.build_single_host_report(host, group, self.window)
            _, overview = analyser.build_overview_report([host], [single], self.window)
        self.assertTrue(single['is_abnormal'])
        self.assertIn('超过阈值', single['html_content'])
        self.assertIn('超过阈值', overview['html_content'])
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
            (Path(output) / 'single-abnormal.html').write_text(single['html_content'])
            (Path(output) / 'overview-abnormal.html').write_text(overview['html_content'])


if __name__ == '__main__':
    unittest.main()
