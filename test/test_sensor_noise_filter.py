#!/usr/bin/env python3
# coding: utf-8
"""Validate obvious lm-sensors noise filtering for host reports."""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')
CORE_DIR = os.path.join(ROOT_DIR, 'class', 'core')
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
ES_MODEL_DIR = os.path.join(ROOT_DIR, 'class', 'es', 'model')
CLIENT_DIR = os.path.join(ROOT_DIR, 'scripts', 'client')

for path in (ROOT_DIR, SCRIPTS_DIR, CORE_DIR, PLUGIN_DIR, ES_MODEL_DIR, CLIENT_DIR):
    if path not in sys.path:
        sys.path.insert(0, path)

os.chdir(ROOT_DIR)

from report_analyser import filter_obvious_sensor_noise


def assert_contains(names, expected):
    missing = [name for name in expected if name not in names]
    if missing:
        raise AssertionError('missing expected sensors: {0}'.format(', '.join(missing)))


def assert_not_contains(names, unexpected):
    found = [name for name in unexpected if name in names]
    if found:
        raise AssertionError('unexpected sensors kept: {0}'.format(', '.join(found)))


def main():
    sensors = {
        'temperatures': [
            {'name': 'AUXTIN1', 'value': 127, 'unit': '°C'},
            {'name': 'AUXTIN2', 'value': 109, 'unit': '°C'},
            {'name': 'T_Sensor', 'value': -40, 'unit': '°C'},
            {'name': 'PCH_CPU_TEMP', 'value': 0, 'unit': '°C'},
            {'name': 'temp1', 'value': 'N/A', 'unit': '°C'},
            {'name': 'Tctl', 'value': 72, 'unit': '°C'},
            {'name': 'Tccd1', 'value': 70, 'unit': '°C'},
            {'name': 'TSI0_TEMP', 'value': 71, 'unit': '°C'},
            {'name': 'PECI Agent 0', 'value': 73, 'unit': '°C'},
            {'name': 'Motherboard', 'value': 45, 'unit': '°C'},
            {'name': 'Chipset', 'value': 50, 'unit': '°C'},
            {'name': 'VRM', 'value': 82, 'unit': '°C'},
            {'name': 'Composite', 'value': 54, 'unit': '°C'},
            {'name': 'Sensor 1', 'value': 56, 'unit': '°C'},
            {'name': 'PHY Temperature', 'value': 65, 'unit': '°C'},
            {'name': 'MAC Temperature', 'value': 66, 'unit': '°C'},
        ],
        'fans': [
            {'name': 'fan1', 'value': 0, 'unit': 'RPM'},
            {'name': 'CPU Fan', 'value': 900, 'unit': 'RPM'},
        ],
        'voltages': [
            {'name': 'in0', 'value': 0.0, 'unit': 'V', 'min': 0, 'max': 0, 'status': 'ALARM'},
            {'name': 'Vcore', 'value': 1.12, 'unit': 'V'},
        ],
        'intrusions': [
            {'name': 'intrusion0', 'value': 'ALARM'},
            {'name': 'chassis', 'value': 'OK'},
        ],
    }
    issues = [
        {'category': '温度', 'severity': 'critical', 'message': 'AUXTIN1 127°C', 'detail': '传感器 AUXTIN1 温度过高'},
        {'category': '温度', 'severity': 'warning', 'message': 'VRM 82°C', 'detail': '传感器 VRM 温度过高'},
        {'category': '风扇', 'severity': 'warning', 'message': '风扇停转且温度异常', 'detail': '检测到 fan1 转速为 0'},
        {'category': '电压', 'severity': 'warning', 'message': 'in0 ALARM', 'detail': 'in0 min=0 max=0'},
        {'category': '机箱', 'severity': 'warning', 'message': 'intrusion0 ALARM', 'detail': 'intrusion0 opened'},
    ]

    cleaned, cleaned_issues = filter_obvious_sensor_noise(sensors, issues)
    temp_names = [item.get('name') for item in cleaned.get('temperatures', [])]
    fan_names = [item.get('name') for item in cleaned.get('fans', [])]
    volt_names = [item.get('name') for item in cleaned.get('voltages', [])]
    intrusion_names = [item.get('name') for item in cleaned.get('intrusions', [])]
    issue_messages = [item.get('message') for item in cleaned_issues]

    assert_not_contains(temp_names, ['AUXTIN1', 'AUXTIN2', 'T_Sensor', 'PCH_CPU_TEMP', 'temp1'])
    assert_contains(temp_names, ['Tctl', 'Tccd1', 'TSI0_TEMP', 'PECI Agent 0', 'Motherboard', 'Chipset', 'VRM', 'Composite', 'Sensor 1', 'PHY Temperature', 'MAC Temperature'])
    assert_not_contains(fan_names, ['fan1'])
    assert_contains(fan_names, ['CPU Fan'])
    assert_not_contains(volt_names, ['in0'])
    assert_contains(volt_names, ['Vcore'])
    assert_not_contains(intrusion_names, ['intrusion0'])
    assert_contains(intrusion_names, ['chassis'])
    assert_not_contains(issue_messages, ['AUXTIN1 127°C', '风扇停转且温度异常', 'in0 ALARM', 'intrusion0 ALARM'])
    assert_contains(issue_messages, ['VRM 82°C'])
    print('[OK] sensor noise filter sample passed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
