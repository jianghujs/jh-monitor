## ADDED Requirements

### Requirement: Plugin-managed HA alert notification
The ha_manager plugin SHALL be responsible for detecting and sending HA alert notifications, while Jianghu Monitor SHALL only display, store, and summarize alert notification events.

#### Scenario: Plugin sends HA alert notification
- **WHEN** the ha_manager plugin detects a HA alert and the local plugin is the active notifier for the pair
- **THEN** the plugin SHALL send the notification through the Jianghu Panel notification channel
- **AND** Jianghu Monitor SHALL NOT send a duplicate email for the same HA alert

#### Scenario: Monitor displays plugin notification event
- **WHEN** the plugin reports an alert notification event to Jianghu Monitor
- **THEN** Jianghu Monitor SHALL store and display the event in HA management views and reports

### Requirement: Primary notifier ownership
Each HA pair SHALL have one configured `primary_notifier_host_id` that determines the primary plugin responsible for HA alert notifications.

#### Scenario: Primary notifier is reachable
- **WHEN** the local plugin is not the primary notifier and the primary notifier is reachable
- **THEN** the local plugin SHALL NOT send ordinary HA alert notifications for the pair

#### Scenario: Local plugin is primary notifier
- **WHEN** the local plugin host id equals `primary_notifier_host_id`
- **THEN** the local plugin SHALL evaluate alert state changes and send HA alert or recovery notifications when required

#### Scenario: Notifier configuration is inconsistent
- **WHEN** the local plugin detects that its `primary_notifier_host_id` differs from the peer plugin configuration
- **THEN** the plugin SHALL mark the notifier configuration as abnormal in self-check or overview state
- **AND** the plugin SHALL record the mismatch in the interaction log

### Requirement: Backup notifier takeover
The backup notifier plugin SHALL take over HA alert notifications only after the primary notifier remains unreachable for a configured threshold.

#### Scenario: Primary notifier becomes unreachable
- **WHEN** the local plugin is not the primary notifier and it cannot reach the primary notifier for the configured number of consecutive checks
- **THEN** the local plugin SHALL enter backup takeover mode
- **AND** the local plugin SHALL be allowed to send HA alert notifications for the pair

#### Scenario: Primary notifier recovers
- **WHEN** the backup notifier is in takeover mode and the primary notifier becomes reachable for the configured number of consecutive checks
- **THEN** the backup notifier SHALL exit takeover mode
- **AND** ordinary HA alert notifications SHALL return to the primary notifier

### Requirement: Pair-level abnormal notification state
The plugin SHALL maintain a local pair-level abnormal state and use it to send one alert notification when the HA pair enters any abnormal state and one recovery notification only after all active alerts recover.

#### Scenario: Pair enters abnormal state
- **WHEN** the previous active alert set is empty and the current active alert set is not empty
- **THEN** the active notifier SHALL send one HA alert notification containing the current alert summary
- **AND** the plugin SHALL save the pair-level abnormal state and current active alert details after notification handling

#### Scenario: New alert appears during existing abnormal state
- **WHEN** the previous active alert set is not empty and the current active alert set contains one or more new alert keys
- **THEN** the plugin SHALL update the saved active alert details
- **AND** the plugin SHALL NOT send another HA alert notification

#### Scenario: Some alerts recover but others remain active
- **WHEN** the previous active alert set is not empty and the current active alert set is still not empty
- **THEN** the plugin SHALL update the saved active alert details
- **AND** the plugin SHALL NOT send an HA recovery notification

#### Scenario: All alerts recover
- **WHEN** the previous active alert set is not empty and the current active alert set is empty
- **THEN** the active notifier SHALL send one HA recovery notification summarizing the recovered abnormal period
- **AND** the plugin SHALL clear the saved pair-level abnormal state

#### Scenario: Notification send fails
- **WHEN** an HA alert notification fails to send
- **THEN** the plugin SHALL record the failure
- **AND** the plugin SHALL avoid marking the pair-level abnormal state as successfully notified in a way that would suppress a later retry

### Requirement: Standard HA alert keys
The plugin SHALL generate stable alert keys from pair id, alert type, and alert subject so that repeated checks identify the same active alert consistently.

#### Scenario: Host unreachable alert key
- **WHEN** a host in the HA pair is unreachable
- **THEN** the alert key SHALL include the pair id, `host_unreachable`, and the unreachable host id

#### Scenario: Pair-level alert key
- **WHEN** the HA pair has a pair-level alert such as double-master or no-master
- **THEN** the alert key SHALL include the pair id and the pair-level alert type without depending on the detecting host

### Requirement: Default HA alert scope
The plugin SHALL notify by default only for high-value HA alerts and SHALL NOT default to emailing every self-check warning.

#### Scenario: High-value HA alert detected
- **WHEN** the plugin detects host unreachable, double-master, no-master, degraded master, recovery guard, or switch-stuck state
- **THEN** the active notifier SHALL consider the alert eligible for notification

#### Scenario: Ordinary self-check warning detected
- **WHEN** the plugin detects an ordinary self-check warning and key self-check notification is not enabled
- **THEN** the plugin SHALL display or report the warning but SHALL NOT send an HA alert email for it

### Requirement: Alert notification events reported to monitor
The plugin SHALL report alert notification lifecycle events to Jianghu Monitor for display and daily report aggregation.

#### Scenario: Alert notification sent
- **WHEN** the plugin sends an HA alert notification or HA recovery notification
- **THEN** it SHALL report an event containing pair id, alert key, alert type, level, status, title, message, and sender host id to Jianghu Monitor

#### Scenario: Alert notification skipped or failed
- **WHEN** the plugin skips notification because it is not the active notifier or notification sending fails
- **THEN** it SHALL report or log enough information for operators to understand why no notification was sent

### Requirement: Plugin scheduled alert check
The ha_manager plugin SHALL expose a scheduled alert check entrypoint that Jianghu Panel task process can run without opening the plugin UI.

#### Scenario: Scheduled alert check runs
- **WHEN** the plugin is installed and its scheduled tasks are enabled
- **THEN** Jianghu Panel task process SHALL periodically execute the plugin alert check entrypoint
- **AND** alert notification behavior SHALL work even when the plugin page is not open
