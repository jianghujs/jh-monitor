## ADDED Requirements

### Requirement: Cloud monitor SHALL request manual switch by desired state
The cloud monitor SHALL initiate a manual HA switch by updating desired master state and creating a switch run.

#### Scenario: Operator requests switch to standby host
- **WHEN** the operator confirms switching an HA pair to the standby host
- **THEN** the cloud monitor creates a switch run, updates desired master host, records switch options, and creates the switch log file path

#### Scenario: First version receives failure condition
- **WHEN** a host is offline or partially abnormal
- **THEN** the cloud monitor alerts the operator but SHALL NOT automatically initiate a switch

### Requirement: Plugin SHALL execute offline phase on old master
The plugin SHALL execute the old master's offline flow based on the existing Jianghu panel offline script process.

#### Scenario: Old master receives offline phase
- **WHEN** the old master plugin polls and receives an offline phase for a switch run
- **THEN** it executes the offline flow, reports phase start, reports step results, and reports `offline_done` or failure

#### Scenario: Offline flow fails
- **WHEN** a required offline step fails and the failure policy is stop
- **THEN** the plugin reports failure and the switch run becomes failed or waiting for manual retry

### Requirement: Plugin SHALL execute online phase on new master
The plugin SHALL execute the target master's online flow based on the existing Jianghu panel online script process.

#### Scenario: Target master receives online phase
- **WHEN** the target master plugin polls and receives an online phase for a switch run
- **THEN** it applies the switch options non-interactively, executes the online flow, reports step results, and reports actual role as master after validation

#### Scenario: Online options are provided
- **WHEN** the online flow starts
- **THEN** the plugin uses configured options for local IP, remote IP, remote SSH port, checksum, file sync, restore settings, incremental restore, and MySQL promotion without interactive prompts

### Requirement: Switch execution SHALL be guarded by local lock
The plugin SHALL prevent concurrent switch execution on the same host.

#### Scenario: Existing switch is running
- **WHEN** a plugin already holds the local switch lock
- **THEN** it refuses to start another switch run and reports the lock state to cloud monitor
