## Why

江湖面板主备切换目前依赖分散脚本和人工判断，云监控缺少统一入口来查看两台机器的实际主备状态、自检结果、切换进度和日志。两台主备机器部署在不同机房且各自有云监控时，还需要让任意一边云监控都能看到两台机器各自的状态和日志。

## What Changes

- 新增江湖云监控“主备管理”模块，提供简洁 table 列表、主备组详情多标签页、手动切换、告警提醒和日志查看。
- 新增江湖面板 `ha_manager` 插件，用于绑定对端面板、配置云监控地址、自检、执行上下线流程、上报状态和日志。
- 插件绑定改为输入对方公网 IP、SSH 端口、SSH 用户和对方公钥，测试 SSH 后保存；`pair_id` 由系统生成或云监控下发，不在界面手动填写。
- 云监控地址作为插件独立配置项，默认留空；留空时插件只做本机能力，不上传状态和日志。
- 第一版只支持手动切换。切换可由云监控发起，也可由插件首页本地发起；切换确认弹窗承载上线/下线参数和风险确认。
- 切换执行覆盖 `/www/server/jh-panel/scripts/os_tool/vm/default/switch__generate_offline.sh` 和 `/www/server/jh-panel/scripts/os_tool/vm/default/switch__generate_online.sh` 的全部流程。
- 切换状态和日志统一通过 API 上报云监控，不使用 filebeat/ES；云监控在 `/www/server/jh-monitor/logs/ha_switch/` 保存每次切换日志文件，SQLite 只存状态和日志地址。
- 支持双机房双云监控：两边插件通过 SSH 采集对端状态和日志，各自向本机房云监控聚合上报“本机 + 对端”数据。
- 云监控在切换完成后回调配置的外部地址，例如江湖数据同步切换数据库接口。

## Capabilities

### New Capabilities

- `ha-management-ui`: Cloud monitor SHALL provide a logged-in HA management UI with table list and multi-tab group detail views.
- `ha-plugin-binding`: Jianghu panel SHALL provide the `ha_manager` plugin UI for peer binding, cloud monitor configuration, local overview, health checks, and local manual switching.
- `ha-switch-orchestration`: The system SHALL support manual HA switch orchestration through cloud monitor desired state and plugin-executed offline/online phases.
- `ha-status-log-reporting`: The system SHALL report actual HA state, switch progress, and per-host logs through APIs, with retry and file-backed cloud monitor logs.
- `ha-peer-aggregation`: In dual-datacenter deployments, each plugin SHALL collect peer state/logs over SSH and aggregate both hosts to its local cloud monitor.
- `ha-alert-callback`: The cloud monitor SHALL classify HA alerts and invoke configured callbacks after successful actual master switch.

### Modified Capabilities

- None.

## Impact

- Affected cloud monitor code: `route/__init__.py`, `route/templates/default/layout.html`, new `route/templates/default/ha_management.html`, new `route/static/app/ha_management.js`, future `class/core/ha_api.py` or equivalent, public plugin API handlers, SQLite schema, and log writer under `/www/server/jh-monitor/logs/ha_switch/`.
- Affected panel code: new `/www/server/jh-panel/plugins/ha_manager/` plugin, local plugin config/state/log files, SSH binding/test flow, and wrappers around existing offline/online scripts.
- APIs: new logged-in HA management APIs and signed public plugin APIs for pulling desired state, reporting state, reporting switch events, acknowledging phases, and callback configuration.
- Data: new HA pair/state/switch-run/callback records in SQLite; switch logs stored as files, not ES documents.
- Operations: two panel servers both install `ha_manager`; operators bind peer SSH, optionally configure cloud monitor URL, and perform manual switch from either cloud monitor or the plugin homepage.
