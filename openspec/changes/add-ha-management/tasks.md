## 1. Cloud Monitor UI Foundation

- [x] 1.1 Add `ha_management` to page routing whitelist and sidebar navigation.
- [x] 1.2 Create the HA management list page with compact table layout, search, summary counters, and row actions; do not include an add relationship button.
- [x] 1.3 Implement HA group detail dialog with tabs for group overview, host list, health status, switch status, and switch logs.
- [x] 1.4 Ensure host list, health status, switch status, and switch logs render both HA hosts separately.
- [x] 1.5 Add UI states for normal, warning, switching, danger, empty list, and simulated refresh.

## 2. Cloud Monitor Data Model and APIs

- [x] 2.1 Add SQLite schema and migration/ensure logic for HA pair, HA host state, HA switch run, and HA callback records.
- [x] 2.2 Implement authenticated HA management APIs for list, detail, update pair config, request switch, retry switch, cancel switch, read log, and callback config.
- [x] 2.3 Implement switch run creation with desired master update, options persistence, status initialization, and log path allocation under `/www/server/jh-monitor/logs/ha_switch/`.
- [x] 2.4 Implement status derivation for normal, warning, switching, danger, unknown, drifted, double-master, and double-standby cases.
- [x] 2.5 Implement log file read by offset for the detail and log views.

## 3. Signed Plugin API

- [x] 3.1 Add signed public API middleware/helper for plugin requests using timestamp, nonce, body hash, and HMAC signature.
- [x] 3.2 Implement `/pub/ha_register_pair` for plugins to register or update HA relationship name, local host information, and peer host information.
- [x] 3.3 Implement `/pub/ha_pull_desired_state` for plugin polling and phase assignment.
- [x] 3.4 Implement `/pub/ha_report_state` for actual role, online status, health status, collection status, and health details.
- [x] 3.5 Implement `/pub/ha_report_switch_event` for switch status and log event reporting with idempotency.
- [x] 3.6 Implement `/pub/ha_ack_switch_phase` for claiming, completing, and failing switch phases.
- [x] 3.7 Add nonce replay protection and clear error responses for invalid signatures, stale timestamps, unknown pair ids, and unknown host ids.

## 4. Cloud Monitor Log Handling

- [x] 4.1 Create log directory management for `/www/server/jh-monitor/logs/ha_switch/YYYY-MM/`.
- [x] 4.2 Append switch events to log files using readable operator format.
- [x] 4.3 Store only switch status, current phase, current step, last error, step summary, and log path in SQLite.
- [x] 4.4 Deduplicate log events using `event_id` or `origin_host_id + seq`.
- [x] 4.5 Expose per-host logs grouped by `origin_host_id` while preserving the full log file view.

## 5. Panel Plugin UI and Configuration

- [x] 5.1 Create `/www/server/jh-panel/plugins/ha_manager/` plugin structure with metadata, install script, index page, and JS.
- [x] 5.2 Implement plugin overview tab showing local role, desired role, peer binding, cloud monitor report state, health summary, and local switch action.
- [x] 5.3 Implement peer binding tab with peer public IP, SSH port, SSH user, peer public key, SSH test, and save binding action.
- [x] 5.4 Ensure `pair_id` is generated or received internally and is not exposed as a manual UI input.
- [x] 5.5 Implement cloud monitor tab with HA relationship name, URL, poll interval, report interval, test, save/register, and clear actions; empty URL disables registration and upload.
- [x] 5.6 Implement plugin health and switch log tabs consistent with Jianghu panel plugin style.

## 6. Plugin Local State and Peer Aggregation

- [x] 6.1 Persist local plugin config, local role, peer binding, cloud monitor config, and API secret safely.
- [x] 6.2 Write local HA state snapshot to `/www/server/ha_manager/data/state.json`.
- [x] 6.3 Write local switch logs to `/www/server/ha_manager/logs/switch/<switch_run_id>.log` with monotonically increasing sequence numbers.
- [x] 6.4 Implement SSH peer collection for peer state snapshot, switch status, and log sequence metadata.
- [x] 6.5 Implement incremental peer log collection into `/www/server/ha_manager/logs/peer/<peer_host_id>/<switch_run_id>.log`.
- [x] 6.6 Aggregate local and peer state/logs into cloud monitor reports with `origin_host_id`, `report_host_id`, `collect_method`, and `collect_status`.
- [x] 6.7 Distinguish SSH collection failure from confirmed peer offline in reported state.

## 7. Switch Execution

- [x] 7.1 Wrap the offline flow from `switch__generate_offline.sh` into a non-interactive plugin executor.
- [x] 7.2 Wrap the online flow from `switch__generate_online.sh` into a non-interactive plugin executor.
- [x] 7.3 Map online switch options for local IP, remote IP, SSH port, checksum, file sync, restore settings, xtrabackup incremental restore, and MySQL promotion.
- [x] 7.4 Add local switch lock to prevent concurrent switch execution on the same host.
- [x] 7.5 Report every major switch step start, success, warning, and failure through the switch event API.
- [x] 7.6 Implement local plugin homepage switch flow with confirmation modal and log view transition.

## 8. Alerts, Retry, and Callback

- [x] 8.1 Implement red danger alerts for confirmed primary offline, double master, double standby, switch failure, state drift, and plugin lost contact.
- [x] 8.2 Implement orange warnings for MySQL, rsync/lsyncd, OpenResty, checksum difference, non-critical step failure, callback failure, and SSH collection failure.
- [x] 8.3 Implement retry controls for failed switch phases and failed callbacks.
- [x] 8.4 Implement callback configuration and callback execution after actual master switch is confirmed.
- [x] 8.5 Record callback attempts and failures in switch state and switch log files.

## 9. Validation

- [x] 9.1 Run `python3 -m py_compile` for changed cloud monitor Python modules.
- [x] 9.2 Run `node --check` for changed cloud monitor and plugin JavaScript files.
- [x] 9.3 Validate plugin metadata JSON and install shell syntax.
- [x] 9.4 Add or run focused tests for HMAC validation, nonce replay, log deduplication, and switch status derivation.
- [x] 9.5 Validate UI flows for list, detail tabs, switch dialog, per-host health, per-host switch status, and per-host logs.
- [x] 9.6 Validate dual-datacenter simulation where each plugin reports local plus SSH-collected peer data to its own cloud monitor.
