## ADDED Requirements

### Requirement: Cloud monitor HA page
The system SHALL provide a logged-in cloud monitor page for managing HA pairs.

#### Scenario: Operator opens HA management page
- **WHEN** an authenticated operator visits `/ha_management`
- **THEN** the system displays the HA management page using the existing cloud monitor layout and sidebar navigation

#### Scenario: Anonymous user opens HA management page
- **WHEN** an unauthenticated user visits `/ha_management`
- **THEN** the system redirects the user to the login page

### Requirement: HA pair list SHALL use compact table layout
The system SHALL list HA pairs in a compact table similar to the host management list.

#### Scenario: Operator views HA pair list
- **WHEN** the HA management page loads
- **THEN** the system displays each HA pair with pair name, current master host, standby host, status, desired/actual consistency, latest report time, and row actions

#### Scenario: Operator searches HA pairs
- **WHEN** the operator searches by pair name, pair id, host name, host id, or IP
- **THEN** the system filters the table to matching HA pairs

### Requirement: HA group detail SHALL use multiple tabs
The system SHALL show HA group details in a multi-tab dialog similar to host detail.

#### Scenario: Operator opens HA group detail
- **WHEN** the operator clicks detail for an HA pair
- **THEN** the system opens a dialog with tabs for group overview, host list, health status, switch status, and switch logs

#### Scenario: Operator views host list tab
- **WHEN** the host list tab is selected
- **THEN** the system displays both hosts with name, IP, host id, actual role, and online status

#### Scenario: Operator views health status tab
- **WHEN** the health status tab is selected
- **THEN** the system displays each host's own plugin, MySQL, rsync/lsyncd, OpenResty, latest report time, and alert level

#### Scenario: Operator views switch status tab
- **WHEN** the switch status tab is selected
- **THEN** the system displays each host's own switch phase, execution status, current step, next step, and log file reference

#### Scenario: Operator views switch logs tab
- **WHEN** the switch logs tab is selected
- **THEN** the system displays logs grouped by source host and also provides the full switch log file view

### Requirement: HA status colors SHALL communicate severity
The system SHALL use red for major HA exceptions and orange for partial repairable warnings.

#### Scenario: Primary host is offline
- **WHEN** the actual primary host is offline or has stopped reporting beyond the configured threshold
- **THEN** the HA list and detail display a red exception status indicating that manual switch may be needed

#### Scenario: Partial subsystem status is abnormal
- **WHEN** MySQL, rsync/lsyncd, OpenResty, callback, or SSH collection is abnormal but the primary host is not confirmed offline
- **THEN** the HA list and detail display an orange warning identifying the affected subsystem
