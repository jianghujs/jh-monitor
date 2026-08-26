# ha-status-log-reporting Specification

## Purpose
TBD - created by archiving change add-ha-management. Update Purpose after archive.
## Requirements
### Requirement: Plugin SHALL report actual HA state
The plugin SHALL periodically report actual role and health state to cloud monitor when a cloud monitor URL is configured.

#### Scenario: Periodic state report succeeds
- **WHEN** the report interval elapses and cloud monitor URL is configured
- **THEN** the plugin sends actual role, online status, health status, health detail, latest switch run id, and report timestamp

#### Scenario: Cloud monitor does not respond
- **WHEN** state report or switch event report fails because cloud monitor does not respond
- **THEN** the plugin keeps the unacknowledged report queued and retries periodically

### Requirement: Switch logs SHALL be reported through API
The system SHALL transfer switch status and logs through APIs instead of filebeat or Elasticsearch.

#### Scenario: Plugin reports switch event
- **WHEN** a switch step starts, succeeds, warns, or fails
- **THEN** the plugin reports a switch event containing switch run id, source host, reporting host, collect method, phase, step, status, sequence, and log text

### Requirement: Cloud monitor SHALL store switch log files
The cloud monitor SHALL store each switch run log as a file and persist only status indexes in SQLite.

#### Scenario: Cloud monitor accepts switch event
- **WHEN** the cloud monitor accepts a switch event for a known switch run
- **THEN** it appends the event to `/www/server/jh-monitor/logs/ha_switch/YYYY-MM/<switch_run_id>.log` and updates SQLite status, current step, error summary, and log path

#### Scenario: Duplicate switch event is received
- **WHEN** the cloud monitor receives an event with an already processed event id or source-host sequence
- **THEN** it treats the event as idempotent and SHALL NOT append duplicate log content

### Requirement: Cloud monitor SHALL display logs by source host
The cloud monitor SHALL separate switch logs by the host that originally produced them.

#### Scenario: Operator views switch logs
- **WHEN** the operator opens switch logs for an HA pair
- **THEN** the page displays per-host logs using `origin_host_id` and also provides the complete log file view

