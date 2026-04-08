# coding: utf-8

DATE_TIME_FORMAT = 'yyyy-MM-dd HH:mm:ss||strict_date_optional_time'
DATE_ONLY_FORMAT = 'yyyy-MM-dd||strict_date_optional_time'

REPORT_INDEXES = {
    'host-debian-system-status': {
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
                        'host_status': {'type': 'keyword'},
                        'system_type': {'type': 'keyword'}
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
    'host-pve-system-status': {
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
                        'host_status': {'type': 'keyword'},
                        'system_type': {'type': 'keyword'}
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
                'pve': {'type': 'object', 'dynamic': True},
                'add_time': {'type': 'date', 'format': DATE_TIME_FORMAT},
                'add_timestamp': {'type': 'double'}
            }
        }
    },
    'host-debian-xtrabackup': {
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
    'host-debian-xtrabackup-inc': {
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
    'host-debian-backup': {
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


__all__ = [
    'DATE_TIME_FORMAT',
    'DATE_ONLY_FORMAT',
    'REPORT_INDEXES',
]
