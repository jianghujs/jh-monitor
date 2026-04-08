# coding: utf-8


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


__all__ = [
    'build_validation_state',
    'build_delivery_state',
]
