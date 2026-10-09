# Design

## Context

See proposal.md Why. Current state: `pia/docker-compose.yml` is empty (0 bytes), `bda/` is empty, `sbd/` holds only `.gitkeep` placeholders. Host provides Docker 29.8.2 with Compose v5.6.0. Constraints from exploration: InfluxDB `latest` tag now points to v3 (different port/env), so `2.9.1` must be pinned; single org with `robot_id` as frozen low-cardinality tag key; three heterogeneous payloads (MiR tour/battery, printer temp/job, Dobot coordinates); stack must be portable across machines with first-boot auto-provisioning of org plus `mir_robots` / `3d_printers` / `dobot`.

## Goals / Non-Goals

**Goals:**
- One `docker compose up` on any machine provisions org plus three buckets on first boot and converges healthy with persistent state.
- Org, buckets, and API token come purely from `.env` with no secrets in git.
- One Grafana Flux datasource serves all three buckets; bucket choice stays a per-query concern.

**Non-Goals:**
- No MQTT broker, OPC-UA gateway, or robot simulators in this change; ingestion protocols stay a Node-RED flow concern.
- No prebuilt Grafana dashboards or alert rules beyond the datasource default and verification panels; dashboards evolve separately.
- No custom Node-RED Dockerfile unless extra nodes prove necessary.

## Decisions

- **Pin `influxdb:2.9.1` and `grafana:13.2.2`, float `nodered:latest`.** Rationale: Influx `latest` would silently jump to v3 Core; Grafana major behavior (Flux provisioning schema) is version-sensitive. Node-RED floats for class convenience. Alternative (pin `nodered:4.x`) reconsidered if a rebuild breaks flows; recorded as follow-up.
- **Auto-provisioning via `DOCKER_INFLUXDB_INIT_MODE=setup` plus an init script for the extra buckets.** Rationale: portability requires a fresh machine to reach the same state with one `up`; the image only auto-creates a single bucket from env, so the first bucket comes from `DOCKER_INFLUXDB_INIT_BUCKET` and the remaining two via a script in `/docker-entrypoint-initdb.d` using the same admin token. Alternative (manual UI creation) was the earlier plan and is rejected now because fresh clones would boot without buckets.
- **Three buckets over one bucket plus `robot_type` tag.** Rationale: payloads share almost no fields and have different rates/lifetimes; separate buckets keep schemas dense and allow independent retention set at provisioning time. Alternative (single `robots` bucket with `robot_type` tag) would simplify init to one bucket but produce sparse series and one shared retention. Buckets do not enforce tags, so `robot_id` discipline stays a writer contract. Note: `3d_printers` starts with a digit, so every Flux reference must quote the bucket name.
- **Operator-chosen admin token in `.env` before first boot.** Rationale: init needs a known token so Node-RED and Grafana share it with no copy-paste round trip; `.env.example` marks it required. Alternative (image-generated token) rejected because the value would have to be fished out of `docker logs` on every new machine.
- **Named volumes for InfluxDB/Grafana data, host directory for Node-RED `/data`.** Rationale: `influxdb2-data` and `grafana-data` survive `down`/`up`; Node-RED uses a host dir (`./nodered`) so `flows.json` stays git-reviewable AND editor saves work — a file bind mount of `flows.json` was tried and breaks Node-RED's atomic save (`EBUSY` on rename across mounts). Only `flows.json` is tracked; the rest of the host data dir is gitignored. Alternative (file bind mount) rejected after failing live verification.
- **One bridge network with `depends_on` healthy on InfluxDB `/health` plus `restart: unless-stopped`.** Rationale: removes cold-start race where Node-RED/Grafana dial Influx before it is ready; inter-service URLs use service names (`http://influxdb:8086`). Alternative (no ordering plus retry-in-flows) rejected as it pushes infra flakiness into flows.
- **Provisioned Grafana datasource, manual dashboards.** Rationale: datasource YAML makes org/URL/token wiring reproducible from `.env` interpolation while leaving dashboard design free. Alternative (all-manual datasource) rejected because every clone would repeat clicks.

## Risks / Trade-offs

- [Risk] `docker compose down -v` deletes the provisioned org/buckets with no in-repo backup → Mitigation: document named volumes as the persistence boundary and warn against `-v`; moving machines means fresh volumes plus the same `.env` to re-provision identically.
- [Risk] Token leaks via `flows.json` or provisioning YAML committed with real values → Mitigation: env indirection everywhere plus `.gitignore` on `.env` and `*_data` dirs; `.env.example` carries only placeholders.
- [Risk] Init vars apply only on an empty volume, so changing org/buckets later requires a volume reset → Mitigation: spec pins first-boot provisioning; tasks verify fresh-volume provisioning and document the reset path explicitly.
- [Risk] `nodered:latest` drifts major on rebuild → Mitigation: note the pinning tradeoff in proposal Impact; tasks include a verify-flows step after pull.
- [Risk] Extra Node-RED nodes (e.g. InfluxDB contrib) missing from stock image → Mitigation: try stock plus palette install first; custom Dockerfile is an explicit non-goal escape hatch, not assumed.

## Migration Plan

1. Fill `pia/.env` from `.env.example` (org, bucket names, chosen admin token, retentions); never commit `.env`.
2. `docker compose up -d` (first run pulls pinned images and provisions org plus `mir_robots`, `3d_printers`, `dobot`); wait for Influx `/health`, then verify Node-RED `:1880` and Grafana `:3000`.
3. Node-RED Influx nodes and the provisioned Grafana datasource use `http://influxdb:8086` with org/token from env; write one test point per bucket filtered by `robot_id`.
4. Rollback: `docker compose down` keeps data; `down -v` is destructive and re-provisions identically on next `up` with the same `.env`.
5. Move machines: copy the project plus `.env` values (never the `.env` file itself through git), run `up -d` on fresh volumes.

## Open Questions

- Final org name and per-bucket retentions (set via `.env` before first boot; changing them later needs a volume reset, which the tasks document).
- Shared admin token versus scoped write/read tokens (defaults to shared for simplicity; scoping later does not change bucket design).
- Per-robot versus unified Grafana dashboards and the exact Node-RED ingestion protocol per machine (flow-level concerns; compose provides ports and volumes either way).
- Follow-up: bake `node-red-contrib-influxdb` into a custom Node-RED image (verified missing from stock `nodered/node-red` 5.0.7; palette install works but lands in the untracked host data dir, so fresh clones lose it).
