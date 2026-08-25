# coding: utf-8

import json


def parse_csv_args(raw_items):
    values = []
    for item in raw_items or []:
        for value in str(item or '').split(','):
            value = value.strip()
            if value != '' and value not in values:
                values.append(value)
    return values


def parse_api_response(raw_response):
    if isinstance(raw_response, dict):
        return raw_response
    try:
        return json.loads(raw_response)
    except Exception:
        return {
            'status': False,
            'msg': '接口返回不是 JSON',
            'raw_response': raw_response
        }


def print_json(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))

