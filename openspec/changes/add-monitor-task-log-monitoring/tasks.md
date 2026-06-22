## 1. Monitor task data model and backend foundation

- [x] 1.1 Add the `monitor_task` table definition to `data/sql/default.sql` with task metadata, install state, analysis state, timestamps, and grace seconds.
- [x] 1.2 Implement runtime schema ensure logic for `monitor_task` so upgraded installations create missing table/columns safely.
- [x] 1.3 Add monitor task helper functions for normalizing status values, timestamps, intervals, host metadata, and generated task ids.
- [x] 1.4 Implement `class/core/monitor_task_api.py` list, add, edit, delete, enable/disable, and install command APIs.
- [x] 1.5 Add `monitor_task_api` to the authenticated API whitelist in `route/__init__.py`.

## 2. Monitor task management page

- [x] 2.1 Add `monitor_task` to the page whitelist and add a sidebar entry in `route/templates/default/layout.html`.
- [x] 2.2 Create `route/templates/default/monitor_task.html` using the existing panel layout, search bar, toolbar, table, and operation-column style.
- [x] 2.3 Create `route/static/app/monitor_task.js` for loading/searching tasks, rendering status labels, and opening add/edit/delete/enable dialogs.
- [x] 2.4 Implement install command dialog and copy behavior using the server-generated command.
- [x] 2.5 Ensure the page labels task state as latest daily-report analysis result and displays `last_analyse_at` when present.

## 3. Public setup APIs and installation script

- [x] 3.1 Add `/pub/get_monitor_task_install_script` handler in `class/core/pub_api.py` to return the monitor task installation shell script.
- [x] 3.2 Add `/pub/register_monitor_task` handler that validates existing host ownership and creates or updates the matching monitor task.
- [x] 3.3 Add `/pub/update_monitor_task_install_status` handler that records `installed` or `failed` state with callback message and update time.
- [x] 3.4 Implement the client installation script with install/update actions, argument parsing, prerequisite checks, and clear failure handling.
- [x] 3.5 Make the setup script idempotently create log directories/files, local task config, monitor-task-specific filebeat input config, and `/usr/local/bin/jh-monitor-task-log` symlink.
- [x] 3.6 Ensure task log filebeat inputs live under an independent monitor task configuration path and are not written into existing host collection input files.
- [x] 3.7 Validate filebeat configuration and reload/restart filebeat when a task input is installed.

## 4. Standard task logging command

- [x] 4.1 Add the deployed `jh-monitor-task-log` wrapper command and Python helper under the client script assets.
- [x] 4.2 Implement argument validation for `--task-id`, `--status`, `--msg`, and `--run-at`.
- [x] 4.3 Write JSON Lines events containing task id, status, message, run time, and collector source to the configured task log path.
- [x] 4.4 Add local command-level validation or tests for default messages, invalid status handling, and JSON escaping.

## 5. Elasticsearch ingestion and queries

- [x] 5.1 Add `host-monitor-task-event` index/template definition with keyword/date mappings for task event fields.
- [x] 5.2 Extend ES init tooling to create or update the monitor task event index/template.
- [x] 5.3 Add query builder/service code for fetching the latest event by `task_id + host_id`, ordered by `run_at` with `@timestamp` fallback.
- [x] 5.4 Add focused query/service tests or validation scripts for latest-event found and no-event cases.

## 6. Daily report analysis integration

- [x] 6.1 Add monitor task loading and grouping by host to `scripts/report_analyser.py`.
- [x] 6.2 Implement task status classification using latest event status, `check_interval`, `grace_seconds`, and analysis time.
- [x] 6.3 Persist `last_status`, `last_msg`, `last_run_at`, and `last_analyse_at` back to `monitor_task` during daily report generation.
- [x] 6.4 Add structured monitor task results to single-host report documents and report data streams.
- [x] 6.5 Append monitor task errors to `error_tips` and monitor task warnings to orange `summary_tips` so existing overview aggregation includes them.
- [x] 6.6 Handle ES query failures without deleting task definitions and with clear analysis failure messages.

## 7. Report template updates

- [x] 7.1 Update `route/templates/report/host_panel_report.html` to render monitor task details when present.
- [x] 7.2 Update `route/templates/report/host_pve_report.html` to render monitor task details when present.
- [x] 7.3 Confirm overview report behavior needs no separate task section beyond existing abnormal/warning host summaries.

## 8. Validation and rollout checks

- [x] 8.1 Run `python3 -m py_compile` for changed Python modules and scripts.
- [x] 8.2 Add or run a focused monitor task report analysis validation script with normal, warning, error, overdue, and missing-log cases.
- [x] 8.3 Run ES init check for the task event index/template after mapping changes.
- [x] 8.4 Verify the management page loads, can create a task, and can copy a valid install command.
- [x] 8.5 Verify a client install dry run or controlled install creates the expected command, task-specific filebeat config, log path, and install status callback.
- [x] 8.6 Verify task-specific filebeat config remains isolated from existing host collection input files.
- [x] 8.7 Run the existing daily report persistence validation path with monitor task results included.
