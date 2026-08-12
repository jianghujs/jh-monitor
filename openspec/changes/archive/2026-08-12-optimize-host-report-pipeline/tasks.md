## 1. Report configuration foundation

- [x] 1.1 Add the host report configuration section to `route/templates/default/config.html` and wire the related front-end actions for Elasticsearch settings and threshold fields.
- [x] 1.2 Implement backend read/save APIs for report thresholds and Elasticsearch settings, including default `{}` initialization and atomic JSON writes for `data/report_config.json` and `data/es.json`.
- [x] 1.3 Add payload validation and Elasticsearch connectivity checking so invalid settings are rejected before persistence.

## 2. Client collection pipeline

- [x] 2.1 Implement the local report collector script that emits normalized host system status JSON into `/home/${USERNAME}/jh-monitor-scripts/data/`.
- [x] 2.2 Update `scripts/client/install/debian.sh` to deploy the collector, create data/log directories, register `/etc/cron.d/jh-monitor-report-collector`, and execute the collector once after install/update.
- [x] 2.3 Adjust `scripts/client/install.sh` and related install assets so collector deployment remains compatible with the existing `ansible_user` directory conventions while running the collector from `root` cron.
- [x] 2.4 Extend filebeat configuration and install/update flow to ingest collector output, xtrabackup histories, and `backup.log` into the four raw Elasticsearch indices.

## 3. Elasticsearch report data modeling

- [x] 3.1 Define and create the required raw/report index mappings for `host-system-status`, `host-xtrabackup`, `host-xtrabackup-inc`, `host-backup`, `host-report-single`, and `host-report-overview`.
- [x] 3.2 Standardize shared document fields such as `host_id`, `host_name`, `host_ip`, report dates, timestamps, validation state, and delivery metadata across the pipeline.

## 4. Daily report analysis

- [x] 4.1 Add a daily analysis task in `task.py` that loads the target report window from Elasticsearch and groups raw data by host and date.
- [x] 4.2 Port the anomaly and summary rules from `/www/server/jh-panel/scripts/report.py` so the analyzer produces `summary_tips`, `error_tips`, and structured system/backup/business detail sections.
- [x] 4.3 Render and persist single-host reports into `host-report-single`, including HTML content, completeness validation results, and resend-ready metadata.
- [x] 4.4 Aggregate the same-day single-host outputs into the overview report and persist it into `host-report-overview` with host totals and abnormal host summaries.

## 5. Daily report delivery

- [x] 5.1 Add a delivery task in `task.py` that reads only validated same-day report documents from Elasticsearch instead of fetching live host data.
- [x] 5.2 Reuse the existing email notification path to send the overview report every day and only the abnormal single-host reports.
- [x] 5.3 Persist per-report delivery status, recipients, failure reason, and retry count so skipped, failed, and successful sends can be audited and retried.

## 6. Validation and rollout safeguards

- [x] 6.1 Add install/runtime checks that confirm the collector cron, first-run output, and filebeat inputs are present after deployment.
- [x] 6.2 Add analysis and delivery preflight validation for missing raw data, empty HTML, invalid report dates, and incomplete report documents.
- [x] 6.3 Document or script the rollout sequence for enabling configuration, collection, analysis, and delivery with a defined fallback to the legacy send path during cutover.
