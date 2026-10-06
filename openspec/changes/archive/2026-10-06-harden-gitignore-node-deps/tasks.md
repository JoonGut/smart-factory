# Tasks

## 1. Root gitignore hardening

- [x] 1.1 Append Node-RED runtime/secret redundancy block to root `.gitignore` (`**/node_modules/`, `**/.npm/`, `**/flows_cred.json`, `**/.flows*.backup`, `**/.config.nodes.json*`, `**/.config.runtime.json*`, `*.backup`, `*.log`, `.DS_Store`, `!pia/.env.example` with comments) and verify `git diff .gitignore` shows only the appended block
- [x] 1.2 Verify no tracked file becomes newly ignored by running `git status --short` and `git check-ignore -v pia/.env pia/.env.example pia/docker-compose.yml pia/grafana/provisioning/datasources/influxdb.yml` and confirming `.env.example`, compose, and provisioning paths are NOT ignored

## 2. Nested Node-RED ignore update

- [x] 2.1 Add `!package.json` and `!package-lock.json` negations (with comment) to `pia/nodered/.gitignore` keeping `*`, `!.gitignore`, `!flows.json` intact, and verify file content matches design
- [x] 2.2 Verify ignore matrix with `git check-ignore -v pia/nodered/node_modules pia/nodered/.npm pia/nodered/flows_cred.json pia/nodered/.config.nodes.json pia/nodered/.config.runtime.json pia/nodered/settings.js` all reporting ignored, and `git check-ignore pia/nodered/flows.json pia/nodered/package.json pia/nodered/package-lock.json` reporting NOT ignored (exit non-zero)

## 3. Reproducibility and secret checks

- [x] 3.1 Verify Node-RED manifest declares InfluxDB nodes by running `python3 -c "import json; print(json.load(open('pia/nodered/package.json'))['dependencies'])"` showing `node-red-contrib-influxdb`, and `npm ci --dry-run` (or `npm install --dry-run`) in `pia/nodered/` succeeding without missing-node implications
- [x] 3.2 Run secret scan with `grep -r "REPLACE_WITH" pia/.env.example` confirming placeholders only, plus `git status --short pia/nodered/` showing `flows.json`, `package.json`, `package-lock.json` as the only committable runtime files and no `flows_cred.json` or `node_modules` entries, and verify temporary removal of `pia/nodered/.gitignore` still leaves `flows_cred.json` and `node_modules` ignored via root
