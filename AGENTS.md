# Repository Guidelines

## Project Structure & Module Organization
- `class/core/`: Flask-style API modules and panel business logic, e.g. `host_api.py`, `config_api.py`.
- `class/es/`: Elasticsearch query builders, services, schema definitions, and init scripts.
- `class/plugin/`: shared adapters such as `es.py`, ORM helpers, and utility wrappers.
- `route/templates/` and `route/static/`: server-rendered HTML, JS, CSS, and report templates.
- `scripts/`: operational scripts, collectors, installers, report analysis/sending, and maintenance tools.
- `test/`: focused validation scripts such as `test_report_es_persistence.py` and ES/debug helpers.
- Runtime/config data lives under `data/`; avoid committing secrets or environment-specific JSON changes unless intentional.

## Build, Test, and Development Commands
- `python3 -m py_compile class/core/host_api.py`: quick syntax check for edited Python modules.
- `python3 test/test_report_es_persistence.py --host-id <HOST_ID>`: verify report generation and ES persistence.
- `python3 class/es/init/init.py --check-only --month YYYY-MM`: inspect report indices/data streams for a month.
- `python3 class/es/init/init.py --month YYYY-MM`: initialize/update report indices and monthly data streams.
- `python3 scripts/test_pve_report_pipeline_send.py --host-id <HOST_ID> --dry-run --send`: exercise report generation/send flow without real notifications.

## Coding Style & Naming Conventions
- Python uses 4-space indentation, snake_case functions, and small focused helpers.
- Keep files ASCII unless the file already contains Chinese/UI text that must remain.
- Prefer existing service/query split: put ES query bodies in `class/es/query/`, read/write orchestration in `class/es/service/`.
- Frontend JS in `route/static/app/` follows plain jQuery/Vue-min style; keep browser-side changes minimal and consistent.

## Testing Guidelines
- There is no single test runner; use targeted scripts in `test/` and `scripts/` based on the area changed.
- Name new checks `test_<feature>.py` and keep them executable with `python3 <path>`.
- For ES/report changes, validate both syntax (`py_compile`) and behavior (`test_report_es_persistence.py`).

## Commit & Pull Request Guidelines
- Recent history uses short, topic-first commits such as `报告查询问题`, `报表数据流`, `bugfix`.
- Prefer concise commit subjects describing the user-visible change or fix.
- PRs should include: changed modules, validation commands run, config/index impacts, and screenshots for template/UI updates.

## Security & Configuration Tips
- ES settings are read from `data/es.json`; confirm host, auth, and target cluster before running init or migration scripts.
- Do not hard-code credentials in scripts or templates.
- When changing report mappings or data streams, keep backward compatibility with existing `host-report-*` indices unless a migration is explicitly planned.
