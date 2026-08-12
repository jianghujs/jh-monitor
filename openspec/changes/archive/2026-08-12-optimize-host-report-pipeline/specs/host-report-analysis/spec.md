## ADDED Requirements

### Requirement: Daily analysis SHALL generate single-host reports from Elasticsearch raw data
The system SHALL run a dedicated daily host report analysis task that reads raw documents for a target report date from Elasticsearch, applies the existing `/www/server/jh-panel/scripts/report.py` anomaly rules and configured thresholds, and produces a structured single-host report for each host.

#### Scenario: Generate a healthy single-host report
- **WHEN** the analysis task processes a host whose raw data stays within configured thresholds for the full report window
- **THEN** it stores a single-host report whose summary indicates normal operation and whose structured sections reflect the analyzed host data for that date

#### Scenario: Generate an abnormal single-host report
- **WHEN** the analysis task detects threshold breaches or missing backup evidence according to the existing report rules
- **THEN** it records the resulting summary tips, error tips, structured detail fields, and rendered HTML in the generated single-host report

### Requirement: Analysis SHALL persist reports into dedicated report indices
The system SHALL write generated single-host reports to `host-report-single` and the generated daily overview report to `host-report-overview`, and each report document SHALL include the report date, covered time window, HTML content, and enough structured data to support validation and resend workflows.

#### Scenario: Persist single-host report document
- **WHEN** analysis completes a host report for a given date
- **THEN** the system stores the report in `host-report-single` with host identity, time window, HTML content, summary data, and structured detail fields

#### Scenario: Persist overview report document
- **WHEN** analysis completes the all-host aggregation for a given date
- **THEN** the system stores the overview report in `host-report-overview` with host totals, abnormal host summaries, and the list of same-day single-host report fragments

### Requirement: Analysis SHALL validate raw data completeness before marking reports ready
The system SHALL verify that required raw inputs exist for each analyzed host and date, SHALL flag incomplete analyses, and SHALL prevent incomplete report documents from being treated as ready-to-send reports.

#### Scenario: Complete raw data set
- **WHEN** the analysis task finds all required raw data inputs for a host and date
- **THEN** it marks the generated report as ready for downstream delivery validation

#### Scenario: Missing or stale raw data
- **WHEN** required raw documents are absent or older than the report window rules allow
- **THEN** the generated report records the completeness failure and is excluded from ready-to-send delivery candidates until re-analysis succeeds
