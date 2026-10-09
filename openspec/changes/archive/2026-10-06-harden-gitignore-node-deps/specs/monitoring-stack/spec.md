# Spec Delta

## MODIFIED Requirements

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

## ADDED Requirements

### Requirement: Node-RED dependencies are reproducible per clone
The system SHALL track `pia/nodered/package.json` and `pia/nodered/package-lock.json` in version control declaring the required Node-RED contribution nodes (including `node-red-contrib-influxdb`), so a fresh clone can reproduce the exact Node-RED runtime dependencies without relying on the floating `nodered:latest` image contents.

#### Scenario: Fresh clone declares InfluxDB nodes
- **WHEN** a fresh clone is inspected before `npm install`
- **THEN** `pia/nodered/package.json` lists `node-red-contrib-influxdb` and `pia/nodered/package-lock.json` pins its resolved tree, and neither file is ignored by git

#### Scenario: Reinstall converges without missing nodes
- **WHEN** a user runs `npm ci` (or `npm install`) in `pia/nodered/` and starts the stack
- **THEN** Node-RED starts with no missing-node warnings for the InfluxDB output nodes used by `flows.json`
