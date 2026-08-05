## Context

`jh-monitor` 当前已有主机管理列表和主机详情弹窗，适合承载“主备管理”列表与多标签详情。江湖面板已有上下线脚本：`switch__generate_offline.sh` 和 `switch__generate_online.sh`，但这些脚本目前偏人工交互式流程，缺少可由云监控追踪的状态、日志和重试语义。

目标部署形态不是单中心云监控。两台主备面板部署在两个机房，每个机房各自部署一套云监控。任意一边云监控都需要看到两台机器各自的主备状态、自检状态、切换状态和日志。云监控不应主动跨机房 SSH，跨机房采集由面板插件完成。

## Goals / Non-Goals

**Goals:**

- 在云监控提供主备管理列表和组别详情，多标签展示主机列表、自检状态、切换状态、切换日志。
- 在江湖面板提供 `ha_manager` 插件，完成对端绑定、云监控配置、本地自检、本地切换和日志查看。
- 通过云监控保存期望状态，插件执行实际 offline/online 切换并上报实际状态。
- 每次切换在云监控 `/www/server/jh-monitor/logs/ha_switch/` 生成日志文件，SQLite 只保存状态索引和日志地址。
- 支持插件通过 SSH 采集对端状态和日志，并把“本机 + 对端”聚合上报到本机房云监控。
- 第一版支持手动切换、红色异常和橙色提醒、切换完成外部回调。

**Non-Goals:**

- 第一版不做自动故障切换。
- 第一版不使用 filebeat/ES 传输主备切换状态和日志。
- 云监控不直接 SSH 到跨机房对端机器。
- 第一版不重构现有主机报告、ES 报告流水线或通用脚本日志监控能力。

## Decisions

### 1. Use a dedicated HA module instead of extending host fields only

- Decision: 新增 HA pair/state/switch-run/callback 数据模型；现有 `host.is_master`、`backup_host_id` 等字段只作为兼容展示来源。
- Rationale: 主备管理需要区分配置关系、期望状态、实际状态、切换状态和日志地址，单个布尔字段无法表达切换中、失败、双主、双备、采集失败等状态。
- Alternatives considered: 直接复用 `host` 表字段。实现更快，但无法支持切换任务、日志追踪和双机房聚合上报。

### 2. Keep cloud monitor as control plane and plugin as execution plane

- Decision: 云监控只更新期望主机并创建切换任务；插件轮询期望状态，领取 offline/online 阶段并执行脚本流程。
- Rationale: 真正操作服务、MySQL、rsync、OpenResty 的能力在面板机器本地，插件执行更贴近权限和环境。
- Alternatives considered: 云监控直接 SSH 执行切换。会扩大云监控权限范围，也不适合双机房网络限制。

### 3. Let plugins aggregate peer state/logs over SSH

- Decision: 两台面板插件都能通过绑定的 SSH 通道读取对端 `state.json` 和日志增量，并把本机与对端数据统一上报到本机房云监控。
- Rationale: 双机房各自有云监控时，本机房云监控通常只能稳定访问本机房面板。插件之间已有绑定 SSH 关系，由插件做跨机房采集更自然。
- Alternatives considered: 两套云监控互相同步。会引入云监控间认证、冲突合并和网络开放问题，不适合作为第一版基础链路。

### 4. Store detailed switch logs as files

- Decision: 云监控每次切换在 `/www/server/jh-monitor/logs/ha_switch/YYYY-MM/<switch_run_id>.log` 保存完整日志，SQLite 只保存状态、步骤摘要、错误摘要和日志地址。
- Rationale: 切换日志可能较长，文件便于运维直接查看，也避免 SQLite 承载大量追加日志。
- Alternatives considered: 日志全量入 SQLite。查询简单，但持续追加和大日志存储不合适。

### 5. Identify log origin separately from reporter

- Decision: 日志事件携带 `origin_host_id`、`report_host_id`、`collect_method` 和 `seq`。云监控按 `origin_host_id` 展示两台机器各自日志。
- Rationale: 同一条对端日志可能由本机插件通过 SSH 采集后上报，必须区分“日志实际来自谁”和“是谁上报到当前云监控”。
- Alternatives considered: 只使用 `host_id`。字段含义容易混淆，无法准确处理双云监控和对端采集场景。

### 6. Keep switch options in the switch confirmation dialog

- Decision: 插件不保留独立“切换选项”页签。当前为备切换为主时，在确认弹窗中展示上线参数；当前为主切换为备时，弹窗展示下线流程摘要和接管确认。
- Rationale: 切换参数是单次操作上下文，长期暴露为独立配置页容易让用户误以为修改后会立即生效。
- Alternatives considered: 保留独立配置页。适合后续维护默认配置，但第一版手动切换中会增加理解成本。

## Risks / Trade-offs

- [SSH 采集失败被误判为主机离线] -> 区分 `collect_status` 和 `online_status`，采集失败先显示采集异常，不直接判定业务离线。
- [双云监控数据不一致] -> 两边云监控以各自机房插件上报为准，页面展示最近上报时间、上报主机和采集方式。
- [对端日志重复上传] -> 使用 `event_id` 或 `origin_host_id + seq` 做幂等。
- [脚本交互阻塞] -> 将 offline/online 流程封装为非交互执行器，所有 prompt 参数由 options 提供。
- [重复执行切换] -> 使用 `switch_run_id`、阶段状态和本地锁限制同机并发切换。
- [外部回调失败] -> 切换保持成功，回调状态单独标记失败/重试中，并写入本次切换日志。

## Migration Plan

1. 先上线 UI 和 OpenSpec 规格，确认列表、详情页、插件交互和字段模型。
2. 新增云监控 SQLite 表和管理 API，创建 HA pair/state/switch-run/callback 基础能力。
3. 新增 `ha_manager` 插件配置、绑定、自检、状态快照和本地日志落盘。
4. 接入 signed plugin APIs，先完成本机状态/日志上报。
5. 实现 SSH 采集对端状态和日志增量，并完成聚合上报和幂等处理。
6. 将 offline/online 脚本流程封装为非交互执行器，接入手动切换。
7. 接入外部回调、失败重试、页面重试和日志查看。
8. 回滚时隐藏页面入口并禁用插件轮询；已保存日志文件和 SQLite 状态可保留用于审计。

## Open Questions

- 插件与云监控 API 签名密钥由云监控下发，还是插件绑定时本地生成后登记到云监控。
- 对端 SSH 采集使用直接读取文件、执行插件命令，还是后续增加本地 Unix/HTTP 只读接口。
- 日志文件单文件大小上限和历史清理策略需要在实现前确定默认值。
