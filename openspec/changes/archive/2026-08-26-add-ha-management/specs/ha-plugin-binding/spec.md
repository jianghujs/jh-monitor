## ADDED Requirements

### Requirement: HA manager plugin SHALL be named ha_manager
The Jianghu panel plugin SHALL be delivered as `ha_manager`.

#### Scenario: Plugin is installed
- **WHEN** the operator installs the HA plugin on a Jianghu panel server
- **THEN** the plugin directory and plugin file references use `ha_manager`

### Requirement: Plugin SHALL bind peer by SSH information
The plugin SHALL bind the peer server by peer public IP, SSH port, SSH user, and peer public key.

#### Scenario: Operator configures peer binding
- **WHEN** the operator enters peer public IP, SSH port, SSH user, and peer public key
- **THEN** the plugin allows the operator to test SSH connectivity before saving the binding

#### Scenario: Operator saves binding without pair id input
- **WHEN** the operator saves a valid peer binding
- **THEN** the plugin stores or receives the HA relationship id internally without showing a `pair_id` input field in the UI

### Requirement: Plugin SHALL configure cloud monitor separately
The plugin SHALL provide a separate cloud monitor configuration tab.

#### Scenario: Cloud monitor URL is empty
- **WHEN** the cloud monitor URL is empty
- **THEN** the plugin works locally and SHALL NOT upload HA state, switch state, or logs to cloud monitor

#### Scenario: Cloud monitor URL is configured
- **WHEN** the cloud monitor URL is configured and saved
- **THEN** the plugin uses the configured polling and reporting intervals for cloud monitor communication

#### Scenario: Operator saves cloud monitor registration
- **WHEN** the operator enters an HA relationship name, configures cloud monitor URL, and saves the cloud monitor configuration
- **THEN** the plugin registers or updates the HA relationship in cloud monitor using that relationship name as the business subject name, such as Jianghu Demo, Dev02, Dev03, or MD Xuanfeng, and includes local plus peer host information in subsequent reports

### Requirement: Plugin homepage SHALL support local manual switch
The plugin SHALL allow operators to start a local manual switch from the plugin homepage.

#### Scenario: Current node is master
- **WHEN** the plugin homepage detects the current node role is `master`
- **THEN** it displays a switch action to switch the current node to standby

#### Scenario: Current node is standby
- **WHEN** the plugin homepage detects the current node role is `standby`
- **THEN** it displays a switch action to switch the current node to master

#### Scenario: Operator confirms local switch
- **WHEN** the operator starts a local switch
- **THEN** the plugin opens a confirmation dialog with the relevant offline or online flow options and shows switch logs after confirmation

### Requirement: Plugin SHALL expose local health and logs
The plugin SHALL provide tabs for health status and switch logs.

#### Scenario: Operator opens plugin health tab
- **WHEN** the operator opens the health status tab
- **THEN** the plugin displays SSH, cloud monitor connection, MySQL, rsync/lsyncd, OpenResty, and local execution lock checks

#### Scenario: Operator opens plugin switch log tab
- **WHEN** the operator opens the switch log tab
- **THEN** the plugin displays the latest switch log and cloud monitor log path when available
