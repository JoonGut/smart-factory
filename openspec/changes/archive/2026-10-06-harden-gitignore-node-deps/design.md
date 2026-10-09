# Design

## Context

See proposal.md Why. Current state (observed):
- Root `.gitignore` covers `pia/.env`, `**/.env`, `*_data/`, `data/` only.
- `pia/nodered/.gitignore` is `*` + `!.gitignore` + `!flows.json`, so today `node_modules/`, `.npm/`, `flows_cred.json` (99 bytes, key `$`), `.config.*.json`, `*.backup`, `package.json` (declares `node-red-contrib-influxdb ~0.7.0`), and default `settings.js` are all ignored by the nested file alone (`git check-ignore -v` confirms).
- `pia/nodered/flows.json` (10 nodes) uses `influxdb` config + `influxdb out` nodes; without the manifest a fresh clone trusts `nodered:latest` to ship them (risk already noted in the archived monitoring-stack proposal).
- `pia/.env` (real values) is correctly ignored; `pia/.env.example` is correctly tracked. InfluxDB/Grafana state lives in named volumes, so no host data dirs need new rules beyond defense-in-depth.

## Goals / Non-Goals

**Goals:**
- Make secret/runtime exclusion survive deletion of the nested gitignore (redundancy without changing tracked set, except the two manifests).
- Make Node-RED node set reproducible via tracked `package.json` + `package-lock.json`.
- Keep the tracked set minimal and reviewable: `flows.json` + manifests + provisioning/compose/env-template.

**Non-Goals:**
- No custom Node-RED Dockerfile, no image pin change, no flow or provisioning edits.
- No `settings.js` customization (stays ignored; revisit only if customized).
- No secrets rotation or migration of existing checkouts beyond gitignore semantics.

## Decisions

- **Two-layer ignore (nested precise + root redundant) over single-file consolidation.**
  Rationale: nested file stays the source of truth for `/data` semantics (`*` default-deny); root gains explicit `**/` patterns so `git check-ignore` still passes if nested is lost. Alternative (root only) would weaken per-dir clarity for future `bda/` or `sbd/` mounts; alternative (nested only) is the current single point of failure.
- **Track `package.json` + `package-lock.json` via `!package.json` / `!package-lock.json` negations in nested file.**
  Rationale (option B, user-confirmed): declares `node-red-contrib-influxdb ~0.7.0` per clone; enables `npm ci`. Alternative (option A, keep ignoring) was rejected because it couples reproducibility to the floating `nodered:latest` tag. `package-lock.json` diffs on bumps are intended signal, not noise.
- **Keep `settings.js` ignored.**
  Rationale: observed file is the 26k-line Node-RED default with no customization; tracking it would add review noise and merge conflicts. If customized later, add `!settings.js` then.
- **Explicit secret/runtime pattern list in root (not just `*`).**
  `**/node_modules/`, `**/.npm/`, `**/flows_cred.json`, `**/.flows*.backup`, `**/.config.nodes.json*`, `**/.config.runtime.json*`, `*.backup`, plus `*.log`, `.DS_Store`. Explicitness makes `git status` audits and the spec's "no real token" scenario checkable without reading the nested file.
- **Add `!pia/.env.example` guard in root.**
  Rationale: documents that the template must stay tracked even as `**/.env` broadens; prevents a future `*.example` or `.env*` rule from accidentally hiding it.

## Risks / Trade-offs

- [Risk] Tracked `package-lock.json` churn on every `npm install` with different npm versions → Mitigation: tasks pin `npm ci` for verification and note lockfile is authoritative.
- [Risk] `*.backup` in root could hide a legitimately trackable `*.backup` elsewhere → Mitigation: scope is intentional; no such file exists today (`ls` shows only Node-RED backups); negation can be added per path if needed.
- [Risk] `**/node_modules/` in root is broader than `pia/nodered/` → Mitigation: desired; future `bda/`/`sbd/` JS tooling gets the same protection for free.
- [Risk] Existing clones with already-committed `node_modules` (none today — dir is untracked) would need `git rm --cached` → Mitigation: tasks verify `git status` shows `??` only for intended files; no history rewrite needed.

## Migration Plan

- Edit two files only: root `.gitignore` (append block) and `pia/nodered/.gitignore` (add two negations + comment update).
- No container rebuild, no volume reset, no token rotation. Rollback is `git checkout -- .gitignore pia/nodered/.gitignore`.
- Verify with `git check-ignore -v` matrix and `git status --short` before/after; verify `npm ci` still resolves the InfluxDB nodes.

## Open Questions

- None blocking. Follow-up noted but out of scope: whether to pin `nodered:latest` to a digest now that deps are declared (reduces drift but adds bump toil).
