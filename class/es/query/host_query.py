# coding: utf-8


HOST_STATUS_INDEXES = 'host-system-status,host-*-system-status-*,*-host-system-status-*'
FILEBEAT_INDEXES = 'filebeat-*'
LOG_MONITOR_INDEXES = (
    'filebeat-*,'
    'host-*-syslog-*,'
    'host-*-nginx-*,'
    'host-*-nginx-error-*,'
    'host-*-eggjs-*,'
    'host-*-mysql-*,'
    'host-*-jh-panel-*'
)
HOST_REPORT_SINGLE_INDEXES = 'host-report-single,host-report-single-test'
HOST_REPORT_SINGLE_DATA_STREAM_PREFIX = 'host-report-single'
HOST_REPORT_TEST_SINGLE_DATA_STREAM_PREFIX = 'host-report-test-single'
HOST_REPORT_SINGLE_DATA_STREAM_INDEXES = 'host-report-single-*'

HOST_STATUS_SOURCE_FIELDS = [
    "host",
    "system",
    "pve",
    "add_time",
    "add_timestamp",
    "collector"
]

REPORT_LOG_SOURCE_FIELDS = ["message", "@timestamp", "host.ip"]
LOG_DETAIL_SOURCE_FIELDS = ["message", "@timestamp", "host.ip", "log.file.path"]
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
                "report_time": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            },
            {
                "report_date": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            }
        ]
    }


def buildLatestSingleHostReportDataStreamSearchBody(host_ids, size=None):
    if size is None:
        size = len(host_ids or []) * 10
    if size <= 0:
        size = 100
    if size < 100:
        size = 100

    return {
        "size": size,
        "query": buildSingleHostReportQuery(host_ids, ''),
        "sort": [
            {
                "report_time": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            },
            {
                "@timestamp": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            },
            {
                "report_date": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            }
        ]
    }


def buildLatestSingleHostReportLegacySearchBody(host_ids, size=None):
    if size is None:
        size = len(host_ids or []) * 5
    if size <= 0:
        size = 100
    if size < 100:
        size = 100
    return buildSingleHostReportSearchBody(host_ids, size=size)


def buildLogPathListSearchBody(host_ip):
    host_ip = str(host_ip or '').strip()

    if host_ip == '':
        return {"size": 0, "query": {"match_none": {}}}

    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    _buildDualTermShouldFilter("host.ip", host_ip)
                ]
            }
        },
        "aggs": {
            "unique_paths": {
                "terms": {
                    "field": "log.file.path",
                    "size": 10000,
                    "order": {
                        "latest_timestamp": "desc"
                    }
                },
                "aggs": {
                    "latest_timestamp": {
                        "max": {
                            "field": "@timestamp"
                        }
                    },
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


def buildLogPathCompositeSearchBody(host_ip, after_key=None, page_size=500):
    host_ip = str(host_ip or '').strip()

    if host_ip == '':
        return {"size": 0, "query": {"match_none": {}}}

    try:
        page_size = int(page_size)
    except Exception:
        page_size = 500
    if page_size < 1:
        page_size = 1
    if page_size > 1000:
        page_size = 1000

    composite_body = {
        "size": page_size,
        "sources": [
            {
                "path": {
                    "terms": {
                        "field": "log.file.path"
                    }
                }
            }
        ]
    }
    if after_key:
        composite_body["after"] = after_key

    return {
        "size": 0,
        "query": {
            "bool": {
                "filter": [
                    _buildDualTermShouldFilter("host.ip", host_ip)
                ]
            }
        },
        "aggs": {
            "unique_paths": {
                "composite": composite_body,
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


def buildLogDetailQuery(host_ip, log_file_path, keyword=''):
    host_ip = str(host_ip or '').strip()
    log_file_path = str(log_file_path or '').strip()
    keyword = str(keyword or '').strip()

    if host_ip == '' or log_file_path == '':
        return {"match_none": {}}

    bool_query = {
        "filter": [
            _buildDualTermShouldFilter("log.file.path", log_file_path),
            _buildDualTermShouldFilter("host.ip", host_ip)
        ]
    }
    if keyword != '':
        bool_query["must"] = [
            {
                "simple_query_string": {
                    "query": keyword,
                    "fields": ["message"],
                    "default_operator": "and"
                }
            }
        ]

    return {"bool": bool_query}


def buildLogDetailSearchBody(host_ip, log_file_path, keyword='', page=1, limit=100):
    try:
        page = int(page)
    except Exception:
        page = 1
    if page < 1:
        page = 1

    try:
        limit = int(limit)
    except Exception:
        limit = 100
    if limit < 1:
        limit = 1

    return {
        "from": (page - 1) * limit,
        "size": limit,
        "track_total_hits": True,
        "query": buildLogDetailQuery(host_ip, log_file_path, keyword),
        "sort": [
            {
                "@timestamp": {
                    "order": "desc",
                    "unmapped_type": "date"
                }
            }
        ],
        "_source": LOG_DETAIL_SOURCE_FIELDS
    }
