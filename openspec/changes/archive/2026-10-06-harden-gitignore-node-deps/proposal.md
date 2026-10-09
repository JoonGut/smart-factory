# Proposal

## Why

Node-RED's `/data` bind mount mixes three things: source to track (`flows.json`), reproducible dependency manifest (`package.json` / `package-lock.json`), and local-only runtime/secrets (`node_modules/`, `.npm/`, `flows_cred.json`, `.config.*.json`, `*.backup`). Root `.gitignore` only covers `.env` and data dirs, so all Node-RED hygiene currently hangs on a single nested `pia/nodered/.gitignore` (`*` + `!flows.json`). If that file is deleted or moved, a `git add` would commit secrets and megabytes of runtime. At the same time the nested rule ignores `package.json`, so a fresh clone loses the `node-red-contrib-influxdb` declaration and depends on the floating `nodered:latest` image shipping the right nodes.

## What Changes

- Harden root `.gitignore` with defense-in-depth entries for Node-RED runtime, secrets, and OS/log noise, without changing what is tracked today except the two manifests below.
- Track `pia/nodered/package.json` and `pia/nodered/package-lock.json` (add negations to nested gitignore) so `node-red-contrib-influxdb ~0.7.0` is reproducible per clone.
- Keep ignored: `node_modules/`, `.npm/`, `flows_cred.json` (+ `.flows*.backup`), `.config.nodes.json*`, `.config.runtime.json*`, `*.backup`, `settings.js` (still default, uncustomized), `.env` (all paths).
- Keep tracked: `flows.json`, `.env.example`, `docker-compose.yml`, `influxdb/initdb.d/*`, `grafana/provisioning/*`, `grafana/dashboards/*`.
- Document the `!pia/.env.example` guarantee so the template can never be accidentally ignored.

## Capabilities

### New Capabilities

- None. No new runtime behavior is introduced.

### Modified Capabilities

- `monitoring-stack`: extend the "Secrets stay out of version control" requirement to explicitly cover Node-RED credential/runtime files, and extend the fresh-clone reproducibility contract to include the Node-RED dependency manifest.

## Impact

- Affects `.gitignore` (root) and `pia/nodered/.gitignore` only. No compose, InfluxDB, Grafana, or flow logic changes.
- Dependencies: none new. Risk is low; the main tradeoff is that tracked `package-lock.json` will produce diffs on `npm install` version bumps, which is intended.
- Fresh clones gain `npm ci`-style reproducibility; existing checkouts lose nothing except no longer being able to accidentally commit `flows_cred.json` or `node_modules/`.
