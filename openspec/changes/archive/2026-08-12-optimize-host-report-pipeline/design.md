## Context

`jh-monitor` 目前已经具备主机监控任务、邮件通知能力，以及客户端安装脚本和 filebeat 安装资源，但每日报告仍以“发送时实时取数 + 当场分析 + 逐台发送”为主。现状带来的问题包括：

- 报告链路耦合在 SSH 连通、远端主机即时状态和发送操作上，失败点多且难以重试。
- 原始数据与最终报告没有统一集中存储，难以按日期追溯、补算和复盘。
- 客户端侧已有 `scripts/client/install.sh`、`scripts/client/install/debian.sh`、filebeat 安装资源和报告脚本雏形，但缺少围绕日报场景的标准化路径、定时、幂等更新和 ES 数据模型。
- 发送侧已经存在 `task.py` 中的定时任务和邮件通知基础能力，适合扩展为独立的“分析任务 + 发送任务”。

该变更会跨越面板配置、客户端安装、数据采集、ES 存储、日报分析和邮件发送，属于典型的跨模块架构调整。

## Goals / Non-Goals

**Goals:**
- 将日报流程拆分为采集、分析、发送三个独立阶段，降低单点故障影响。
- 统一 ES 原始索引和报告索引结构，让原始数据、报告结果和发送状态都可追溯。
- 在面板中统一维护 ES 参数和报告阈值配置，并通过后端做默认初始化、原子写入和校验。
- 复用 `/www/server/jh-panel/scripts/report.py` 的日报判断口径，保证新旧日报结论一致。
- 让客户端安装/更新流程能够稳定部署采集脚本、cron 和 filebeat 配置，且重复执行不产生重复任务。

**Non-Goals:**
- 本次不重做现有邮件通知渠道，只复用已有邮件发送能力。
- 本次不把日报采集重新降权回 `ansible_user` 执行；第一版默认由 `root` cron 执行。
- 本次不扩展新的异常口径（如站点停机、JianghuJS 停机、Docker 停机）作为上线前置条件，仍以 `report.py` 现有口径为准。
- 本次不实现周报和趋势图，仅在数据模型和任务拆分上为后续扩展预留空间。

## Decisions

### 1. Use ES-backed stage boundaries instead of live fetch during send

- Decision: 将 ES 作为三段流水线的唯一交接面。采集阶段只负责写原始事实数据，分析阶段只负责读取原始索引并生成报告，发送阶段只负责读取报告索引并投递邮件。
- Rationale: 这样可以把发送从“依赖主机在线和 SSH 连通”切换为“依赖报告是否已经生成”，最适合支持补算、重发和追溯。
- Alternatives considered:
  - 继续在发送阶段实时 SSH 取数：实现改动小，但不稳定性和不可追溯问题依旧存在。
  - 采集后直接写本地 sqlite：虽然接入成本低，但不适合跨主机集中汇总、按日期重算和统一检索。

### 2. Split configuration into dedicated JSON files and backend-owned validation

- Decision: 报告阈值保存到 `data/report_config.json`，ES 参数保存到 `data/es.json`，文件缺失时自动初始化为 `{}`，写入时使用临时文件替换正式文件；前端只负责展示与录入，后端统一负责读取、保存、范围校验和连接校验。
- Rationale: 该方案与仓库中已有 `data/notify.json` 的管理方式一致，落地成本低，也能避免前端自行拼接配置逻辑导致的数据损坏。
- Alternatives considered:
  - 把全部配置并入现有 `notify.json`：耦合过高，后续 ES 参数轮换与阈值管理不够清晰。
  - 直接落数据库：需要额外建表和迁移逻辑，当前项目已有 JSON 配置惯例，没有必要优先引入。

### 3. Install a local collector under the ansible user directory but execute it via root cron

