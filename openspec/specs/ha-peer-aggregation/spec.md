# ha-peer-aggregation Specification

## Purpose
TBD - created by archiving change add-ha-management. Update Purpose after archive.
## Requirements
### Requirement: Plugin SHALL collect peer state over SSH
Each `ha_manager` plugin SHALL collect peer HA state through the configured SSH binding.

#### Scenario: Peer SSH collection succeeds
- **WHEN** the plugin can connect to the peer over SSH
- **THEN** it reads the peer HA state snapshot, peer switch status, and peer log sequence metadata

#### Scenario: Peer SSH collection fails
- **WHEN** the plugin cannot connect to the peer over SSH
- **THEN** it reports `collect_status=failed` and `health_status=unknown` for the peer without treating the peer as confirmed business offline

### Requirement: Plugin SHALL collect peer logs incrementally
Each plugin SHALL collect peer switch logs incrementally and preserve source-host identity.

#### Scenario: Peer has new log lines
- **WHEN** the peer log sequence is greater than the last collected sequence
- **THEN** the plugin fetches only new peer log events and reports them with `origin_host_id` set to the peer and `collect_method=ssh_peer`

#### Scenario: Peer log collection is partial
- **WHEN** the plugin can read peer state but fails to read peer logs
- **THEN** it reports `collect_status=partial` and cloud monitor shows a warning that logs are incomplete

### Requirement: Local cloud monitor SHALL receive aggregated host data
The plugin SHALL upload both local and peer data to the cloud monitor configured in that plugin.

#### Scenario: Datacenter A plugin reports to datacenter A cloud monitor
- **WHEN** datacenter A plugin completes local and peer collection
- **THEN** datacenter A cloud monitor receives state and logs for both datacenter A host and datacenter B host

#### Scenario: Datacenter B plugin reports to datacenter B cloud monitor
- **WHEN** datacenter B plugin completes local and peer collection
- **THEN** datacenter B cloud monitor receives state and logs for both datacenter B host and datacenter A host

### Requirement: Cloud monitor SHALL distinguish collection failure from host offline
The cloud monitor SHALL store and display collection status separately from host online status.

#### Scenario: Peer collection failed but host offline is unknown
- **WHEN** a plugin reports peer `collect_status=failed` without peer `online_status=offline`
- **THEN** the cloud monitor displays a collection warning and SHALL NOT mark the peer as confirmed offline solely from the collection failure

