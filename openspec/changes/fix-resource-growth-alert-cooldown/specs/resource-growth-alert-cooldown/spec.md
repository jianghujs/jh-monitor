## ADDED Requirements

### Requirement: Resource growth alerts respect configured cooldowns
The system SHALL suppress repeated resource growth notifications for the same host and alarm level until the configured notification interval has elapsed.

#### Scenario: Alert remains inside cooldown
- **WHEN** the latest resource growth alert for a host and level is newer than the configured interval
- **THEN** the system SHALL skip sending another notification for that host and level

#### Scenario: Alert cooldown has elapsed
- **WHEN** a resource growth condition still exists after the configured interval has elapsed
- **THEN** the system SHALL record and send a new notification

### Requirement: Alert cooldown is isolated by host and level
The system SHALL maintain notification-layer cooldown state independently for each host and alarm level.

#### Scenario: Different hosts alert concurrently
- **WHEN** two different hosts trigger resource growth alerts during the same scan
- **THEN** each host SHALL be eligible for its own notification

#### Scenario: Warning escalates to critical
- **WHEN** a host with a recent warning alert triggers a critical alert
- **THEN** the critical alert SHALL use a separate cooldown key and remain eligible for notification

### Requirement: Database failures fail closed for notification delivery
The system MUST NOT send a resource growth notification when it cannot reliably read the previous alert state or persist the new alert record.

#### Scenario: Previous alert lookup fails
- **WHEN** the previous resource growth alert query returns a database error
- **THEN** the system SHALL skip notification delivery for that host in the current scan and log the failure

#### Scenario: New alert record cannot be persisted
- **WHEN** the system detects a resource growth alert but cannot persist its alert record
- **THEN** the system SHALL not send the notification and SHALL log the persistence failure
