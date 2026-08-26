# ha-alert-callback Specification

## Purpose
TBD - created by archiving change add-ha-management. Update Purpose after archive.
## Requirements
### Requirement: Cloud monitor SHALL classify HA alerts
The cloud monitor SHALL classify HA status into normal, warning, switching, and danger states.

#### Scenario: Actual primary is offline
- **WHEN** the actual primary host is offline or its plugin has not reported beyond the threshold
- **THEN** the cloud monitor displays a red danger alert and indicates that manual switch may be needed

#### Scenario: Subsystem warning exists
- **WHEN** MySQL, rsync/lsyncd, OpenResty, callback, or peer collection is abnormal but HA primary is not confirmed offline
- **THEN** the cloud monitor displays an orange warning identifying the affected subsystem

### Requirement: Cloud monitor SHALL retry state and log callback handling
The cloud monitor SHALL expose enough state for retrying failed switch phases and failed callbacks.

#### Scenario: Switch phase failed
- **WHEN** offline or online phase fails
- **THEN** the cloud monitor records failed phase, current step, last error, log path, and retry availability

#### Scenario: Callback failed after successful switch
- **WHEN** the switch succeeded but external callback failed
- **THEN** the switch remains successful while callback status is marked failed or retrying

### Requirement: Cloud monitor SHALL call external systems after actual switch completion
The cloud monitor SHALL invoke configured callback URLs after confirming the actual master has switched.

#### Scenario: Actual switch is confirmed
- **WHEN** offline phase is complete, online phase is complete, new master reports actual role master, and switch run becomes success
- **THEN** the cloud monitor calls each enabled callback URL with pair id, switch run id, old master, new master, actual master, status, and finish time

#### Scenario: Callback response is not successful
- **WHEN** the callback endpoint does not respond successfully
- **THEN** the cloud monitor records the error in switch state and appends the callback error to the switch log file

