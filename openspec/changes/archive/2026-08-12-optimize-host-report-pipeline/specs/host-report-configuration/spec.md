## ADDED Requirements

### Requirement: Panel SHALL manage report pipeline configuration centrally
The system SHALL provide a dedicated host report configuration area in the panel settings UI for Elasticsearch connectivity and host report anomaly thresholds, and the backend SHALL own loading, saving, and returning those values.

#### Scenario: Load configuration for display
- **WHEN** an operator opens the panel settings page
- **THEN** the system returns the current Elasticsearch settings and host report threshold values from the host report configuration APIs

#### Scenario: Save configuration successfully
- **WHEN** an operator submits valid Elasticsearch settings and threshold values
- **THEN** the backend validates the payload and persists the Elasticsearch settings and threshold settings through dedicated configuration storage

### Requirement: Configuration storage SHALL be separated and resilient
The system SHALL store report thresholds in `data/report_config.json` and Elasticsearch settings in `data/es.json`, SHALL initialize missing files as `{}`, and SHALL write updates atomically so interrupted writes do not corrupt saved configuration.

#### Scenario: Missing configuration files
- **WHEN** the backend reads host report configuration and either JSON file does not exist
- **THEN** the system creates or treats the missing file as an empty `{}` configuration and returns a valid default response

#### Scenario: Configuration write interruption protection
- **WHEN** the backend persists updated configuration
- **THEN** the system writes the new content to a temporary file and replaces the target JSON file only after the temporary write succeeds

### Requirement: Configuration validation SHALL reject invalid values before persistence
The system SHALL reject malformed Elasticsearch configuration and out-of-range threshold values, and SHALL support Elasticsearch connectivity verification before committing a new Elasticsearch configuration.

#### Scenario: Invalid threshold payload
- **WHEN** an operator submits a threshold value that is empty, non-numeric, or outside the accepted range
- **THEN** the backend rejects the request and reports which field failed validation

#### Scenario: Elasticsearch connectivity check fails
- **WHEN** an operator requests a save or test with unreachable Elasticsearch connection parameters
- **THEN** the system returns a failed connectivity result and SHALL NOT persist the invalid Elasticsearch configuration
