## Why

当前防火墙同步、主备 NAS 同步等脚本任务只在各自机器上留下非统一日志，云监控无法按任务频率和执行结果纳入日报，也缺少一个面板入口来维护这些脚本任务和复制标准安装命令。需要新增脚本日志监控能力，让运维脚本通过统一命令写入结构化日志，由 filebeat 入 ES，并在每日主机报告中形成异常和提醒结论。

## What Changes

- 新增“监控任务”管理页，参考主机管理页提供任务列表、搜索、添加、编辑、删除、启停和复制安装命令能力。
- 新增 `monitor_task` 本地表和后端管理 API，用于维护任务名称、归属主机、日志路径、检查频率、启用状态、安装状态和最近一次日报分析状态。
- 新增客户端初始化脚本下载、任务注册和安装状态回写接口，让被监控主机执行面板生成的安装命令即可完成任务注册、日志路径准备、独立的 filebeat 任务日志 input 配置和 `jh-monitor-task-log` 下发。
- 新增 `jh-monitor-task-log` 标准日志命令，业务脚本通过该命令写入 JSON Lines 任务结果日志，避免自行拼接 JSON。
- 新增 `host-monitor-task-event` ES 任务日志索引模板和查询能力，按 `task_id + host_id` 获取最近任务事件。
- 在日报生成阶段读取启用的监控任务并即时分析任务状态，回写 `monitor_task.last_status/last_msg/last_run_at/last_analyse_at`，并把异常或提醒纳入单机报告和总览报告。
- 第一版不新增独立实时分析定时器；管理页展示“最近一次日报分析结果”。

## Capabilities

### New Capabilities
- `monitor-task-management`: Manage script log monitoring tasks in the panel, including task metadata, enablement, lifecycle operations, install command generation, and recent analysis status display.
- `monitor-task-client-setup`: Provide public client setup endpoints and scripts that register tasks, install the standard logging command, configure filebeat inputs, and report install status.
- `monitor-task-log-ingestion`: Standardize task result log format and ingest task events into the shared Elasticsearch index `host-monitor-task-event`.
- `monitor-task-report-analysis`: Analyze enabled monitor tasks during daily report generation, classify task status by frequency and latest event state, persist recent analysis results, and include task findings in single-host and overview reports.

### Modified Capabilities
- None.

## Impact

- Affected code: `route/__init__.py`, `route/templates/default/layout.html`, new `route/templates/default/monitor_task.html`, new `route/static/app/monitor_task.js`, new `class/core/monitor_task_api.py`, updated `class/core/pub_api.py`, `scripts/report_analyser.py`, report templates, ES init/model/query/service modules, and client install assets/scripts.
- Data and storage: new SQLite table `monitor_task`; new ES index/template `host-monitor-task-event`; new task analysis fields embedded in report documents and report data streams.
- External systems: client hosts need filebeat configured with task-log-specific input files isolated from existing host collection inputs; Elasticsearch stores task event documents; business scripts call `/usr/local/bin/jh-monitor-task-log` after task execution.
- Operations: operators add a task in the panel, copy and run the generated install command on the monitored host, then rely on the next daily report to update task status and surface warnings/errors.
