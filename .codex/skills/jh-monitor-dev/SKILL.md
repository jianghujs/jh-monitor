---
name: jh-monitor-dev
description: Jianghu Monitor project development conventions for /www/server/jh-monitor. Use when Codex works on cloud monitor backend APIs, frontend pages, OpenSpec changes, HA management, task scripts, validation, or service restart for this project.
---

# JH Monitor Dev

## Scope

Use this skill for development under `/www/server/jh-monitor`.

## Project Layout

- Backend APIs live under `class/core/`, including HA/cloud monitor APIs.
- Shared adapters and helpers live under `class/plugin/`.
- Frontend templates live under `route/templates/`.
- Frontend JS/CSS lives under `route/static/`.
- Operational scripts live under `scripts/`.
- Runtime data lives under `data/`; avoid committing environment-specific runtime changes unless intentional.

## Restart

When a Jianghu Monitor change requires restarting the program, use:

```bash
jhm 1 -y
```

Do not use `jh 1 -y` for this project; that command is for Jianghu Panel.

## Validation

Use focused checks based on changed files:

- Python backend:

  ```bash
  python3 -m py_compile /www/server/jh-monitor/class/core/<file>.py
  ```

- Frontend JavaScript:

  ```bash
  node --check /www/server/jh-monitor/route/static/app/<file>.js
  ```

When changing browser-loaded JS or CSS, bump the query version in the corresponding template to avoid stale cache.

