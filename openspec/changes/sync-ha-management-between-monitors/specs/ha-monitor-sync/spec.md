## ADDED Requirements

### Requirement: Configure HA monitor synchronization

The system SHALL allow an operator to manage a synchronization configuration list in the settings page. Each synchronization configuration SHALL include stable local monitor identity, synchronization type, peer monitor URL, shared secret, enable switch, and handshake status.

#### Scenario: Save synchronization configuration
- **WHEN** an operator adds a synchronization configuration with peer monitor URL, shared secret, enable switch, and synchronization type `ha_management` in the settings page
- **THEN** the system MUST persist the configuration in the synchronization list and generate a stable local `monitor_id` if one does not already exist

#### Scenario: Edit synchronization configuration
- **WHEN** an operator edits an existing synchronization configuration
- **THEN** the system MUST update that configuration without changing unrelated synchronization configurations

#### Scenario: Delete synchronization configuration
- **WHEN** an operator deletes a synchronization configuration that is not actively applying events
- **THEN** the system MUST remove or disable that configuration and MUST NOT pull new events for it

#### Scenario: Disable one synchronization configuration
- **WHEN** an operator disables one synchronization configuration while other configurations remain enabled
- **THEN** the system MUST stop pulling or applying events for the disabled configuration and MUST continue processing enabled configurations

#### Scenario: HA management synchronization type
- **WHEN** an operator sets synchronization type to `ha_management`
- **THEN** the system MUST synchronize HA pair, host state, switch run, switch log, and alert event data

#### Scenario: Synchronization disabled
- **WHEN** a synchronization configuration is disabled
- **THEN** the system MUST NOT pull or apply synchronization events from that peer monitor

### Requirement: Exchange monitor identity securely

The system SHALL provide a signed handshake between two Jianghu Monitor instances to verify the peer and exchange monitor identity.

#### Scenario: Successful handshake
- **WHEN** the local monitor sends a valid signed handshake request to the peer monitor
- **THEN** the peer monitor MUST return its `monitor_id`, monitor name, and supported HA sync version

#### Scenario: Invalid signature
- **WHEN** a handshake request has an invalid signature, expired timestamp, or reused nonce
- **THEN** the peer monitor MUST reject the request and MUST NOT update synchronization state

### Requirement: Record typed monitor synchronization events

The system SHALL record typed business-level synchronization events when data changes need to be propagated to a peer monitor. The first supported synchronization type SHALL be `ha_management` for HA management data, and the event schema MUST reserve `sync_type` for future data domains.

#### Scenario: Host state report creates sync event
- **WHEN** `/pub/ha_report_state` updates `ha_host_state` or `ha_pair` data
- **THEN** the system MUST create synchronization events with `sync_type=ha_management` for the changed HA state data

#### Scenario: Switch task creates sync event
- **WHEN** `/ha/request_switch` creates a HA switch run
- **THEN** the system MUST create a synchronization event with `sync_type=ha_management` containing the switch task and execution ownership metadata

#### Scenario: Switch log creates sync event
- **WHEN** `/pub/ha_report_switch_event` accepts a new non-duplicate switch event
- **THEN** the system MUST create a synchronization event with `sync_type=ha_management` for that switch log event

#### Scenario: Alert event creates sync event
- **WHEN** `/pub/ha_report_alert_event` accepts a new non-duplicate alert event
- **THEN** the system MUST create a synchronization event with `sync_type=ha_management` for that alert event

### Requirement: Pull and apply typed monitor synchronization events

The system SHALL periodically pull unapplied synchronization events from the peer monitor by synchronization configuration and `sync_type`, then apply `ha_management` events idempotently to local HA tables.

#### Scenario: Pull new events
- **WHEN** the local monitor has enabled synchronization configurations
- **THEN** the local monitor MUST pull events newer than each enabled configuration's stored peer synchronization cursor

#### Scenario: Apply event once
- **WHEN** the local monitor receives an event whose `event_id` has already been applied
- **THEN** the local monitor MUST ignore the duplicate event and keep the existing local data unchanged

#### Scenario: Advance cursor after success
- **WHEN** the local monitor successfully applies all events returned by a pull request
- **THEN** the local monitor MUST advance its synchronization cursor for that peer monitor

#### Scenario: Keep cursor after failure
- **WHEN** applying an event fails
- **THEN** the local monitor MUST keep the previous cursor and record the failure in the HA sync log

### Requirement: Merge synchronized host states

The system SHALL merge synchronized `ha_host_state` data by freshness and source trust so that each monitor can display the latest known status for both HA hosts.

#### Scenario: Newer host state wins
- **WHEN** a synchronized host state has the same `pair_id` and `host_id` as a local record but a newer `last_report_at`
- **THEN** the system MUST update the local record with the synchronized state

