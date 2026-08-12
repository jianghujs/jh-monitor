## Why

当前每日报告仍依赖发送时实时连主机取数、即时分析并逐台发送，链路容易受 SSH 连通性、主机瞬时状态和人工批量操作影响，既不稳定也不利于留痕追溯。需要把报告能力升级为“采集 -> 分析 -> 发送”三段式流水线，把原始数据和最终报告统一沉淀到 ES，降低发送链路风险并为补算、重发和后续周报能力打基础。

## What Changes

- 新增服务器报告配置能力，在 `route/templates/default/config.html` 提供 ES 连接参数和异常阈值配置入口，并由后端统一负责读取、校验、保存与默认初始化。
- 新增客户端报告原始数据采集链路：客户端定时采集系统状态，备份日志通过 filebeat 入库，原始数据按统一字段结构写入 ES 原始索引。
- 新增每日报告分析链路：`task.py` 从 ES 读取当天原始数据，按 `/www/server/jh-panel/scripts/report.py` 的既有口径生成单主机报告和全局概览报告，并写入报告索引。
- 新增统一报告发送链路：发送任务只读取已生成且通过校验的报告索引数据，固定发送“异常主机单机报告 + 全部主机概览报告”，并记录发送状态与失败原因。
- 统一客户端安装/更新路径、cron 注册、首轮执行、filebeat 采集和 ES 索引命名约定，为后续重算、补发和周报能力预留扩展点。

## Capabilities

### New Capabilities
- `host-report-configuration`: Manage ES connectivity and host report threshold settings through panel UI, backend validation, and JSON persistence.
- `host-report-collection`: Collect host runtime and backup source data on clients, standardize payloads, and ingest raw report data into ES on a scheduled cadence.
- `host-report-analysis`: Aggregate raw daily data from ES, apply existing report rules, and persist single-host and overview reports as structured documents plus HTML.
- `host-report-delivery`: Send validated daily reports from ES-backed report indices, limit single-host sends to abnormal hosts, and persist delivery status for retry/audit.

### Modified Capabilities
- None.

## Impact

- Affected code: `task.py`, `route/templates/default/config.html`, related front-end config JS/API handlers, `scripts/client/install.sh`, `scripts/client/install/debian.sh`, filebeat install/config assets, and new/updated client-side collector scripts.
- Data and storage: new JSON config files `data/report_config.json` and `data/es.json`; six ES indices for raw and analyzed report data; delivery status persistence.
- External systems: Elasticsearch becomes the central store for report raw data and generated reports; filebeat becomes part of the supported client install/update flow.
- Operations: report generation moves away from live host fetch at send time, with explicit validation, retry, and future recompute/resend workflows.
