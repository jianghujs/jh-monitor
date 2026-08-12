## Context

`jh-monitor` 已经有主机管理页、客户端安装脚本、filebeat 采集能力、ES 报告索引和每日主机报告流水线。当前脚本类任务（如防火墙同步、主备 NAS 同步）没有统一的面板管理入口，也没有标准日志格式和中心化状态分析能力，导致任务失败只能依赖人工查看远端日志。

现有页面路由通过 `route/__init__.py` 的页面白名单和 API class 白名单控制，主机管理页由 `route/templates/default/host.html` 与 `route/static/app/host.js` 实现。客户端免登录接口集中在 `/pub/<reqAction>` 并落到 `class/core/pub_api.py`，适合承载安装脚本下载、注册和安装状态回写。日报生成逻辑集中在 `scripts/report_analyser.py`，已经负责生成单机报告、总览报告、HTML 内容和发送状态所需字段。

## Goals / Non-Goals

**Goals:**
- 提供一个参考主机管理页风格的“监控任务”管理页，让操作员能维护脚本任务并复制安装命令。
- 通过本地 `monitor_task` 表保存任务定义、安装状态和最近一次日报分析结果。
- 让客户端执行安装命令后完成标准日志命令、日志路径和 filebeat input 的幂等配置。
- 将任务结果日志写入统一 ES 索引 `host-monitor-task-event`，并提供按任务和主机查询最近事件的能力。
- 在日报生成阶段分析启用任务，更新任务最近分析状态，并把异常或提醒纳入单机和总览报告。

**Non-Goals:**
- 第一版不新增独立实时分析定时器，管理页展示最近一次日报分析结果。
- 第一版不做复杂状态大屏、趋势图、历史事件检索页或手动重算入口。
- 第一版不自动安装 filebeat；安装脚本检测 filebeat，不满足条件时回写安装失败和原因。
- 第一版不要求业务脚本改为托管执行，只要求业务脚本在结束时调用 `jh-monitor-task-log`。

## Decisions

### 1. Add a dedicated monitor task page and API class

- Decision: 新增 `/monitor_task` 页面、`route/templates/default/monitor_task.html`、`route/static/app/monitor_task.js` 和 `class/core/monitor_task_api.py`，并把 `monitor_task` 加入页面白名单和 API class 白名单。
- Rationale: 监控任务有独立生命周期和安装命令，不适合塞进主机管理页；沿用现有动态路由和 jQuery/layer 页面风格，改动最贴合现有系统。
- Alternatives considered:
  - 放到主机详情页：入口更贴近单台主机，但不方便跨主机检索任务和批量查看最近分析状态。
  - 只提供 API 不做页面：实现更小，但无法满足操作员复制安装命令和维护任务的需求。

### 2. Store task definitions in SQLite and keep ES only for events

- Decision: 任务定义、安装状态和最近分析结果保存在本地 SQLite `monitor_task` 表；任务执行事件保存在 ES `host-monitor-task-event`。
- Rationale: 任务定义是面板配置数据，适合与 `host` 表同库管理；执行事件是时序日志，适合 ES 查询最近事件和后续扩展历史检索。
- Alternatives considered:
  - 全部写 ES：配置管理和事务更新变复杂，也不符合当前主机配置保存在 SQLite 的习惯。
  - 全部写 SQLite：近期事件查询可做，但 filebeat 已经是日志采集通道，放弃 ES 会丢失集中检索能力。

### 3. Generate install commands server-side

- Decision: 管理页调用后端 API 获取安装命令，前端只展示和复制，不拼接 shell 参数。
- Rationale: server 地址、task_id、host_id、shell 参数转义和后续可能的注册签名都应由后端统一控制，减少复制命令不一致和注入风险。
- Alternatives considered:
  - 前端直接拼接命令：实现简单，但会复制服务端地址和参数转义逻辑，后续增加 token 时需要改前端。

### 4. Use public client endpoints only for setup flow

- Decision: `/pub/get_monitor_task_install_script` 返回安装脚本，`/pub/register_monitor_task` 执行任务 upsert，`/pub/update_monitor_task_install_status` 回写安装状态；管理类操作仍走登录态 `/monitor_task/...`。
- Rationale: 被监控主机初始化不能依赖面板登录态；同时公开接口范围必须压到安装流程，避免暴露完整管理能力。
- Alternatives considered:
  - 全部走 `/api` token：安全边界更一致，但客户端安装命令需要先配置 API token、时间戳和 IP 白名单，运维门槛高。

### 5. Analyze task state during daily report generation

