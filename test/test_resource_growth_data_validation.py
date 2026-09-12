#!/usr/bin/env python3

import json
import os
import sys
import unittest


ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT_DIR, 'class', 'core'))

import jh


class ResourceGrowthDataValidationTest(unittest.TestCase):
    def test_invalid_disk_records_are_ignored(self):
        current_time = 1778640000
        latest_record = {
            'disk_info': json.dumps([
                'invalid disk value',
                {'mountpoint': '/', 'usedPercent': 70.0}
            ])
        }
        history_records = [
            {
                'disk_info': json.dumps([
                    'invalid disk value',
                    {'mountpoint': '/', 'usedPercent': 60.0}
                ]),
                'addtime': current_time - 3600
            },
            {
                'disk_info': json.dumps({
                    'mountpoint': '/',
                    'usedPercent': 65.0
                }),
                'addtime': current_time - 1800
            },
            {
                'disk_info': json.dumps([
                    {'mountpoint': '/', 'usedPercent': 70.0}
                ]),
                'addtime': current_time
            }
        ]

        alarm = jh.analyze_resource_growth(
            'test-host', 'test-host', latest_record, history_records,
            'disk', 'disk_info', 80, 24, 72, 600, 1800,
            current_time, 60
        )

        self.assertIsInstance(alarm, dict)
        self.assertIn('level', alarm)

    def test_invalid_memory_shape_returns_empty_alarm(self):
        current_time = 1778640000
        history_records = [
            {'mem_info': json.dumps({'usedPercent': 60.0}), 'addtime': current_time - 3600},
            {'mem_info': json.dumps({'usedPercent': 70.0}), 'addtime': current_time}
        ]

        alarm = jh.analyze_resource_growth(
            'test-host', 'test-host', {'mem_info': json.dumps([])}, history_records,
            'memory', 'mem_info', 80, 24, 72, 600, 1800,
            current_time, 60
        )

        self.assertEqual(alarm['level'], None)


if __name__ == '__main__':
    unittest.main()
