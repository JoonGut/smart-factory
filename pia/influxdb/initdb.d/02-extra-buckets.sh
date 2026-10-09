#!/bin/bash
# Se ejecuta una vez durante la primera inicializacion (volumen vacio) a traves del punto de entrada de InfluxDB 2.x,
# DESPUeS de que se haya creado `DOCKER_INFLUXDB_INIT_BUCKET` (el bucket MiR).
# Crea los buckets de los robots restantes de forma idempotente.
set -euo pipefail

TOKEN="${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN:?DOCKER_INFLUXDB_INIT_ADMIN_TOKEN is required}"
ORG="${INFLUXDB_ORG:?INFLUXDB_ORG is required}"
RETENTION="${INFLUXDB_RETENTION:-30d}"
# During entrypoint initialization influxd listens on :9999 (not :8086).
HOST="http://localhost:9999"

for BUCKET in "${INFLUXDB_BUCKET_PRINTER:?}" "${INFLUXDB_BUCKET_DOBOT:?}"; do
  if influx bucket list -n "$BUCKET" -o "$ORG" -t "$TOKEN" --host "$HOST" --hide-headers 2>/dev/null | grep -q .; then
    echo "initdb.d: bucket $BUCKET already exists, skipping"
  else
    influx bucket create -n "$BUCKET" -o "$ORG" -r "$RETENTION" -t "$TOKEN" --host "$HOST"
    echo "initdb.d: bucket $BUCKET created (retention $RETENTION)"
  fi
done
