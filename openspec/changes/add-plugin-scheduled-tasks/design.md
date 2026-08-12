## Context

Jianghu Panel already has a long-running `task.py` process that hosts panel-level background work. Plugins currently support installation, status checks, and shell-based execution, but there is no first-class way to declare periodic plugin functions that should run only when the plugin is installed.

For `ha_manager`, periodic work is needed for cloud-monitor state reporting and desired-state polling. Putting a separate daemon or crontab inside the plugin would duplicate lifecycle control and make uninstall/reinstall behavior harder to reason about.

The design must fit existing plugin loading conventions, stay fast in the panel task loop, and avoid one plugin’s failure blocking other panel tasks.

## Goals / Non-Goals

**Goals:**

- Let plugins declare periodic function calls in `info.json`.
- Let `task.py` discover installed plugins and execute declared tasks automatically.
- Keep execution scoped to a whitelist of plugin functions and JSON arguments.
- Support interval, timeout, enable/disable, and simple execution state tracking.
- Apply the mechanism to `ha_manager` without requiring extra daemons or crontab entries.

**Non-Goals:**

- Do not redesign the whole panel task engine.
- Do not add arbitrary remote code execution or shell strings from plugin metadata.
- Do not add a new cloud-monitor API just for scheduler registration.
- Do not move plugin business logic out of `index.py` in this change.

## Decisions

### 1. Use `info.json.tasks` as a declarative task list

Each task entry will describe one method call by `func` and `args`, plus scheduling metadata such as `interval`, `timeout`, and `enabled`.

Rationale: `info.json` is already the plugin’s install-time metadata. Keeping task declarations there makes the behavior visible during plugin install and easy to remove on uninstall.

Alternatives considered:

- A separate scheduler file under the plugin directory. This adds another artifact to maintain and makes installation metadata less obvious.
- A database table for plugin task definitions. That would complicate install/uninstall and make the definition less portable with the plugin package.

### 2. Let `task.py` own scheduling and execution

The panel task process will scan installed plugins, load their metadata, and trigger declared functions when their interval is due.

Rationale: `task.py` already runs as the panel’s always-on coordinator. Reusing it keeps lifecycle unified and avoids an extra service per plugin.

Alternatives considered:

- Plugin-owned cron jobs. This fragments scheduling control and makes uninstall cleanup harder.
- A new scheduler daemon. This duplicates `task.py` behavior and adds another failure domain.

### 3. Execute only whitelisted plugin functions

The scheduler will invoke only explicit `func` names declared in `info.json`, and those calls will be mapped to `python3 /www/server/jh-panel/plugins/<name>/index.py <func> <args_json>`.

Rationale: This keeps the scheduler simple and avoids turning plugin metadata into unrestricted command execution.

Alternatives considered:

- Allow arbitrary shell strings. That is too broad and unsafe for a metadata-driven scheduler.
- Call functions through an imported Python module in-process. That is faster but increases coupling and makes per-plugin isolation weaker.

### 4. Keep execution state lightweight and bounded

The scheduler will track last run time, last success/failure, and a short error summary per plugin task. It should not store full task history in the scheduler loop.

Rationale: The panel task process already runs continuously and should not accumulate large per-task logs or state.

Alternatives considered:

- Persisting every run result in detail. That adds storage overhead and is unnecessary for the first version.

### 5. Make task execution failure isolated

If one plugin task fails, times out, or exits non-zero, the scheduler will record the failure and continue running other plugin tasks and panel tasks.

Rationale: This preserves the panel’s main monitoring duties even when a plugin is misconfigured or temporarily unreachable.

Alternatives considered:

- Failing the whole task loop. That would make one broken plugin affect unrelated panel work.

## Risks / Trade-offs

- [Plugin task output grows noisy] → Keep only short summaries in the scheduler state and cap captured output.
- [Long-running plugin functions block the task loop] → Enforce per-task timeout and isolate execution per task.
- [Metadata drift between installed version and declared tasks] → Read from the installed plugin’s current `info.json` on each scan and treat uninstall as authoritative.
- [Repeated retries create load spikes] → Add a simple minimum interval and backoff on repeated failure.

## Migration Plan

1. Add the `tasks` declaration to `ha_manager/info.json`.
2. Extend `task.py` to scan installed plugins for declared tasks and execute due calls.
3. Add small scheduler state tracking for last run, last error, and next eligible run time.
4. Verify `ha_manager` reports and polls correctly when the panel task process is running.
5. Roll back by removing the `tasks` declaration from plugin metadata and keeping the scheduler parser tolerant of absent or empty task lists.

## Open Questions

- Should scheduler state live in a dedicated panel data file, or be kept entirely in memory and recomputed on restart?
- Should `args` accept only JSON objects, or also allow arrays and primitives for future flexibility?
- Should failed tasks use fixed retry intervals or exponential backoff after repeated failure?