- Decision: 第一版不新增 `monitorTaskAnalyseTask`。`scripts/report_analyser.py` 在生成单机报告时读取该主机启用的 monitor tasks，查询 ES 最近事件，按频率和状态判定结果，并回写 `last_status/last_msg/last_run_at/last_analyse_at`。
- Rationale: 日报是第一版的消费场景，把分析挂在日报生成里可以避免新增调度、锁和失败重试机制；管理页状态文案明确为“最近一次日报分析结果”。
- Alternatives considered:
  - 新增独立定时分析任务：页面状态更实时，但实现和运维复杂度更高，第一版收益有限。
  - 页面刷新时实时分析：操作体验更即时，但会让页面请求依赖 ES 查询和批量状态更新，响应时间不可控。

### 6. Isolate monitor task filebeat inputs from host collection inputs

- Decision: 任务日志采集使用独立配置目录和独立 input 文件，例如 `/etc/filebeat/jh-monitor-task-inputs.d/jh-monitor-task-<task_id>.yml`。安装脚本只确保 filebeat 主配置包含该目录的 include，不把任务 input 写入现有主机采集 input 文件，也不复用主机采集的 per-host 配置文件。
- Rationale: 脚本任务日志属于独立监控域，和主机系统状态、报告采集、备份日志采集的生命周期不同。独立目录能降低覆盖现有采集配置的风险，也便于卸载、排查和按任务幂等更新。
- Alternatives considered:
  - 写入现有 `/etc/filebeat/inputs.d/` 并按文件名区分：实现简单，但仍然和主机采集 input 混在一个目录，后续清理和排障容易误操作。
  - 追加到已有主机采集配置文件：文件数量少，但安装任务时最容易覆盖或破坏现有主机监控采集。

### 7. Keep report integration additive

- Decision: 单机报告文档新增 `monitor_task_tips` 和 `monitor_task_summary` 等结构化字段，同时把异常任务写入 `error_tips`，提醒任务写入橙色 `summary_tips`；总览报告复用现有 `is_abnormal/is_warning` 汇总逻辑。
- Rationale: 这样既能在单机报告展示任务明细，也能不大改总览聚合逻辑，让任务异常自然进入异常主机摘要。
- Alternatives considered:
  - 只追加纯文本 summary_tips：改动最小，但报告里缺少任务列表明细，不利于排查。
  - 重做总览任务专栏：展示更完整，但第一版会显著增加模板和数据结构改动。

## Risks / Trade-offs

- [公开注册接口被伪造调用] -> 注册接口必须校验 `host_id` 已存在、task_id 归属匹配，第一版可追加安装命令 token 字段并限制只更新当前任务定义和安装状态。
- [filebeat 版本差异导致 input 配置不兼容] -> 安装脚本先检测 filebeat 和任务日志专用配置目录；第一版使用当前项目已支持的 `type: log` JSON 配置，并在失败时回写 `install_status=failed`。
- [任务 input 配置影响主机采集] -> 任务日志 input 使用独立目录和独立文件，主配置只增加专用 include，安装和卸载任务不得编辑现有主机采集 input 文件。
- [日报生成时 ES 不可用] -> 单机报告记录任务分析失败提示，`monitor_task` 不覆盖已有成功分析结果或回写 `unknown` 并保存失败消息。
- [日任务执行时间波动导致误报] -> 表结构保留 `grace_seconds`，状态判定使用 `last_run_at + check_interval + grace_seconds`。
- [正常任务太多影响报告可读性] -> 单机报告展示任务明细，但只有异常和提醒进入 summary/error 摘要。

## Migration Plan

1. 新增 `monitor_task` 表定义和运行时 schema ensure，确保已有面板升级后自动具备字段。
2. 新增管理页入口和后端 API，先支持任务维护和安装命令复制。
3. 新增客户端安装脚本、标准日志命令和 public setup 接口，在测试主机上验证重复执行幂等。
4. 新增 ES index template/init 支持和最近事件查询服务。
5. 在日报分析阶段接入任务状态判定，先验证单机报告数据结构和 HTML 输出。
6. 更新报告模板展示监控任务明细，并确认总览异常/提醒汇总符合预期。
7. 回滚时可隐藏页面入口并停止下发安装命令；已创建的 `monitor_task` 表和 ES 事件索引可保留，不影响既有主机报告生成。

## Open Questions

- 安装命令是否第一版就加入一次性或长期 token，还是先只校验 `host_id + task_id` 归属。
- 管理页是否需要“立即分析一次”按钮；当前范围先不做，后续可基于同一分析服务补充。
- `jh-monitor-task-log` 是否需要支持 `--detail-json` 等扩展字段；第一版只要求 status/msg/run_at。
