# First-boot InfluxDB provisioning

The stack provisions the organization, the three buckets, and the admin
token automatically on first boot from `pia/.env` values. No UI clicks
needed — but `.env` must be filled in BEFORE the first `up`, because init
vars apply only on empty volumes.

## Steps (fresh machine or fresh volumes)

1. `cp pia/.env.example pia/.env` and set at minimum:
   `INFLUXDB_INIT_PASSWORD`, `INFLUXDB_ORG`, `INFLUXDB_TOKEN`.
   Bucket names (`mir_robots`, `3d_printers`, `dobot`) and
   `INFLUXDB_RETENTION` already default sensibly. Never commit `.env`.
2. `docker compose -f pia/docker-compose.yml up -d`
3. Wait for InfluxDB healthy, then confirm the layout:
   open http://localhost:8086 and log in, or query the buckets API —
   `mir_robots` comes from `DOCKER_INFLUXDB_INIT_BUCKET`, `3d_printers`
   and `dobot` from `pia/influxdb/initdb.d/02-extra-buckets.sh`.
4. Sanity check: each bucket answers a `robot_id`-filtered Flux query
   (write one test point per bucket, query it back).

This procedure was verified end to end against a fresh volume: first boot
provisioned the org plus all three buckets with the configured retention
and the chosen token, with no manual steps.

## Changing org / buckets / retention later

Init runs once. To change any provisioned value: stop the stack,
`docker compose down -v` (destroys ALL points — back up first via the
InfluxDB backup API if the data matters), update `.env`, and `up -d`
again. Normal `down`/`up` cycles and container recreates keep everything.

## Rotating the API token / reloading Grafana provisioning

Node-RED and Grafana read `INFLUXDB_TOKEN` from the container environment,
and Grafana loads `pia/grafana/provisioning/` at boot. To rotate:

1. Mint the replacement token in InfluxDB (UI: Data > API Tokens, or the
   authorizations API) with read/write on the three robot buckets.
2. Set `INFLUXDB_TOKEN` to the new value in `pia/.env`.
3. Recreate the dependents so they pick up the new environment:
   `docker compose -f pia/docker-compose.yml up -d`
   (recreates Node-RED and Grafana; InfluxDB data volumes are untouched,
   no re-provisioning happens).
4. Verify: Grafana datasource health reports working
   (`/api/datasources/uid/influxdb/health`) and one `robot_id`-filtered
   query per bucket returns rows; Node-RED writes succeed (no 401s in its
   log).
5. Retire the old token in InfluxDB.

Reloading provisioning alone (no token change, e.g. after editing a
dashboard or datasource file): `docker restart smart-factory-grafana`
and confirm the datasource still reports healthy. This rotation was
exercised end to end: token switched, dependents recreated, health and
queries verified, then switched back with the same verification.
