# Tasks

## 1. Env and repo scaffolding

- [x] 1.1 Add `pia/.env.example` with Influx URL, init username/password, org, three bucket names (`mir_robots`, `3d_printers`, `dobot`), retention, admin token, and Grafana admin placeholders, and verify every variable the compose file interpolates has a placeholder entry
- [x] 1.2 Update `.gitignore` for `.env` and Docker data dirs, and verify `git status` on a fresh clone shows no real token or data dir as committable
- [x] 1.3 Create repo mount sources for Node-RED flows and Grafana provisioning (`bda/nodered/`, `bda/grafana/provisioning/datasources/` or `pia/` equivalent), and verify the directories exist with placeholder files so bind mounts resolve

## 2. Compose stack

- [x] 2.1 Author `pia/docker-compose.yml` with pinned `influxdb:2.9.1`, `grafana:13.2.2`, `nodered:latest` on one bridge network, host ports 1880/8086/3000, named volumes, `restart: unless-stopped`, InfluxDB `DOCKER_INFLUXDB_INIT_*` setup env plus init-script mount, and verify `docker compose config` renders without interpolation errors
- [x] 2.2 Add InfluxDB `/health` healthcheck plus `depends_on` healthy ordering for Node-RED and Grafana, and verify a cold `docker compose up -d` converges with no manual restarts and `docker compose ps` shows all healthy/running
- [x] 2.3 Document the images table and the `nodered:latest` drift tradeoff in the stack README section, and verify the documented pull commands match the compose pins

- [x] 2.4 Add the InfluxDB init script creating the two extra buckets with retention on first boot, and verify a fresh volume provisions org plus all three buckets with no manual steps

## 3. Manual InfluxDB provisioning

- [x] 3.1 Document the first-boot auto-provisioning (fill `.env`, `up -d` provisions org, `mir_robots`, `3d_printers`, `dobot` with retentions) plus the `down -v` re-provisioning note, and verify the doc runs as written against a fresh volume
- [x] 3.2 Write one test point per bucket tagged `robot_id` and query each back with a `robot_id` filter, and verify all three buckets return their point and a missing-bucket name fails visibly in logs

## 4. Node-RED wiring

- [x] 4.1 Persist Node-RED `/data` in a host directory bind mount (file bind mounts break editor saves) with only `flows.json` tracked, and verify an editor-created flow survives `docker compose down` plus `up` (without `-v`)
- [x] 4.2 Configure InfluxDB v2 output (URL `http://influxdb:8086`, org, token from env) routing MiR data to `mir_robots`, printer data to `3d_printers`, Dobot data to `dobot` all tagged `robot_id`, and verify one live write per bucket is queryable by `robot_id`
- [x] 4.3 Confirm stock image covers required nodes or record the custom-Dockerfile follow-up, and verify the flows start with no missing-node warnings in the Node-RED log

## 5. Grafana provisioning

- [x] 5.1 Add a provisioned Flux datasource (URL, org, token via env) as the single datasource for all buckets, and verify Grafana starts with the datasource listed as working without manual clicks
- [x] 5.2 Add one verification panel per bucket using `from(bucket: "<name>")` filtered by `robot_id`, and verify all three panels return data through the same datasource
- [x] 5.3 Document the datasource-plus-token rotation steps in the stack docs, and verify the documented steps reload Grafana provisioning successfully

## 6. Integration checks

- [x] 6.1 Run restart persistence check (write points, `down`, `up`, re-query) and verify data, flows, and datasource all survive
- [x] 6.2 Run secret scan (`grep` for token values across committed files) plus fresh-clone `up` smoke test (health endpoints on 1880/8086/3000), and verify no real secret is committed and all three endpoints respond
