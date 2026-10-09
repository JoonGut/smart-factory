# Proposal

## Why

The smart-factory project has no reproducible runtime for its robot data pipeline: `pia/docker-compose.yml` is empty and `bda/` is empty, so Node-RED ingestion, InfluxDB storage, and Grafana visualization cannot be started together. A single pinned compose stack gives every clone a working `up` path for MiR, printer, and Dobot data.

## What Changes

- Add a `pia/docker-compose.yml` stack with three pinned services: `nodered:latest`, `influxdb:2.9.1`, `grafana:13.2.2` on one bridge network with host ports 1880 / 8086 / 3000.
- Persist state with named volumes for InfluxDB (`/var/lib/influxdb2`) and Grafana (`/var/lib/grafana`) plus a host directory for Node-RED (`/data`, so `flows.json` stays editable and git-reviewable); bind-mount Grafana provisioning from the repo.
- Auto-provision a single InfluxDB org plus three buckets (`mir_robots`, `3d_printers`, `dobot`) sharing the frozen tag key `robot_id` on first initialization via `DOCKER_INFLUXDB_INIT_*` plus an init script for the extra buckets, so a fresh machine reaches the same state with one `up`.
- Wire org + buckets + API token into InfluxDB init, Node-RED, and Grafana via a gitignored `.env` plus a committed `.env.example`; the token value is chosen once by the operator in `.env` before first boot.
- Add `depends_on` healthy ordering (Node-RED and Grafana wait for InfluxDB `/health`) and restart policies so `docker compose up` converges reliably.

## Capabilities

### New Capabilities

- `monitoring-stack`: reproducible local observability stack (compose services, persistence, networking, health ordering, first-boot auto-provisioning of the InfluxDB org/buckets from env, per-robot write/read contract on `robot_id`).

### Modified Capabilities

- None. No existing specs exist (`openspec list --specs` returns empty); this is the first capability.

## Impact

- Affects `pia/` (compose file, `.env.example`, InfluxDB init script, flows and provisioning bind-mount sources).
- Dependencies: Docker Engine with Compose v2; pinned images `influxdb:2.9.1`, `grafana:13.2.2`, `nodered:latest` (only floating tag; major jumps possible on rebuild).
- Portability risk: init vars apply only on an empty volume, so moving machines means fresh volumes plus the same `.env`; token embedded in `flows.json`/provisioning must stay out of git via `.env` indirection.
