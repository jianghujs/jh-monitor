#!/usr/bin/env python3
# coding: utf-8

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'class', 'plugin'))

from reporting_freshness import derive_reporting_freshness


def main():
    reference = 200000

    fresh = derive_reporting_freshness(reference, reference - 86399)
    assert fresh['reporting_freshness'] == 'fresh', fresh
    assert not fresh['reporting_abnormal'], fresh
    assert fresh['reporting_age_seconds'] == 86399, fresh

    stale = derive_reporting_freshness(reference, reference - 86400)
    assert stale['reporting_freshness'] == 'stale', stale
    assert stale['reporting_abnormal'], stale
    assert stale['reporting_status_text'] == '超过24小时未上报', stale

    pending = derive_reporting_freshness(reference, None, reference - 86399)
    assert pending['reporting_freshness'] == 'pending', pending
    assert pending['reporting_status_text'] == '待上报', pending

    never = derive_reporting_freshness(reference, None, reference - 86400)
    assert never['reporting_freshness'] == 'never_reported', never
    assert never['reporting_abnormal'], never

    invalid = derive_reporting_freshness(reference, 'not-a-time', 'also-invalid')
    assert invalid['reporting_freshness'] == 'pending', invalid
    assert invalid['reporting_age_seconds'] == 0, invalid

    future = derive_reporting_freshness(reference, reference + 60)
    assert future['reporting_freshness'] == 'fresh', future
    assert future['reporting_age_seconds'] == 0, future

    recovered = derive_reporting_freshness(reference, reference - 10, reference - 200000)
    assert recovered['reporting_freshness'] == 'fresh', recovered
    assert not recovered['reporting_abnormal'], recovered

    iso = derive_reporting_freshness('2026-10-31T12:00:00+08:00', '2026-10-30T12:00:00+08:00')
    assert iso['reporting_freshness'] == 'stale', iso
    assert iso['last_report_at'] == '2026-10-30 12:00:00', iso

    print('reporting freshness: ok')


if __name__ == '__main__':
    main()
