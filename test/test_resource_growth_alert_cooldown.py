#!/usr/bin/env python3

import os
import sys
import time
import unittest
from unittest import mock


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

import task


class FakeAlarmSql:
    def __init__(self, insert_result):
        self.insert_result = insert_result
        self.insert_args = None

    def table(self, table_name):
        self.table_name = table_name
        return self

    def add(self, keys, values):
        self.insert_args = (keys, values)
        return self.insert_result


class ResourceGrowthAlertCooldownTest(unittest.TestCase):
    def test_query_error_fails_closed(self):
        should_skip, error = task.get_resource_growth_alarm_cooldown_decision(
            'error: database is locked', 10000, '紧急', 3600, 7200
        )

        self.assertTrue(should_skip)
        self.assertIn('database is locked', error)

    def test_recent_critical_alarm_is_suppressed(self):
        current_time = 10000
        last_alarm = {
            'alarm_level': '紧急',
            'addtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time - 300))
        }

        should_skip, error = task.get_resource_growth_alarm_cooldown_decision(
            last_alarm, current_time, '紧急', 3600, 7200
        )

        self.assertTrue(should_skip)
        self.assertEqual(error, '')

    def test_warning_cooldown_does_not_suppress_critical_escalation(self):
        current_time = 10000
        last_alarm = {
            'alarm_level': '警告',
            'addtime': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time - 300))
        }

        should_skip, error = task.get_resource_growth_alarm_cooldown_decision(
            last_alarm, current_time, '紧急', 3600, 7200
        )

        self.assertFalse(should_skip)
        self.assertEqual(error, '')

    def test_empty_alarm_history_allows_notification(self):
        should_skip, error = task.get_resource_growth_alarm_cooldown_decision(
            [], 10000, '紧急', 3600, 7200
        )

        self.assertFalse(should_skip)
        self.assertEqual(error, '')

    def test_persistence_failure_stops_notification(self):
        sql = FakeAlarmSql('error: database is locked')

        with mock.patch.object(task.jh, 'notifyMessage') as notify_message:
            persisted, error = task.persist_and_notify_resource_growth_alarm(
                sql, 'host-1', 'Host 1', '紧急', 'content',
                '2026-10-19 10:00:00', 'title', '<p>content</p>', 3600
            )

        self.assertFalse(persisted)
        self.assertIn('database is locked', error)
        notify_message.assert_not_called()

    def test_notification_uses_host_level_key_and_configured_interval(self):
        sql = FakeAlarmSql(456)

        with mock.patch.object(task.jh, 'notifyMessage', return_value=True) as notify_message:
            persisted, error = task.persist_and_notify_resource_growth_alarm(
                sql, 'host-1', 'Host 1', '警告', 'content',
                '2026-10-19 10:00:00', 'title', '<p>content</p>', 7200
            )

        self.assertTrue(persisted)
        self.assertEqual(error, '')
        notify_message.assert_called_once_with(
            title='title',
            msg='<p>content</p>',
            msgtype='html',
            stype='资源增长预警:host-1:warning',
            trigger_time=7200
        )


if __name__ == '__main__':
    unittest.main()
