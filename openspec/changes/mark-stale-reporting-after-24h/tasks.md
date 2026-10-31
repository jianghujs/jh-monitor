## 1. Reporting freshness foundation

- [x] 1.1 Add a reusable backend helper that derives `fresh`, `stale`, `pending`, and `never_reported` from reference time, latest report/receive time, and creation/registration time using the 86,400-second boundary.
- [x] 1.2 Make the helper return structured display fields including abnormal flag, normalized latest report time, non-negative age seconds, and a stable Chinese status reason.
- [x] 1.3 Add focused tests for 86,399/86,400-second boundaries, missing and invalid times, never-reported grace periods, future timestamps, and recovery after a new report.

## 2. Host management integration

- [x] 2.1 Extend the latest host status mapping/service result with reporting freshness while preserving the raw `host_status`, last status document, and Elasticsearch error distinction.
- [x] 2.2 Update the host list API to derive never-reported state from the host creation time and return the structured freshness fields for every row.
- [x] 2.3 Update the host management page so reporting abnormality takes precedence over stale Running/Stopped values, pending hosts display `待上报`, and the latest report time remains visible.
- [x] 2.4 Add host-list tests covering fresh running, stale running, stale stopped, pending first report, expired first-report grace period, recovery, and Elasticsearch-unavailable behavior.

## 3. HA management integration

- [x] 3.1 Add per-host reporting freshness derivation to HA normalization using server receive time first, reported time as fallback, and registration/add time for the first-report grace period.
- [x] 3.2 Refactor HA pair status derivation to accept a reference time and add a danger reason for every stale or expired never-reported host without mutating stored online or health fields.
- [x] 3.3 Make HA list and detail APIs dynamically return derived pair status plus structured per-host freshness instead of trusting only the stored `ha_pair.status`.
- [x] 3.4 Extend read-only HA relationship snapshots with the same freshness fields and pair danger semantics without initializing or mutating the HA schema.
- [x] 3.5 Update the HA management list and detail views to show per-host reporting abnormality, latest report time, and the affected machine in the relationship-level error text.
- [x] 3.6 Add HA tests for one-sided stale reporting, both hosts stale, pending registration, expired never-reported registration, existing offline/danger/warning precedence, switching precedence, and recovery.

## 4. Daily report integration

- [x] 4.1 Make daily host analysis resolve the latest status at or before the report-window end, including a pre-window lookup when the 24-hour window itself contains no status document.
- [x] 4.2 Add `reporting_stale_24h` and `never_reported_24h` validation/error summaries while retaining the existing 15-minute completeness rule for shorter gaps.
- [x] 4.3 Update overview host counts and abnormal summaries so 24-hour reporting abnormalities are included once with a clear reason and latest report time.
- [x] 4.4 Evaluate HA overview freshness with the report-window end as reference time and include each affected HA host in the abnormal HA summary.
- [x] 4.5 Update report templates only where needed to render the new structured reason without duplicating existing validation messages.
- [x] 4.6 Add report tests for current and historical windows, stale data older than the query window, never-reported hosts, 15-minute-only incompleteness, one-sided stale HA, and post-window data exclusion.

## 5. Compatibility and verification

- [x] 5.1 Verify existing host and HA API fields remain backward compatible and that no Elasticsearch mapping or SQLite migration is required.
- [x] 5.2 Run Python syntax checks for every modified backend/report module and JavaScript syntax checks for modified host/HA page scripts.
- [x] 5.3 Run the new focused tests plus `python3 test/test_report_es_persistence.py --host-id <HOST_ID>` against an available test host, documenting any environment-dependent skips.
- [x] 5.4 Bump static asset query versions in affected templates, restart with `jhm 1 -y`, and verify the host page, HA page, API snapshots, generated daily report, and gunicorn restart time.
