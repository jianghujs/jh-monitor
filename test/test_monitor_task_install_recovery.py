# coding: utf-8

import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for path in ('class/core', 'class/plugin', 'class/es/service'):
    sys.path.insert(0, os.path.join(ROOT, path))

import monitor_task_event_service as events
from monitor_task_api import monitor_task_api


class InstallRecoveryTest(unittest.TestCase):
    def test_storage_retry_preserves_existing_index(self):
        es = Mock()
        conn = es.getConn.return_value
        conn.indices.get_index_template.return_value = {'index_templates': []}
        conn.indices.put_index_template.side_effect = [
            RuntimeError('429 circuit_breaking_exception'), {'acknowledged': True}]
        conn.indices.exists.return_value = True
        es.search.return_value = {'hits': {'hits': []}}
        with self.assertRaises(RuntimeError):
            events.ensureTaskEventStorage(es)
        events.ensureTaskEventStorage(es)
        self.assertEqual(conn.indices.put_index_template.call_count, 2)
        conn.indices.create.assert_not_called()
        conn.indices.delete.assert_not_called()

    def test_new_install_creates_template_before_index(self):
        es = Mock()
        conn = es.getConn.return_value
        conn.indices.get_index_template.return_value = {'index_templates': []}
        conn.indices.put_index_template.return_value = {'acknowledged': True}
        conn.indices.exists.return_value = False
        conn.indices.create.return_value = {'acknowledged': True}
        es.search.return_value = {'hits': {'hits': []}}
        events.ensureTaskEventStorage(es)
        calls = [str(c[0]) for c in conn.indices.mock_calls]
        self.assertLess(calls.index('put_index_template'), calls.index('create'))

    def test_query_errors_are_not_missing_logs(self):
        for response in (None, {'error': '429'}, {'_shards': {'failed': 1}}):
            es = Mock()
            es.search.return_value = response
            with self.assertRaises(RuntimeError):
                events.getLatestTaskEvent('task', 'host', es)
        api = monitor_task_api()
        with patch.object(events, 'getLatestTaskEvent', side_effect=RuntimeError('429')):
            status, message, _, _ = api._evaluateTaskStatus({
                'task_id': 'task', 'host_id': 'host', 'install_status': 'installed'})
        self.assertEqual(status, 'unknown')
        self.assertIn('429', message)
        self.assertNotIn('等待首次日志', message)

    def test_matching_template_is_not_rewritten(self):
        sys.path.insert(0, os.path.join(ROOT, 'class/es/model'))
        from report_schema import TASK_EVENT_INDEX_TEMPLATES
        es = Mock()
        conn = es.getConn.return_value
        conn.indices.get_index_template.return_value = {'index_templates': [
            {'index_template': TASK_EVENT_INDEX_TEMPLATES['host-monitor-task-event-template']}
        ]}
        conn.indices.exists.return_value = True
        es.search.return_value = {'hits': {'hits': []}}
        events.ensureTaskEventStorage(es)
        conn.indices.put_index_template.assert_not_called()
        conn.indices.create.assert_not_called()

    def test_registration_failure_is_reported(self):
        api = monitor_task_api()
        api.ensureMonitorTaskSchema = Mock()
        api._getHost = Mock(return_value={'host_id': 'host'})
        api.updateInstallStatus = Mock()
        with patch.object(events, 'ensureTaskEventStorage', side_effect=RuntimeError('429')):
            ok, msg, row = api.upsertTaskFromSetup({'task_id': 'task', 'host_id': 'host'})
        self.assertFalse(ok)
        self.assertIn('429', msg)
        self.assertIsNone(row)
        self.assertEqual(api.updateInstallStatus.call_args[0][:2], ('task', 'failed'))

    def test_installer_service_and_output_failures(self):
        # Load only function definitions; all operational commands are stubs.
        with open(os.path.join(ROOT, 'scripts/client/install/monitor_task.sh')) as f:
            script = f.read().split('case "$ACTION" in')[0]
        for scenario in ('restart', 'inactive', 'output', 'ok'):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as tmp:
                declarations = script.replace('/tmp/jh_monitor_task_filebeat_test.log', tmp + '/check.log')
                stubs = '''
SERVER_URL=""
SCENARIO="%s"
systemctl() {
  if [ "$SCENARIO" = restart ] && [ "$1" = restart ]; then return 1; fi
  if [ "$SCENARIO" = inactive ] && [ "$1" = is-active ]; then return 1; fi
  return 0
}
filebeat() {
  if [ "$SCENARIO" = output ] && [ "$2" = output ]; then return 1; fi
  return 0
}
validate_and_reload_filebeat
echo CHECK_PASSED
''' % scenario
                result = subprocess.run(['bash', '-c', declarations + stubs],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode == 0, scenario == 'ok', result.stderr)
                self.assertEqual('CHECK_PASSED' in result.stdout, scenario == 'ok')


if __name__ == '__main__':
    unittest.main()
