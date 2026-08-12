## ADDED Requirements

### Requirement: Daily-report task analysis
The system SHALL analyze enabled monitor tasks during daily report generation.

#### Scenario: Daily report builds single-host report
- **WHEN** the daily report analyzer builds a single-host report
- **THEN** it reads enabled monitor tasks for that host and evaluates each task using the latest ES task event

#### Scenario: Management page is refreshed outside report generation
- **WHEN** an operator views the monitor task management page before another daily report run
- **THEN** the page shows the most recent stored analysis result and does not imply that real-time analysis has run

### Requirement: Task status classification
The system SHALL classify monitor task status from the latest event, configured interval, and grace period.

#### Scenario: No task event exists
- **WHEN** an enabled task has no matching ES event
- **THEN** the analysis classifies the task as `error` with message `未发现任务日志`

#### Scenario: Latest task event is overdue
- **WHEN** the current analysis time is later than `last_run_at + check_interval + grace_seconds`
- **THEN** the analysis classifies the task as `error` with a message indicating the task did not produce logs on schedule

#### Scenario: Latest task event is success
- **WHEN** the latest non-overdue task event status is `success`
- **THEN** the analysis classifies the task as `normal` and uses the latest event message

#### Scenario: Latest task event is warning
- **WHEN** the latest non-overdue task event status is `warning`
- **THEN** the analysis classifies the task as `warning` and uses the latest event message

#### Scenario: Latest task event is error
- **WHEN** the latest non-overdue task event status is `error`
- **THEN** the analysis classifies the task as `error` and uses the latest event message

#### Scenario: Latest task event has unknown status
- **WHEN** the latest non-overdue task event status is not recognized
- **THEN** the analysis classifies the task as `unknown` or `error` and includes the unknown status in the message

### Requirement: Analysis result persistence
The system SHALL persist the latest daily-report analysis result back to the monitor task row.

#### Scenario: Task analysis completes
- **WHEN** a monitor task is evaluated during daily report generation
- **THEN** the system updates `last_status`, `last_msg`, `last_run_at`, and `last_analyse_at` for that task

#### Scenario: ES query fails
- **WHEN** the analyzer cannot query task events from ES
- **THEN** the system records a clear analysis failure message without deleting the task definition

### Requirement: Single-host report task section
The system SHALL include monitor task analysis results in single-host report data and HTML.

#### Scenario: Host has monitor tasks
- **WHEN** a single-host report is generated for a host with enabled monitor tasks
- **THEN** the report document includes structured monitor task results containing task name, status, latest message, latest run time, and check interval

#### Scenario: Task has error status
- **WHEN** any monitor task for the host is classified as `error`
- **THEN** the single-host report is marked abnormal and the task finding is included in `error_tips`

#### Scenario: Task has warning status without errors
- **WHEN** one or more monitor tasks are classified as `warning` and no monitor task is classified as `error`
- **THEN** the single-host report is marked as warning and the task finding is included in orange summary tips

#### Scenario: All tasks are normal
- **WHEN** all monitor tasks for the host are classified as `normal`
- **THEN** the report can show task details without adding abnormal error tips

### Requirement: Overview report propagation
The system SHALL allow monitor task findings to affect the existing overview report classification through single-host report status.

#### Scenario: Single-host task error exists
- **WHEN** a single-host report is abnormal because of monitor task errors
- **THEN** the overview report includes that host in the abnormal host summary using the existing overview aggregation behavior

#### Scenario: Single-host task warning exists
- **WHEN** a single-host report is warning only because of monitor task warnings
- **THEN** the overview report includes that host in the warning host summary using the existing overview aggregation behavior

### Requirement: No independent analyzer in first version
The system SHALL NOT require a separate monitor task analysis scheduler for the first version.

#### Scenario: Daily report has not run yet
- **WHEN** a task was installed but no daily report analysis has evaluated it
- **THEN** the system keeps the task in an unknown or pending analysis state until a daily report run evaluates it
