# ha-management-ui Specification

## Purpose
TBD - created by archiving change add-ha-management. Update Purpose after archive.
## Requirements
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
- **THEN** the system displays each HA pair with pair name, a combined host column, one status label, latest report time, and row actions

#### Scenario: Operator reads combined host column
- **WHEN** an HA pair row is displayed
- **THEN** the host column displays the current datacenter host on the first line and other hosts on subsequent lines, marks master hosts with green, standby hosts with blue, and shows a `本机房` tag after the current datacenter host name

#### Scenario: Operator reads host state indicator
- **WHEN** an HA pair row is displayed
- **THEN** each host row shows a status dot before the host name instead of online/offline text, using green for online, gray for offline, and blinking orange for switching

#### Scenario: Operator hovers switching host dot
- **WHEN** the operator hovers over a blinking orange host status dot
- **THEN** the tooltip explains that the host is currently switching and shows the current switch step

#### Scenario: Operator hovers status label
- **WHEN** the operator hovers over the status label
- **THEN** the status tooltip displays the desired master and actual master values

#### Scenario: Operator searches HA pairs
- **WHEN** the operator searches by pair name, pair id, host name, host id, or IP
- **THEN** the system filters the table to matching HA pairs

### Requirement: Cloud monitor SHALL display plugin-registered HA relationships
The cloud monitor SHALL display HA relationships registered by `ha_manager` plugins and SHALL NOT require operators to add HA relationships manually in the cloud monitor UI.

#### Scenario: Plugin registers HA relationship
- **WHEN** a `ha_manager` plugin reports a relationship name, local host information, peer host information, and cloud monitor registration payload
- **THEN** the cloud monitor creates or updates the HA relationship and displays it in the HA management list

#### Scenario: Operator views cloud monitor page
- **WHEN** the operator opens the HA management page
- **THEN** the page provides refresh, detail, switch, and log actions but SHALL NOT provide an add relationship button

#### Scenario: No plugin has registered yet
- **WHEN** no HA relationship has been registered by any plugin
- **THEN** the cloud monitor empty state instructs the operator to bind the pair, set the relationship name, and configure cloud monitor address in the `ha_manager` plugin

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
- **THEN** the system visualizes offline and online script checks by host, with a status column that displays current state and exposes current state plus expected state in a tooltip

#### Scenario: Step check state matches expectation
- **WHEN** a step check current state matches its expected state for the host role
- **THEN** the status value is displayed in green

#### Scenario: Step check state does not match expectation
- **WHEN** a step check current state does not match its expected state for the host role
- **THEN** the status value is displayed in red

#### Scenario: Host is checked as master
- **WHEN** a host's current role is master
- **THEN** the step checks show master expectations such as MySQL with no slave configuration, OpenResty running, rsyncd running, master-side backup and notification schedules enabled or disabled as defined by the switch scripts

#### Scenario: Host is checked as standby
- **WHEN** a host's current role is standby
- **THEN** the step checks show standby expectations such as MySQL replication healthy, OpenResty stopped, rsyncd stopped, restore schedules enabled, and standby-side backup schedules enabled as defined by the switch scripts

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