- Decision: 客户端采集脚本统一部署到 `/home/${USERNAME}/jh-monitor-scripts/report_collector.py`，输出目录固定为 `/home/${USERNAME}/jh-monitor-scripts/data/`，日志固定为 `/home/${USERNAME}/jh-monitor-logs/report-collector.log`，cron 文件固定为 `/etc/cron.d/jh-monitor-report-collector`，由 `root` 每 5 分钟执行一次，并在安装/更新后立即执行一次。
- Rationale: 采集逻辑需要读取多个系统目录和备份目录。由 `root` 运行可以显著减少 ACL、sudo 白名单和权限排查复杂度，同时继续复用现有安装脚本中围绕 `ansible_user` 目录的约定。
- Alternatives considered:
  - 由 `ansible_user` 周期执行：权限最小化更理想，但第一版需要维护大量 ACL/sudo 细节，实施风险更高。
  - 通过 ansible 定时远程执行并直接写 ES：中心控制更强，但会重新把链路稳定性绑定到 SSH 与控制端调度能力上。

### 4. Reuse report.py rule semantics but move aggregation to jh-monitor tasks

- Decision: 在 `task.py` 中新增独立的分析任务，按“报告日期”读取 `host-system-status`、`host-xtrabackup`、`host-xtrabackup-inc`、`host-backup` 四类原始索引，并按 `/www/server/jh-panel/scripts/report.py` 的口径生成 `summary_tips`、`error_tips`、系统/备份/业务明细以及 HTML 内容。
- Rationale: 现有 `report.py` 已经沉淀了告警阈值、异常判断和展示逻辑，复用其口径比重新定义日报规则更安全，也能减少新旧日报结果偏差。
- Alternatives considered:
  - 在 ES 中直接通过查询脚本完成全部统计：检索方便，但复杂业务规则、HTML 组装和兼容现有口径会变得难以维护。
  - 直接调用远端 `report.py` 生成 HTML：仍然依赖远端现场数据，无法达成“集中分析”的目标。

### 5. Persist delivery audit on report documents rather than fetching live state again

- Decision: 发送任务只读取 `host-report-single` 与 `host-report-overview` 中已经生成且通过校验的报告，成功/失败结果、时间、失败原因和重试次数回写到对应报告文档的发送状态字段中。
- Rationale: 报告文档本身就是发送唯一数据源，把发送审计与报告结果存放在一起，最方便按日期、主机和发送状态检索与补发。
- Alternatives considered:
  - 单独增加发送日志索引：可读性更高，但会增加索引数量与双写复杂度，第一版收益有限。
  - 继续用本地日志记录发送结果：难以集中检索，也不利于按报告维度做补发。

## Risks / Trade-offs

- [ES unavailable during collection or analysis] -> 采集阶段保留本地 JSON 输出，分析/发送阶段在任务日志中明确记录失败原因，并允许按日期重跑。
- [Collector schema drifts from analyzer expectations] -> 为四类原始索引定义固定字段集合与统一命名，分析前增加字段完整性校验。
- [Cron or installer leaves duplicate jobs after upgrade] -> 安装/更新强制执行“清理旧 cron -> 覆盖脚本 -> 重写 cron -> 立即执行 -> 校验输出”的顺序，并把 cron 文件固定到单一路径。
- [New pipeline and legacy send logic produce inconsistent conclusions] -> 分析规则显式对齐 `/www/server/jh-panel/scripts/report.py`，并在上线初期对同一天数据做结果比对。
- [HTML content becomes stale after recompute] -> 以“报告日期 + 主机”作为幂等键，重算时覆盖同一天的报告正文和发送状态，由补发任务负责重新发送。

## Migration Plan

1. 增加配置读写接口和面板配置区，先让 ES 参数与阈值配置可管理。
2. 在客户端安装/更新流程中加入采集脚本、cron 和 filebeat 路径约定，完成原始数据稳定入库。
3. 创建并验证四个原始索引和两个报告索引的 mapping/命名约定。
4. 上线 `task.py` 中的分析任务，先生成报告但不切换正式发送，确认与旧日报口径一致。
5. 切换发送任务到“只读报告索引”的模式，并保留旧链路作为短期回退手段。
6. 若新链路异常，可暂停分析/发送任务并回退到旧日报发送方式；已采集的原始数据可用于后续补算，不需要回滚客户端采集部署。

## Open Questions

- ES 配置保存时的“测试连接”是否作为强制门槛，还是仅提供手动检测按钮。
- 报告发送状态字段是嵌入原报告文档，还是额外保留 attempt history 数组；实现时需要明确字段上限与清理策略。
- 周报与趋势图后续是否继续复用相同的报告索引，还是新增周报专用索引。
