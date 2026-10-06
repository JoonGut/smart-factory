# smart-factory
Recogida de datos para los robots de somorrostro

## Monitoring stack (`pia/`)

One compose stack: Node-RED ingests robot data, InfluxDB stores it per
robot type, Grafana visualizes it. The InfluxDB org and buckets are
created once by hand in the InfluxDB UI; compose only connects to them.

| Service  | Image                  | Host port | Notes                                    |
|----------|------------------------|-----------|------------------------------------------|
| influxdb | `influxdb:2.9.1`       | 8086      | Pinned: `latest` now points to v3 Core   |
| nodered  | `nodered/node-red:latest` | 1880   | Floating tag, see drift note below       |
| grafana  | `grafana:13.2.2`       | 3000      | Pinned: Flux provisioning is versioned    |

```bash
cp pia/.env.example pia/.env   # fill in the manual InfluxDB org + token
docker pull influxdb:2.9.1
docker pull nodered/node-red:latest
docker pull grafana/grafana:13.2.2
docker compose -f pia/docker-compose.yml up -d
```

Drift note: `nodered:latest` floats on purpose for class convenience, so a
future rebuild can jump a Node-RED major. If flows break after a pull, pin
to the last working major (e.g. `nodered/node-red:4`) instead.
