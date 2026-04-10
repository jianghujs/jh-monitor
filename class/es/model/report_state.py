# coding: utf-8


def build_validation_state(is_complete=True, status='ready', errors=None):
    if errors is None:
        errors = []
    return {
        'is_complete': is_complete,
        'status': status,
        'errors': errors
    }


def _normalize_delivery_time(last_sent_time):
    if last_sent_time is None:
        return None
    if str(last_sent_time).strip() == '':
        return None
    return last_sent_time


def build_delivery_state(status='pending', last_sent_time=None, recipients=None, retry_count=0, last_error=''):
    if recipients is None:
        recipients = []
    return {
        'status': status,
        'last_sent_time': _normalize_delivery_time(last_sent_time),
        'recipients': recipients,
        'retry_count': retry_count,
        'last_error': last_error
    }


def normalize_delivery_state(delivery=None):
    delivery = delivery or {}
    return build_delivery_state(
        status=delivery.get('status', 'pending'),
        last_sent_time=delivery.get('last_sent_time'),
        recipients=delivery.get('recipients', []),
        retry_count=delivery.get('retry_count', 0),
        last_error=delivery.get('last_error', '')
    )


__all__ = [
    'build_validation_state',
    'build_delivery_state',
    'normalize_delivery_state',
]
