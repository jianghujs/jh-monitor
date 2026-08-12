## ADDED Requirements

### Requirement: Standard task log command
The system SHALL provide a standard command for business scripts to append monitor task execution results as JSON Lines.

#### Scenario: Business script writes success without message
- **WHEN** a business script runs `jh-monitor-task-log --task-id <task_id>`
- **THEN** the command appends a JSON line for the task with status `success`, default message `成功`, and a run time

#### Scenario: Business script writes explicit status and message
- **WHEN** a business script runs `jh-monitor-task-log --task-id <task_id> --status warning --msg <message>`
- **THEN** the command appends a JSON line containing the task id, status, message, and run time

#### Scenario: Business script uses invalid status
- **WHEN** a business script passes a status outside `success`, `warning`, and `error`
- **THEN** the command exits with failure and does not append an invalid JSON line

### Requirement: Task event document format
The task event log format SHALL include the fields needed for ES ingestion and report analysis.

#### Scenario: Command writes event
- **WHEN** `jh-monitor-task-log` appends a task event
- **THEN** the JSON line contains `task_id`, `status`, `msg`, `run_at`, and `collector_source`

#### Scenario: Filebeat enriches event
- **WHEN** filebeat ingests a task event log line
- **THEN** the ES document includes `task_id`, `task_name`, `host_id`, `host_ip` when available, `log_path`, `status`, `msg`, `run_at`, `collector_source`, and `@timestamp`

### Requirement: Shared task event index
The system SHALL ingest all monitor task events into the shared Elasticsearch index `host-monitor-task-event`.

#### Scenario: Task event is collected
- **WHEN** filebeat collects a valid monitor task JSON line
- **THEN** the event is indexed into `host-monitor-task-event` rather than a per-task index

### Requirement: Task event index mapping
The system SHALL define Elasticsearch mappings suitable for filtering and time sorting task events.

#### Scenario: Index template is initialized
- **WHEN** the ES init script creates or updates task event index resources
- **THEN** the mapping treats `task_id`, `host_id`, `status`, `collector_source`, and `log_path` as keyword-compatible fields and treats `run_at` and `@timestamp` as date fields

### Requirement: Latest task event query
The system SHALL support querying the latest task event for a monitor task and host.

#### Scenario: Latest event exists
- **WHEN** report analysis requests the latest event for a given `task_id` and `host_id`
- **THEN** the system filters by both fields and returns the most recent event ordered by `run_at` with `@timestamp` as fallback

#### Scenario: No event exists
- **WHEN** no ES document exists for a given `task_id` and `host_id`
- **THEN** the query returns an empty result that report analysis can classify as missing task logs
