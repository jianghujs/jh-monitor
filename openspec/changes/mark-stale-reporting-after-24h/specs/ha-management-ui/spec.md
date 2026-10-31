## MODIFIED Requirements

### Requirement: HA status colors SHALL communicate severity
The system SHALL use red for major HA exceptions and orange for partial repairable warnings. The system SHALL compute reporting freshness for each registered HA host independently, and any host that has not reported for at least 24 hours SHALL make the HA pair a red exception even when another host in the pair reported recently.

#### Scenario: Primary host is offline
- **WHEN** the actual primary host is explicitly reported offline
- **THEN** the HA list and detail display a red exception status indicating that manual switch may be needed

#### Scenario: Primary host stopped reporting for 24 hours
- **WHEN** the actual primary host reaches 24 hours without a report
- **THEN** the HA list and detail display a red exception naming the primary host, stating that it exceeded 24 hours without reporting, and showing its latest report time

#### Scenario: Standby host stopped reporting for 24 hours
- **WHEN** the standby host reaches 24 hours without a report while the primary host continues reporting normally
- **THEN** the HA pair still displays a red exception naming the standby host instead of being considered normal from the pair's latest report time

#### Scenario: HA host is inside first-report grace period
- **WHEN** an HA host has never reported and was registered less than 24 hours ago
- **THEN** the host displays `待上报` and does not create a 24-hour danger reason for the pair

#### Scenario: HA host never reports after registration
- **WHEN** an HA host has never reported and its registration age reaches 24 hours
- **THEN** the HA pair displays a red exception naming that host and explaining that it has not reported within 24 hours of registration

#### Scenario: Partial subsystem status is abnormal
- **WHEN** MySQL, rsync/lsyncd, OpenResty, callback, or SSH collection is abnormal but no host is confirmed offline or stale for 24 hours
- **THEN** the HA list and detail display an orange warning identifying the affected subsystem

#### Scenario: Stale HA host reports again
- **WHEN** an HA host with a 24-hour reporting exception supplies a new valid report and no other danger reason remains
- **THEN** the HA pair removes the reporting danger and derives its state from the newly reported online and health values

## ADDED Requirements

### Requirement: HA read surfaces SHALL expose per-host reporting freshness
The HA list API, detail API, read-only relationship snapshots, and daily-report HA overview SHALL expose or consume the same per-host reporting freshness result and SHALL preserve the original reported online and health values separately.

#### Scenario: Operator views HA detail
- **WHEN** an HA host is stale or has never reported after its grace period
- **THEN** the detail view shows the reporting abnormality, original online and self-check state, and latest report time as distinct information

#### Scenario: API client reads HA snapshot
- **WHEN** an authorized API client requests an HA relationship snapshot
- **THEN** each host includes the same structured reporting freshness used by the management page

#### Scenario: Daily report builds HA overview
- **WHEN** the server daily report evaluates HA relationships at the report-window end
- **THEN** it includes each stale or never-reported host in the abnormal HA summary with the same reason used by the HA page
