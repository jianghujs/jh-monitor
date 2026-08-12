## ADDED Requirements

### Requirement: Client installation SHALL provision the report collector as an idempotent scheduled job
The system SHALL install the report collector under `/home/${USERNAME}/jh-monitor-scripts/`, SHALL schedule it through `/etc/cron.d/jh-monitor-report-collector` as a `root` cron job running every 5 minutes, and SHALL make install/update execution idempotent.

#### Scenario: First-time installation
- **WHEN** `scripts/client/install/debian.sh` runs on a host without the collector cron configured
- **THEN** the script deploys the collector files, creates the data and log directories, writes the cron file, and executes the collector once immediately

#### Scenario: Repeat installation or update
- **WHEN** `scripts/client/install/debian.sh` runs on a host that already has a prior collector version
- **THEN** the script removes obsolete cron or script references, rewrites the canonical cron file, and leaves exactly one active collector schedule behind

### Requirement: Collector output SHALL use standardized raw report schemas
The report collector SHALL emit structured raw host status documents with normalized host identity, timestamps, and status fields, and SHALL write those documents to the local collector data directory without assembling final daily reports.

#### Scenario: Successful collector run
- **WHEN** the scheduled collector executes successfully
- **THEN** it writes host system status data into the local collector output directory using the standardized raw schema and records execution details in the collector log

#### Scenario: Collector dependency or permission failure
- **WHEN** the collector cannot read required source data or write its output files
- **THEN** the install/update validation or runtime log reports the failure clearly and the host is not treated as having valid fresh raw data for that cycle

### Requirement: Filebeat ingestion SHALL map raw sources into dedicated Elasticsearch indices
The system SHALL ingest host system status, xtrabackup full backup records, xtrabackup incremental backup records, and generic backup event records into `host-system-status`, `host-xtrabackup`, `host-xtrabackup-inc`, and `host-backup` respectively.

#### Scenario: Ingest collector JSON output
- **WHEN** filebeat scans the local collector output directory
- **THEN** it forwards host system status documents into the `host-system-status` index with the expected normalized fields

#### Scenario: Ingest backup source records
- **WHEN** filebeat scans backup history JSON files and `backup.log`
- **THEN** it routes xtrabackup full, xtrabackup incremental, and generic backup events into their corresponding Elasticsearch indices without merging them into final report documents
