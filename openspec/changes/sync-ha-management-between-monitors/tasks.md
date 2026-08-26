## 1. Schema and Configuration

- [x] 1.1 Add stable local Jianghu Monitor identity fields `monitor_id` and `monitor_name`.
- [x] 1.2 Add cloud monitor synchronization configuration list schema with `sync_id`, `sync_name`, `sync_type`, `peer_monitor_url`, `peer_monitor_id`, `peer_monitor_name`, `sync_secret`, `enabled`, `last_sync_at`, and `last_error`.
- [x] 1.3 Add create, update, delete, enable/disable, and handshake-test APIs for synchronization configurations.
- [x] 1.4 Add generic monitor sync schema with `sync_type` for synchronization events, applied-event idempotency, per-configuration/per-type cursors, and synchronization status.
- [x] 1.5 Extend `ha_switch_run` with origin/execution monitor fields, claim fields, synchronization status, and conflict/waiting-executor state support.
- [x] 1.6 Add schema migration compatibility so existing `ha_*` tables and switch runs continue to load without manual migration.

## 2. Sync Event Recording

- [x] 2.1 Implement a shared typed monitor sync event writer that creates globally unique events with `sync_type`, source monitor, event type, object key, payload, and sequence metadata.
- [x] 2.2 Emit `sync_type=ha_management` events when `/pub/ha_report_state` updates `ha_pair` or `ha_host_state`.
- [x] 2.3 Emit `sync_type=ha_management` events when `/ha/request_switch` creates or updates a `ha_switch_run`.
- [x] 2.4 Emit `sync_type=ha_management` events when `/pub/ha_report_switch_event` accepts a new switch event.
- [x] 2.5 Emit `sync_type=ha_management` events when `/pub/ha_ack_switch_phase` advances switch run status.
- [x] 2.6 Emit `sync_type=ha_management` events when `/pub/ha_report_alert_event` accepts a new alert event.

## 3. Monitor-to-Monitor APIs

- [x] 3.1 Add signed `/pub/ha_monitor_sync_handshake` API to exchange monitor identity and sync version.
- [x] 3.2 Add signed `/pub/ha_monitor_sync_pull` API to return peer sync events after a requested cursor.
- [x] 3.3 Add signed `/pub/ha_monitor_sync_ack` API to record peer-applied cursor acknowledgement.
- [x] 3.4 Add nonce, timestamp, body hash, and signature validation for monitor-to-monitor sync APIs.
- [x] 3.5 Add response payloads that include sync status, cursor, monitor identity, and clear failure messages.

## 4. Sync Pull and Apply Job

- [x] 4.1 Add a scheduled monitor sync task that iterates enabled synchronization configurations and applies `ha_management` events in the first version.
- [x] 4.2 Implement pull loop that reads the stored peer cursor and fetches new events in bounded batches.
- [x] 4.3 Implement idempotent event application for HA pair and host state events.
- [x] 4.4 Implement idempotent event application for switch run, switch event, and phase acknowledgement events.
- [x] 4.5 Implement idempotent event application for alert events.
- [x] 4.6 Advance peer cursor only after all events in the batch are applied successfully.
- [x] 4.7 Write synchronization logs and last success/failure status for operations and troubleshooting.

## 5. State Merge and Conflict Rules

- [x] 5.1 Implement host state merge rules using `last_report_at` freshness and `collect_method=local` trust priority.
- [x] 5.2 Preserve `report_batch_id` behavior so existing `_normalizePair()` display logic can still group reported host states.
- [x] 5.3 Ensure stale synchronized failure placeholders do not overwrite newer successful local or synchronized state.
- [x] 5.4 Add active switch conflict detection per `pair_id` during synchronized switch task application.
- [x] 5.5 Mark conflicting or non-executable synchronized tasks as non-dispatchable and expose an operator-readable reason.

## 6. Cross-Monitor Switch Dispatch

- [x] 6.1 Add execution monitor selection when creating switch tasks from the HA management page when sync type is `ha_management` and HA sync is enabled.
- [x] 6.2 Allow task creation on monitor A with `origin_monitor_id=A` and `execution_monitor_id=B` when only monitor B has an available executor.
- [x] 6.3 Update `/pub/ha_pull_desired_state` so only the configured execution monitor dispatches executable phase information.
- [x] 6.4 Add claim token and claimed host handling to avoid duplicate plugin execution for the same synchronized switch phase.
- [x] 6.5 Synchronize remote execution logs, phase status, final status, and errors back to the origin monitor.

## 7. UI and Reporting

- [x] 7.1 Add settings-page cloud monitor synchronization list UI with add, edit, delete, enable/disable, sync type `ha_management`, peer monitor URL, monitor names, shared secret, and handshake test.
- [x] 7.2 Show synchronized source, latest sync time, origin monitor, execution monitor, and non-dispatch reason in HA management detail or switch dialogs.
- [x] 7.3 Show synchronization failure reason and last successful sync time in a visible troubleshooting location.
- [x] 7.4 Keep daily report generation reading local `ha_*` tables and verify synchronized HA state appears in HA overview, abnormal HA summary, and warning HA summary.

## 8. Validation and Documentation

- [x] 8.1 Add focused backend checks for sync signature validation, duplicate event handling, cursor advancement, and cursor retention on failure.
- [x] 8.2 Add focused checks for host state merge priority and stale placeholder handling.
- [x] 8.3 Add focused checks for cross-monitor switch task routing and duplicate dispatch protection.
- [x] 8.4 Validate syntax for changed Python modules with `python3 -m py_compile`.
- [x] 8.5 Update HA implementation documentation with monitor-to-monitor sync data flow, tables, logs, and troubleshooting commands.
- [x] 8.6 Document operational rollout and rollback steps for enabling HA synchronization between two Jianghu Monitor instances.
