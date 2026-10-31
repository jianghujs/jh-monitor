# coding: utf-8

import datetime
import time


STALE_SECONDS = 24 * 60 * 60


def parse_timestamp(value, default=0):
    if value in (None, ''):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return default
    try:
        return int(float(text))
    except (TypeError, ValueError):
        pass
    try:
        parsed = datetime.datetime.fromisoformat(text.replace('Z', '+00:00'))
        if parsed.tzinfo is not None:
            return int(parsed.timestamp())
        return int(time.mktime(parsed.timetuple()))
    except (TypeError, ValueError, OverflowError):
        return default


def format_timestamp(timestamp):
    timestamp = parse_timestamp(timestamp)
    if timestamp <= 0:
        return ''
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))


def derive_reporting_freshness(reference_time=None, report_time=None, created_time=None, display_report_time=None):
    reference_ts = parse_timestamp(reference_time, int(time.time()))
    report_ts = parse_timestamp(report_time)
    created_ts = parse_timestamp(created_time)

    if report_ts > 0:
        age_seconds = max(reference_ts - report_ts, 0)
        freshness = 'stale' if age_seconds >= STALE_SECONDS else 'fresh'
        abnormal = freshness == 'stale'
        status_text = '超过24小时未上报' if abnormal else '上报正常'
    else:
        age_seconds = max(reference_ts - created_ts, 0) if created_ts > 0 else 0
        freshness = 'never_reported' if created_ts > 0 and age_seconds >= STALE_SECONDS else 'pending'
        abnormal = freshness == 'never_reported'
        status_text = '创建后超过24小时仍未上报' if abnormal else '待上报'

    visible_report_ts = parse_timestamp(display_report_time) or report_ts
    return {
        'reporting_freshness': freshness,
        'reporting_abnormal': abnormal,
        'reporting_status_text': status_text,
        'reporting_age_seconds': age_seconds,
        'last_report_at': format_timestamp(visible_report_ts),
    }