#### Scenario: Local collection is preferred
- **WHEN** two host states have the same `pair_id`, `host_id`, and `last_report_at`, but one has `collect_method=local` and the other has `collect_method=ssh_peer`
- **THEN** the system MUST prefer the `local` state for display and status calculation

#### Scenario: Peer status fills local outage gap
- **WHEN** a local business host stops reporting to its local monitor but the peer monitor synchronizes a newer state for the same HA pair
- **THEN** the local monitor MUST display the synchronized HA state and use it in HA status calculation

### Requirement: Route cross-monitor switch tasks to one execution monitor

The system SHALL assign every cross-monitor HA switch task to exactly one execution monitor and only that monitor may dispatch executable phases to plugins.

#### Scenario: Local monitor cannot execute target switch
- **WHEN** an operator creates a switch task on monitor A, synchronization type is `ha_management`, and monitor A has no available local or `ssh_peer` executor for the target phase, but monitor B has an available executor
- **THEN** monitor A MUST create the switch task with `origin_monitor_id=A` and `execution_monitor_id=B`

#### Scenario: Execution monitor dispatches task
- **WHEN** monitor B applies a synchronized switch task whose `execution_monitor_id` equals monitor B's `monitor_id`
- **THEN** monitor B MUST allow `/pub/ha_pull_desired_state` to return executable phase information to the eligible plugin host

#### Scenario: Non-execution monitor does not dispatch task
- **WHEN** monitor A has a switch task whose `execution_monitor_id` does not equal monitor A's `monitor_id`
- **THEN** monitor A MUST NOT return executable phase information for that task from `/pub/ha_pull_desired_state`

### Requirement: Prevent duplicate switch execution

The system SHALL prevent two Jianghu Monitor instances or two plugin hosts from executing the same HA switch task concurrently.

#### Scenario: Active task conflict
- **WHEN** a monitor applies a synchronized switch task for a `pair_id` that already has an unfinished local switch task
- **THEN** the system MUST mark the later task as conflicted or waiting for operator action and MUST NOT dispatch it to a plugin

#### Scenario: Claimed task remains owned
- **WHEN** a plugin host has already claimed a synchronized switch task with a valid claim token
- **THEN** the system MUST NOT issue a second claim for the same switch phase to another plugin host

#### Scenario: Duplicate log event ignored
- **WHEN** the same switch log event is received more than once through direct report or synchronization
- **THEN** the system MUST store the event once using `event_id` or `switch_run_id + origin_host_id + seq` idempotency

### Requirement: Synchronize switch progress and logs back to origin monitor

The system SHALL synchronize switch phase progress, log events, acknowledgements, failures, and final status back to the monitor where the task was created.

#### Scenario: Remote execution log visible at origin
- **WHEN** monitor B executes a switch task created on monitor A and receives switch log events from the plugin
- **THEN** monitor A MUST receive synchronized log events and display them in the original switch task log

#### Scenario: Remote phase success advances origin state
- **WHEN** monitor B receives a successful phase acknowledgement for a task created on monitor A
- **THEN** monitor A MUST receive the synchronized run update and show the same switch phase status

#### Scenario: Final status synchronized
- **WHEN** monitor B marks a synchronized switch task as `success`, `waiting_retry`, `cancelled`, or `conflict`
- **THEN** monitor A MUST apply the same final status to its local copy of the switch task

### Requirement: Show synchronization source and task ownership in HA management UI

The system SHALL show enough synchronization metadata in the HA management page for operators to understand where data came from and where a switch task will execute.

#### Scenario: Synchronized host state shown
- **WHEN** a host state displayed on the HA management page was last updated through peer monitor synchronization
- **THEN** the page MUST indicate that the state is synchronized from the peer monitor and show the latest synchronization time

#### Scenario: Cross-monitor task confirmation
- **WHEN** an operator creates a switch task that will execute on the peer monitor
- **THEN** the confirmation view MUST show the origin monitor, execution monitor, and expected executor host when known

#### Scenario: Synchronization failure visible
- **WHEN** HA synchronization fails for the peer monitor
- **THEN** the HA management page or configuration page MUST expose the latest failure reason and last successful synchronization time

### Requirement: Preserve daily report behavior with synchronized HA data

The system SHALL keep the server daily report reading local HA tables while benefiting from synchronized HA state.

#### Scenario: Daily report includes synchronized HA status
- **WHEN** HA synchronization has applied peer monitor state into the local `ha_*` tables and `ha_enabled=true`
- **THEN** the daily report MUST include the synchronized HA status in the HA overview, abnormal HA summary, and warning HA summary

#### Scenario: HA synchronization failure does not block report
- **WHEN** HA synchronization is unavailable or failing
- **THEN** the daily report MUST still generate using the latest local HA data and MUST NOT fail solely because HA synchronization failed
