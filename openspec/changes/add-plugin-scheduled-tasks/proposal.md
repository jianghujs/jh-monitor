## Why

Some Jianghu Panel plugins need lightweight periodic work after installation, such as `ha_manager` polling cloud monitor desired state and reporting HA status. Today that scheduling responsibility is unclear: putting timers inside each plugin would duplicate daemon logic, while manual execution cannot provide stable cloud-monitor data flow.

## What Changes

- Add a declarative plugin scheduled task convention in plugin `info.json`.
- Let `/www/server/jh-panel/task.py` discover installed plugins with declared tasks and execute them automatically at their configured interval.
- Use `func` plus JSON `args` to describe which plugin `index.py` method to call.
- Add per-task timeout, enable flag, minimum interval, and lightweight execution state so one plugin task cannot block panel-wide monitoring.
- Apply the convention to `ha_manager` so HA state reporting and desired-state polling are triggered by the Jianghu Panel task process when the plugin is installed and cloud monitor reporting is configured.
- Do not add plugin-owned crontab entries, systemd services, or extra daemon processes for this scheduling path.

## Capabilities

### New Capabilities

- `plugin-scheduled-tasks`: Plugins can declare periodic `index.py` function calls in `info.json`, and the Jianghu Panel task process executes those functions for installed plugins according to the declaration.

### Modified Capabilities

None.

## Impact

- Affected Jianghu Panel code: `/www/server/jh-panel/task.py`, plugin metadata parsing, and plugin `info.json` files that opt in to scheduled tasks.
- Affected HA plugin code/config: `/www/server/jh-panel/plugins/ha_manager/info.json` declares `poll_monitor` and `report_state` scheduled tasks; existing `index.py` methods remain the execution target.
- Affected cloud monitor behavior: `/www/server/jh-monitor` receives HA reports more reliably through existing `/pub/ha_*` APIs; no new cloud monitor public API is required for the scheduler itself.
- Runtime data may include a small scheduler state/log file under the panel data or plugin runtime directory to track last run, failures, and output summaries.
