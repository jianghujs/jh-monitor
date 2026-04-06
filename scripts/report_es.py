# coding: utf-8

import json
import os

from elasticsearch import Elasticsearch

ES_CONFIG_PATH = 'data/es.json'
DATE_TIME_FORMAT = 'yyyy-MM-dd HH:mm:ss||strict_date_optional_time'
DATE_ONLY_FORMAT = 'yyyy-MM-dd||strict_date_optional_time'

REPORT_INDEXES = {
    'host-system-status': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'dynamic': True,
            'properties': {
                'host': {
                    'properties': {
                        'host_id': {'type': 'keyword'},
                        'host_name': {'type': 'keyword'},
                        'host_ip': {'type': 'ip'},
                        'host_group': {'type': 'keyword'},
                        'host_status': {'type': 'keyword'}
                    }
                },
                'system': {
                    'properties': {
                        'cpu': {'type': 'float'},
                        'memory': {'type': 'float'},
                        'load': {
                            'properties': {
                                'pro': {'type': 'float'},
                                'one': {'type': 'float'},
                                'five': {'type': 'float'},
                                'fifteen': {'type': 'float'}
                            }
                        },
                        'disks': {'type': 'nested'}
                    }
                },
                'site': {'type': 'nested'},
                'jianghujs': {'type': 'nested'},
                'docker': {'type': 'nested'},
                'mysql': {'type': 'object', 'dynamic': True},
                'lsync': {'type': 'object', 'dynamic': True},
                'rsync': {'type': 'nested'},
                'add_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'add_timestamp': {'type': 'double'}
            }
        }
    },
    'host-xtrabackup': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'dynamic': True,
            'properties': {
                'host_id': {'type': 'keyword'},
                'host_name': {'type': 'keyword'},
                'host_ip': {'type': 'ip'},
                'id': {'type': 'keyword'},
                'add_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'add_timestamp': {'type': 'double'},
                'size': {'type': 'keyword'},
                'size_bytes': {'type': 'double'},
                'collector_source': {'type': 'keyword'}
            }
        }
    },
    'host-xtrabackup-inc': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'dynamic': True,
            'properties': {
                'host_id': {'type': 'keyword'},
                'host_name': {'type': 'keyword'},
                'host_ip': {'type': 'ip'},
                'id': {'type': 'keyword'},
                'backup_type': {'type': 'keyword'},
                'add_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'add_timestamp': {'type': 'double'},
                'size': {'type': 'keyword'},
                'size_bytes': {'type': 'double'},
                'collector_source': {'type': 'keyword'}
            }
        }
    },
    'host-backup': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'dynamic': True,
            'properties': {
                'host_id': {'type': 'keyword'},
                'host_name': {'type': 'keyword'},
                'host_ip': {'type': 'ip'},
                'type': {'type': 'keyword'},
                'filename': {'type': 'keyword'},
                'path': {'type': 'keyword'},
                'size': {'type': 'keyword'},
                'size_bytes': {'type': 'double'},
                'message': {'type': 'text'},
                'add_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'collector_source': {'type': 'keyword'}
            }
        }
    },
    'host-report-single': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'dynamic': True,
            'properties': {
                'report_type': {'type': 'keyword'},
                'report_date': {'type': 'date', 'format': DATE_ONLY_FORMAT},
                'report_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'start_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'end_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'start_date': {'type': 'date', 'format': DATE_ONLY_FORMAT},
                'end_date': {'type': 'date', 'format': DATE_ONLY_FORMAT},
                'host_id': {'type': 'keyword'},
                'host_name': {'type': 'keyword'},
                'host_ip': {'type': 'ip'},
                'summary_tips': {'type': 'text'},
                'error_tips': {'type': 'text'},
                'html_content': {'type': 'text'},
                'validation': {
                    'properties': {
                        'is_complete': {'type': 'boolean'},
                        'status': {'type': 'keyword'},
                        'errors': {'type': 'keyword'}
                    }
                },
                'delivery': {
                    'properties': {
                        'status': {'type': 'keyword'},
                        'last_sent_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                        'recipients': {'type': 'keyword'},
                        'retry_count': {'type': 'integer'},
                        'last_error': {'type': 'text'}
                    }
                },
                'extra_info': {'type': 'object', 'enabled': False}
            }
        }
    },
    'host-report-overview': {
        'settings': {
            'number_of_shards': 1,
            'number_of_replicas': 0
        },
        'mappings': {
            'dynamic': True,
            'properties': {
                'report_type': {'type': 'keyword'},
                'report_date': {'type': 'date', 'format': DATE_ONLY_FORMAT},
                'report_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'start_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'end_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'title': {'type': 'text'},
                'html_content': {'type': 'text'},
                'host_overview_info': {'type': 'object', 'dynamic': True},
                'host_overview_tips': {'type': 'nested'},
                'exception_host_summary_tips': {'type': 'nested'},
                'single_host_report_list': {'type': 'nested'},
                'validation': {
                    'properties': {
                        'is_complete': {'type': 'boolean'},
                        'status': {'type': 'keyword'},
                        'errors': {'type': 'keyword'}
                    }
                },
                'delivery': {
                    'properties': {
                        'status': {'type': 'keyword'},
                        'last_sent_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                        'recipients': {'type': 'keyword'},
                        'retry_count': {'type': 'integer'},
                        'last_error': {'type': 'text'}
                    }
                },
                'extra_info': {'type': 'object', 'enabled': False}
            }
        }
    }
}


def read_es_config(path=ES_CONFIG_PATH):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, 'r') as fp:
            return json.load(fp)
    except Exception:
        return {}


def normalize_es_hosts(es_config):
    hosts = es_config.get('hosts', [])
    if isinstance(hosts, list) and len(hosts) > 0:
        return hosts
    return [{'host': '127.0.0.1', 'port': 9200, 'scheme': 'http'}]


class ReportES(object):
    def __init__(self, config_path=ES_CONFIG_PATH):
        self.config_path = config_path
        self.es_config = read_es_config(config_path)
        self.client = None

    def get_client(self):
        if self.client is not None:
            return self.client

        kwargs = {
            'hosts': normalize_es_hosts(self.es_config),
            'request_timeout': 10,
            'verify_certs': False
        }
        username = self.es_config.get('username', '')
        password = self.es_config.get('password', '')
        if username != '':
            kwargs['basic_auth'] = (username, password)

        self.client = Elasticsearch(**kwargs)
        return self.client

    def ensure_indices(self):
        client = self.get_client()
        results = []
        for index_name, index_body in REPORT_INDEXES.items():
            exists = client.indices.exists(index=index_name)
            if exists:
                client.indices.put_mapping(index=index_name, body=index_body.get('mappings', {}))
                results.append({'index': index_name, 'action': 'updated'})
            else:
                client.indices.create(index=index_name, body=index_body)
                results.append({'index': index_name, 'action': 'created'})
        return results


def build_validation_state(is_complete=True, status='ready', errors=None):
    if errors is None:
        errors = []
    return {
        'is_complete': is_complete,
        'status': status,
        'errors': errors
    }


def build_delivery_state(status='pending', last_sent_time='', recipients=None, retry_count=0, last_error=''):
    if recipients is None:
        recipients = []
    return {
        'status': status,
        'last_sent_time': last_sent_time,
        'recipients': recipients,
        'retry_count': retry_count,
        'last_error': last_error
    }
