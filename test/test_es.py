#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import sys
import traceback

sys.path.append(os.getcwd() + "/class/core")
sys.path.append(os.getcwd() + "/class/plugin")

import jh
from es import ES


def build_panel_report_query(host_ip):
    return {
        "size": 1,
        "query": {
            "bool": {
                "filter": [
                    {
                        "bool": {
                            "should": [
                                {
                                    "term": {
                                        "log.file.path.keyword": "/www/server/jh-panel/logs/report.log"
                                    }
                                },
                                {
                                    "term": {
                                        "log.file.path": "/www/server/jh-panel/logs/report.log"
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    {
                        "bool": {
                            "should": [
                                {
                                    "term": {
                                        "host.ip.keyword": host_ip
                                    }
                                },
                                {
                                    "term": {
                                        "host.ip": host_ip
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    }
                ]
            }
        },
        "sort": [
            {
                "@timestamp": {
                    "order": "desc"
                }
            }
        ],
        "_source": ["message", "@timestamp", "host.ip"]
    }


def get_host_ips():
    rows = jh.M('host').field('ip').select()
    if isinstance(rows, str):
        print("Failed to load host list:", rows)
        return []
    ips = []
    for row in rows:
        host_ip = row.get('ip')
        if host_ip:
            ips.append(host_ip)
    return ips


def main():
    es = ES()
    host_ips = get_host_ips()
    if not host_ips:
        print("No host IPs found")
        return 1

    panel_report = {}
    msearch_body = []
    for host_ip in host_ips:
        msearch_body.append({"index": "filebeat-*"})
        msearch_body.append(build_panel_report_query(host_ip))

    try:
        response = es.getConn().msearch(body=msearch_body)
    except Exception:
        traceback.print_exc()
        return 1

    if response is None:
        print("ES msearch returned None")
        return 1

    if hasattr(response, "body"):
        response = response.body
    elif hasattr(response, "to_dict"):
        response = response.to_dict()

    responses = response.get("responses", [])
    for idx, item in enumerate(responses):
        if idx >= len(host_ips):
            break
        host_ip = host_ips[idx]
        print("========= ES Response Start:", host_ip, "=========")
        print(json.dumps(item, indent=2, ensure_ascii=False))
        print("========= ES Response End:", host_ip, "=========")

        hits = item.get("hits", {}).get("hits", [])
        if not hits:
            continue
        source = hits[0].get("_source", {})
        panel_report[host_ip] = source.get("message")

    print("========= Panel Report Parsed Start =========")
    print(json.dumps(panel_report, indent=2, ensure_ascii=False))
    print("========= Panel Report Parsed End =========")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
