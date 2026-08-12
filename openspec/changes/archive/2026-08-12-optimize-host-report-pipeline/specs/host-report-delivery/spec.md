## ADDED Requirements

### Requirement: Daily delivery SHALL send only validated reports from report indices
The system SHALL execute a dedicated delivery task that reads only validated same-day documents from `host-report-single` and `host-report-overview`, SHALL send the overview report every day, and SHALL send single-host reports only for hosts marked abnormal.

#### Scenario: Send overview and abnormal host reports
- **WHEN** the delivery task runs for a date with one overview report and multiple single-host reports
- **THEN** it sends the overview report plus only the abnormal single-host reports and skips normal single-host reports

#### Scenario: Reject non-validated reports
- **WHEN** a report document is missing required HTML, has an invalid report date, or is marked incomplete by analysis validation
- **THEN** the delivery task skips that document and records why it was not eligible to send

### Requirement: Delivery SHALL reuse the existing mail notification channel
The system SHALL send host reports through the existing email notification capability and SHALL reuse the notification configuration and mail dispatch path already used by `jh-monitor`.

#### Scenario: Mail configuration is available
- **WHEN** the delivery task has eligible report documents and email notification is configured correctly
- **THEN** it sends the report HTML through the existing mail notification path without fetching live host data again

#### Scenario: Mail configuration is unavailable
- **WHEN** the delivery task starts and email notification prerequisites are not configured
- **THEN** it reports the configuration failure and does not mark any attempted report as successfully sent

### Requirement: Delivery SHALL persist send status and retry metadata with each report
The system SHALL record send time, recipients, success or failure state, failure reason, and retry count for each report delivery attempt so operators can audit, retry, and reconcile report sends by date.

#### Scenario: Successful report delivery
- **WHEN** an eligible report is sent successfully
- **THEN** the system updates that report's delivery metadata with the success state, send timestamp, recipients, and current retry count

#### Scenario: Failed report delivery and retry
- **WHEN** an eligible report send attempt fails
- **THEN** the system stores the failure state and reason, increments the retry count, and keeps the report available for a later retry workflow
