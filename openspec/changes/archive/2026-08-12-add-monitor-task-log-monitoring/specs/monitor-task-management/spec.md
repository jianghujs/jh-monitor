## ADDED Requirements

### Requirement: Monitor task management page
The system SHALL provide a logged-in panel page for managing script log monitoring tasks.

#### Scenario: Operator opens the monitor task page
- **WHEN** an authenticated operator visits `/monitor_task`
- **THEN** the system displays a monitor task management page using the existing panel layout and sidebar navigation

#### Scenario: Anonymous user opens the monitor task page
- **WHEN** an unauthenticated user visits `/monitor_task`
- **THEN** the system redirects the user to the login page

### Requirement: Monitor task list
The system SHALL list monitor tasks with enough metadata to operate and inspect recent daily-report analysis results.

#### Scenario: Operator views task list
- **WHEN** the monitor task page loads
- **THEN** the system displays task name, task id, host name or IP, log path, check interval, enabled state, install status, latest status, latest message, latest run time, and latest analysis time for each task

#### Scenario: Operator searches tasks
- **WHEN** the operator searches by task name, task id, host name, or host IP
- **THEN** the system filters the list to matching monitor tasks

### Requirement: Monitor task lifecycle operations
The system SHALL allow authenticated operators to add, edit, delete, enable, and disable monitor tasks.

#### Scenario: Operator adds a task
- **WHEN** the operator selects a host and submits task name, log path, check interval, and optional grace seconds
- **THEN** the system creates a monitor task with a server-generated `task_id` and default install and analysis states

#### Scenario: Operator edits a task
- **WHEN** the operator updates task name, log path, check interval, grace seconds, or enabled state
- **THEN** the system persists the updated task definition without changing unrelated task fields

#### Scenario: Operator deletes a task
- **WHEN** the operator confirms deletion of a monitor task
- **THEN** the system removes the task definition from the management list and excludes it from future report analysis

### Requirement: Install command generation
The system SHALL generate a copyable installation command for each monitor task on the server side.

#### Scenario: Operator requests install command
- **WHEN** the operator clicks copy or view install command for a monitor task
- **THEN** the system returns a shell command containing the monitor server URL, task id, task name, host id, log path, check interval, and grace seconds as shell-safe arguments

#### Scenario: Task references an unknown host
- **WHEN** the operator requests an install command for a task whose host no longer exists
- **THEN** the system refuses to generate the command and returns an explanatory error

### Requirement: Recent analysis status wording
The system SHALL make clear that the management page status is based on the latest daily report analysis, not real-time monitoring.

#### Scenario: Task has been analyzed
- **WHEN** a task row has `last_analyse_at`
- **THEN** the page labels the displayed state as the latest analysis result and shows the analysis time

#### Scenario: Task has never been analyzed
- **WHEN** a task row does not have `last_analyse_at`
- **THEN** the page displays an unknown or pending analysis state without implying real-time failure
