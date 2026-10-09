# monitoring-stack

## Purpose

Provide a reproducible local runtime where Node-RED ingests robot data, InfluxDB stores it per robot type, and Grafana visualizes it, all started from one compose file.

## Requirements

### Requirement: Pinned three-service stack starts together
The system SHALL provide one compose stack that starts Node-RED, InfluxDB 2.9.1, and Grafana 13.2.2 together on a single bridge network with host ports 1880, 8086, and 3000 respectively.

#### Scenario: Fresh clone starts all services
- **WHEN** a user with Docker Engine plus Compose v2 runs `docker compose up -d` from `pia/` with a valid `.env`
- **THEN** three containers reach healthy/running state and the Node-RED UI, InfluxDB API `/health`, and Grafana login page each respond on their host port

#### Scenario: Start order converges without manual retries
- **WHEN** the stack is started from cold with an empty Docker network
- **THEN** Node-RED and Grafana wait for InfluxDB health before attempting connections and reach running state without manual restart

### Requirement: State survives container restarts
The system SHALL persist InfluxDB data and Grafana configuration in named volumes and Node-RED runtime data (including flows) in a host directory bind mount, across `docker compose down` and `up` cycles.

#### Scenario: Restart keeps robot data
- **WHEN** time-series points have been written and the user runs `docker compose down` (without `-v`) followed by `docker compose up -d`
- **THEN** previously written points, saved Node-RED flows, and Grafana settings remain available

### Requirement: First boot auto-provisions org and buckets
The system SHALL create a single InfluxDB organization with exactly three buckets (`mir_robots`, `3d_printers`, `dobot`) on first initialization from environment values, and SHALL create no additional organizations, buckets, users, or tokens on subsequent restarts.

#### Scenario: Fresh volume provisions the full data layout
- **WHEN** the stack starts for the first time with an empty InfluxDB volume and a valid `.env`
- **THEN** the configured org exists with all three buckets queryable, and restarting the stack creates nothing new

#### Scenario: Missing bucket surfaces a clear failure
- **WHEN** a write or query targets a bucket name outside the three provisioned buckets
- **THEN** it fails with an InfluxDB bucket-not-found error visible in the calling service logs rather than silently creating state

### Requirement: Per-robot write contract on frozen tag key
The system SHALL write every point with the tag key `robot_id` and SHALL route MiR tour/battery data to `mir_robots`, printer temperature/print-job data to `3d_printers`, and Dobot coordinate data to `dobot`.

#### Scenario: Points land in the correct bucket with robot_id
- **WHEN** Node-RED ingests a MiR battery reading, a printer temperature reading, and a Dobot position reading each carrying a `robot_id` tag
- **THEN** the MiR point is queryable in `mir_robots`, the printer point in `3d_printers`, and the Dobot point in `dobot`, each filterable by `robot_id`

#### Scenario: Tag key stays stable
- **WHEN** new robot instances are added
- **THEN** they are distinguished by new `robot_id` tag values with no change to the tag key or bucket names, and existing Grafana filters keep working

### Requirement: Single Flux datasource reads all buckets
The system SHALL expose one Grafana InfluxDB datasource configured with the InfluxDB URL, organization, and API token that can query all three buckets, with bucket selection made per panel query.

#### Scenario: One datasource serves per-robot dashboards
- **WHEN** a dashboard panel queries `from(bucket: "mir_robots")`, another queries `from(bucket: "3d_printers")`, and another queries `from(bucket: "dobot")`
- **THEN** all three panels return data through the same configured datasource without additional datasource entries

### Requirement: Secrets stay out of version control
The system SHALL supply the InfluxDB URL, organization, bucket names, and API token to Node-RED and Grafana through environment variables loaded from a gitignored `.env`, SHALL commit a `.env.example` documenting every required variable with placeholder values, SHALL exclude Node-RED credential and runtime files (`flows_cred.json` and its backups, `.config.nodes.json*`, `.config.runtime.json*`, `*.backup`), installed dependencies (`node_modules/`, `.npm/`), and default `settings.js` from version control, and SHALL enforce these exclusions both in the nested `pia/nodered/.gitignore` and redundantly in the root `.gitignore` so a missing nested file cannot expose secrets or runtime noise.

#### Scenario: Clone contains no real token
- **WHEN** a fresh clone is inspected before local setup
- **THEN** `.env` is absent, `.env.example` lists all required variables with dummy values, and no real token appears in committed flows, provisioning, or compose files

#### Scenario: Node-RED runtime stays local
- **WHEN** Node-RED has run locally (flows edited, nodes installed, credentials written) and `git status` is inspected
- **THEN** `flows_cred.json`, `.config.*.json` files, `*.backup` files, `node_modules/`, and `.npm/` are all ignored by git, while `flows.json` is shown as the only runtime-tracked file

#### Scenario: Nested ignore loss does not leak secrets
- **WHEN** `pia/nodered/.gitignore` is temporarily removed and `git check-ignore` is run against `pia/nodered/flows_cred.json` and `pia/nodered/node_modules`
- **THEN** both paths are still reported as ignored via the root `.gitignore`

### Requirement: Node-RED dependencies are reproducible per clone
The system SHALL track `pia/nodered/package.json` and `pia/nodered/package-lock.json` in version control declaring the required Node-RED contribution nodes (including `node-red-contrib-influxdb`), so a fresh clone can reproduce the exact Node-RED runtime dependencies without relying on the floating `nodered:latest` image contents.

#### Scenario: Fresh clone declares InfluxDB nodes
- **WHEN** a fresh clone is inspected before `npm install`
- **THEN** `pia/nodered/package.json` lists `node-red-contrib-influxdb` and `pia/nodered/package-lock.json` pins its resolved tree, and neither file is ignored by git

#### Scenario: Reinstall converges without missing nodes
- **WHEN** a user runs `npm ci` (or `npm install`) in `pia/nodered/` and starts the stack
- **THEN** Node-RED starts with no missing-node warnings for the InfluxDB output nodes used by `flows.json`
