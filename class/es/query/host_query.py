# coding: utf-8


HOST_STATUS_INDEXES = 'host-system-status,host-*-system-status-*,*-host-system-status-*'
FILEBEAT_INDEXES = 'filebeat-*'
HOST_REPORT_SINGLE_INDEXES = 'host-report-single'

HOST_STATUS_SOURCE_FIELDS = [
    "host",
    "system",
    "pve",
    "add_time",
    "add_timestamp",
    "collector"
]

REPORT_LOG_SOURCE_FIELDS = ["message", "@timestamp", "host.ip"]
LOG_PATH_TIMESTAMP_SOURCE_FIELDS = {"includes": ["@timestamp"]}


def _buildDualTermShouldFilter(field, value):
    return {
        "bool": {
            "should": [
                {"term": {field + ".keyword": value}},
                {"term": {field: value}}
            ],
            "minimum_should_match": 1
        }
    }


def buildLatestStatusQuery(host_row):
    should_filters = []
    host_id = str(host_row.get('host_id', '') or '').strip()
    host_ip = str(host_row.get('ip', '') or '').strip()

    if host_id != '':
        should_filters.append({"term": {"host.host_id": host_id}})
    if host_ip != '':
        should_filters.append({"term": {"host.host_ip": host_ip}})

    if len(should_filters) == 0:
        return {"match_none": {}}

    return {
        "bool": {
            "filter": [
                {
                    "bool": {
                        "should": should_filters,
                        "minimum_should_match": 1
                    }
                }
            ]
        }
    }


def buildLatestStatusSearchBody(host_row):
    return {
        "size": 1,
        "query": buildLatestStatusQuery(host_row),
        "sort": [
            {
                "add_timestamp": {
                    "order": "desc",
                    "unmapped_type": "double"
                }
            }
        ],
        "_source": HOST_STATUS_SOURCE_FIELDS
    }


def buildHostStatusHistoryQuery(host_id='', start_ts=None, end_ts=None):
    filters = []
    host_id = str(host_id or '').strip()

    if host_id != '':
        filters.append({"term": {"host.host_id": host_id}})

    if start_ts is not None or end_ts is not None:
        range_body = {}
        if start_ts is not None:
            range_body['gte'] = start_ts
        if end_ts is not None and end_ts > 0:
            range_body['lte'] = end_ts
        filters.append({"range": {"add_timestamp": range_body}})

    if len(filters) == 0:
        return {"match_all": {}}

    return {"bool": {"filter": filters}}


def buildHostStatusHistorySearchBody(host_id='', start_ts=None, end_ts=None):
    return {
        "query": buildHostStatusHistoryQuery(host_id, start_ts, end_ts),
        "sort": [
            {
                "add_timestamp": {
                    "order": "asc",
                    "unmapped_type": "double"
                }
            }
        ]
    }


def buildLatestReportSearchBody(host_ip, log_path):
    host_ip = str(host_ip or '').strip()
    log_path = str(log_path or '').strip()

    if host_ip == '' or log_path == '':
        return {"size": 0, "query": {"match_none": {}}}

    return {
        "size": 1,
        "query": {
            "bool": {
                "filter": [
                    _buildDualTermShouldFilter("log.file.path", log_path),
                    _buildDualTermShouldFilter("host.ip", host_ip)
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
        "_source": REPORT_LOG_SOURCE_FIELDS
    }


def buildSingleHostReportQuery(host_ids, report_date=''):
    host_ids = [str(item or '').strip() for item in (host_ids or []) if str(item or '').strip() != '']
    report_date = str(report_date or '').strip()

    if len(host_ids) == 0:
        return {"match_none": {}}

    filters = [
        {
            "bool": {
                "should": [
                    {"terms": {"host_id.keyword": host_ids}},
                    {"terms": {"host_id": host_ids}}
                ],
                "minimum_should_match": 1
            }
        }
    ]
    if report_date != '':
        filters.append({"term": {"report_date": report_date}})

    return {"bool": {"filter": filters}}


def buildSingleHostReportSearchBody(host_ids, report_date='', size=None):
    if size is None:
        size = len(host_ids or [])
    if size <= 0:
        size = 10

    return {
        "size": size,
        "query": buildSingleHostReportQuery(host_ids, report_date),
        "sort": [
            {
                "report_date": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            },
            {
                "report_time.keyword": {
                    "order": "desc",
                    "unmapped_type": "keyword"
                }
            }
        ],
        "collapse": {
            "field": "host_id.keyword"
        }
    }


def buildLogPathListSearchBody(host_ip):
    host_ip = str(host_ip or '').strip()

    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"host.ip": host_ip}}
                ]
            }
        },
        "aggs": {
            "unique_paths": {
                "terms": {
                    "field": "log.file.path",
                    "size": 10000
                },
                "aggs": {
                    "latest_update": {
                        "top_hits": {
                            "sort": [
                                {
                                    "@timestamp": {
                                        "order": "desc"
                                    }
                                }
                            ],
                            "_source": LOG_PATH_TIMESTAMP_SOURCE_FIELDS,
                            "size": 1
                        }
                    }
                }
            }
        }
    }


def buildLogDetailSearchBody(host_ip, log_file_path):
    return {
        "size": 100,
        "query": {
            "bool": {
                "filter": [
                    {"term": {"log.file.path": log_file_path}},
                    {"term": {"host.ip": host_ip}}
                ]
            }
        },
        "sort": [
            {
                "@timestamp": {
                    "order": "desc"
                }
            }
        ]
    }
