## ADDED Requirements

### Requirement: System SHALL derive reporting freshness from the latest received data
The system SHALL derive a reporting freshness state for every managed host and registered HA host without overwriting its last reported runtime, online, or health state. A valid latest report whose age is less than 24 hours SHALL be `fresh`; a valid latest report whose age is at least 24 hours SHALL be `stale`.

#### Scenario: Latest report is less than 24 hours old
- **WHEN** the reference time is 86,399 seconds after the latest valid report time
- **THEN** the system marks reporting freshness as `fresh` and continues to use the reported runtime or health state

#### Scenario: Latest report reaches the 24-hour boundary
- **WHEN** the reference time is exactly 86,400 seconds after the latest valid report time
- **THEN** the system marks reporting freshness as `stale`, marks reporting as abnormal, and describes the reason as exceeding 24 hours without a report

#### Scenario: A stale object reports again
- **WHEN** an object previously marked `stale` supplies a new valid report less than 24 hours before the reference time
- **THEN** the system marks reporting freshness as `fresh` without requiring manual state cleanup

#### Scenario: Latest report time is slightly in the future
- **WHEN** clock skew makes the latest valid report time later than the reference time
- **THEN** the system treats the report age as zero and does not mark the object stale solely because of the negative age

### Requirement: Never-reported objects SHALL receive a 24-hour grace period
The system SHALL derive freshness for an object without a valid report from its creation or registration time. An object younger than 24 hours SHALL be `pending`; an object whose grace-period age is at least 24 hours SHALL be `never_reported` and abnormal.

#### Scenario: Newly created host has not reported
- **WHEN** a managed host has no valid report and was created less than 24 hours before the reference time
- **THEN** the system displays the host as waiting for its first report and does not count the 24-hour reporting abnormality

#### Scenario: Host never reports within the grace period
- **WHEN** a managed host has no valid report and was created at least 24 hours before the reference time
- **THEN** the system marks it abnormal and explains that it has never reported within 24 hours of creation

#### Scenario: Registered HA host has not reported
- **WHEN** an HA host has no valid report and its registration age reaches 24 hours
- **THEN** the system marks that HA host `never_reported` and includes it in the HA pair danger state

### Requirement: Host management SHALL distinguish stale reporting from a stopped host
The host management API and page SHALL expose and display reporting freshness independently from the last reported host runtime state. A reporting abnormality SHALL take display precedence over an old `Running` or `Stopped` value.

#### Scenario: Last runtime was running but data is stale
- **WHEN** the latest system-status document says the host is running but its report age is at least 24 hours
- **THEN** the host list displays a red reporting abnormality with the latest report time instead of displaying the host as currently running

#### Scenario: Last runtime was stopped but data is stale
- **WHEN** the latest system-status document says the host is stopped and its report age is at least 24 hours
- **THEN** the host list identifies the primary condition as reporting abnormal rather than claiming that stale data confirms the host is currently stopped

#### Scenario: Host is waiting for its first report
- **WHEN** a newly created host is inside the 24-hour grace period and has no system-status document
- **THEN** the host list displays `待上报` and does not display `已停止`

### Requirement: Reporting freshness SHALL use server-side reference time
The backend SHALL compute reporting freshness and return structured freshness fields; browser clients SHALL NOT independently decide whether 24 hours have elapsed. Interactive pages SHALL use the current cloud-monitor server time, and daily analysis SHALL use the report window end time.

#### Scenario: Operator browser clock differs from server clock
- **WHEN** an operator opens a management page from a browser whose clock or timezone differs from the cloud-monitor server
- **THEN** the displayed freshness state matches the backend result and does not change based on browser time

#### Scenario: Historical daily report is regenerated
- **WHEN** the system regenerates a report for a past report window
- **THEN** freshness is evaluated using the past window end and only status data at or before that end time

### Requirement: Daily reports SHALL identify 24-hour reporting abnormalities
Daily single-host and overview reports SHALL classify hosts that are `stale` or `never_reported` at the report-window end as abnormal and SHALL include a clear 24-hour no-report reason and the latest report time when one exists.

#### Scenario: Host has no data in the last 24 hours
- **WHEN** the latest status at or before the report-window end is at least 24 hours old
- **THEN** the single-host report records a stable 24-hour reporting validation error and the overview includes the host in the abnormal-host summary

#### Scenario: Host has never supplied status data
- **WHEN** the host grace period has expired and no status exists at or before the report-window end
- **THEN** the report records a never-reported validation error and includes the host in the abnormal-host summary

#### Scenario: Status is incomplete but not yet 24 hours stale
- **WHEN** the latest status violates the existing short data-completeness threshold but is less than 24 hours old
- **THEN** the report retains the existing completeness abnormality without falsely labeling it as exceeding 24 hours without a report

### Requirement: Storage failures SHALL remain distinct from reporting abnormalities
The system SHALL NOT classify every object as stale merely because Elasticsearch or the HA SQLite store could not be read.

#### Scenario: Elasticsearch query fails
- **WHEN** the system cannot query the status indices
- **THEN** the host page or daily report exposes the storage-unavailable condition and does not assert that all hosts exceeded 24 hours without reporting

#### Scenario: HA store read fails
- **WHEN** the system cannot read HA state from SQLite
- **THEN** the HA page, snapshot, or report exposes an unavailable/read-failure state instead of manufacturing stale states for all HA hosts
