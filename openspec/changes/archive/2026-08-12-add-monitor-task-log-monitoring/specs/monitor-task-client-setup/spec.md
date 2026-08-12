## ADDED Requirements

### Requirement: Public setup script endpoint
The system SHALL provide a public endpoint that returns the monitor task installation script used by copied install commands.

#### Scenario: Client downloads setup script
- **WHEN** a monitored host requests `/pub/get_monitor_task_install_script`
- **THEN** the system returns an executable shell script that supports install and update actions for monitor task logging

### Requirement: Task registration endpoint
The system SHALL provide a public setup endpoint for registering or updating a monitor task from the client installation script.

#### Scenario: Client registers task with valid host
- **WHEN** the setup script submits task id, task name, host id, log path, check interval, and grace seconds for an existing host
- **THEN** the system creates or updates the matching monitor task and records install status progress

#### Scenario: Client registers task with unknown host
- **WHEN** the setup script submits a host id that does not exist in the panel
- **THEN** the system rejects the registration and returns an error without creating a task

### Requirement: Install status callback
The system SHALL allow the setup script to report installation success or failure for a monitor task.

#### Scenario: Client reports install success
- **WHEN** the setup script finishes creating the logging command, log path, and filebeat input
- **THEN** the system updates the task `install_status` to `installed` and records the callback message and update time

#### Scenario: Client reports install failure
- **WHEN** the setup script cannot complete installation because a prerequisite or validation fails
- **THEN** the system updates the task `install_status` to `failed` and stores a useful failure message

### Requirement: Client setup idempotence
The setup script SHALL be safe to run repeatedly for the same task.

#### Scenario: Operator reruns install command
- **WHEN** the same install command is executed more than once on the monitored host
- **THEN** the setup script overwrites or updates managed files in place without creating duplicate filebeat inputs or duplicate command symlinks

### Requirement: Standard logging command deployment
The setup script SHALL deploy the `jh-monitor-task-log` command and local task configuration for business scripts.

#### Scenario: Setup deploys logging command
- **WHEN** installation succeeds
- **THEN** the monitored host has `/usr/local/bin/jh-monitor-task-log` available and a local task config under `/home/ansible_user/jh-monitor-tasks/<task_id>.json`

### Requirement: Filebeat input deployment
The setup script SHALL configure filebeat to collect the monitor task JSON Lines log file.

#### Scenario: Filebeat is available
- **WHEN** filebeat exists and supports configured inputs
- **THEN** the setup script writes a per-task input file that collects the configured log path and adds task and host fields under root

#### Scenario: Task input is isolated from host collection inputs
- **WHEN** the setup script writes filebeat configuration for a monitor task
- **THEN** it writes the task input under a monitor-task-specific configuration path and does not modify existing host collection input files

#### Scenario: Filebeat include is missing
- **WHEN** filebeat supports external input files but the monitor-task-specific include is not configured
- **THEN** the setup script adds or enables only the monitor-task-specific include without rewriting unrelated host collection inputs

#### Scenario: Filebeat is unavailable
- **WHEN** filebeat is missing or cannot be validated
- **THEN** the setup script fails the installation and reports the failure status to the monitor server
