## Context

当前云监控 HA 后端已经具备 `ha_pair`、`ha_host_state`、`ha_switch_run`、`ha_switch_event` 等 SQLite 表，也有插件公开上报接口。主备插件侧已经能上报本机和通过 SSH 采集到的对端状态，`health_detail` 中包含真实健康摘要和脚本检查结果。

主要问题在展示层：`route/static/app/ha_management.js` 仍通过 `haCheckTemplate` 和 `haBuildHostChecks()` 构造模拟检查项，例如固定的 MySQL 延迟和 lsyncd warning。这样会让云监控页面看起来有状态，但不能作为运维判断依据。

本变更只处理云端展示真实数据，不改变主备切换执行模型。切换执行与两段式流程由 `complete-ha-cloud-switch-flow` 处理。

## Goals / Non-Goals

**Goals:**

- 后端返回稳定、前端易消费的 HA 展示数据结构。
- 自检状态、切换状态、日志展示都以插件上报和云端落库数据为准。
- 缺少真实数据时明确显示未知、未上报或暂无日志，不生成模拟成功/异常。
- 保持现有云监控主备管理页面的信息架构、弹框结构和基础视觉样式，只替换真实数据渲染和必要的空状态/字段展示。
- 保持当前 SQLite 和文件日志存储方式。
- 为后续两段式切换流程预留展示字段，但不在本变更中驱动执行。

**Non-Goals:**

- 不实现 `poll_monitor()` 自动执行云端切换任务。
- 不新增自动故障切换。
- 不改造插件的自检采集脚本，只消费其现有上报结构。
- 不引入 ES、filebeat 或新的日志系统。

## Decisions

### 1. 后端统一规范化展示 payload

后端在 `_normalizePair()` 和 `_normalizeHost()` 中输出前端所需字段，避免前端解析数据库原始字段和 JSON 字符串。

建议主机结构包含：

```json
{
  "host_id": "H_PANEL_xxx",
  "name": "江湖平台@Mega",
  "ip": "1.2.3.4",
  "role": "master",
  "online": "online",
  "health_status": "normal",
  "collect_status": "success",
  "collect_method": "local",
  "report_host_id": "H_PANEL_xxx",
  "health_detail": {},
  "script_checks": [],
  "switch_run_id": "HSR_xxx",
  "switch_phase": "prepare_online",
  "switch_status": "running",
  "current_step": "同步文件 /www/wwwroot",
  "next_step": "checksum 检查",
  "last_error": "",
  "log_path": "...",
  "last_report_at": "2026-08-12 10:00:00"
}
```

选择后端规范化而不是前端直接猜结构，是因为插件上报可能存在版本差异，后端更适合做兼容和默认值处理。

### 2. 自检展示以 `script_checks` 为主，摘要字段为辅

前端渲染优先级：

1. `host.script_checks`。
2. `host.health_detail.script_checks`。
3. `host.health_detail.checks`。
4. 只有摘要时展示一行摘要。
5. 完全缺失时展示“暂无自检明细”。

旧的 `haCheckTemplate` 可作为字段兼容参考，但不得用于生成模拟实际状态。

### 3. 切换状态从 run 与 event 推导

详情页切换状态优先展示当前 `ha_switch_run` 的 `status/current_phase/current_step/next_step/last_error`。主机行再叠加 `ha_host_state` 中的 `switch_phase/switch_status/current_step`。

日志分组优先使用 `ha_switch_event.origin_host_id`；如果没有事件行，则从完整日志中按 `[host_id]` 或来源文本做尽力分组，无法分组时只展示完整日志。

### 4. 状态等级只由真实数据推导

`normal/warning/danger/switching/unknown` 由后端基于实际主机角色、期望主机、上报时间、采集状态、健康状态和运行中切换任务推导。前端只负责样式映射，不重新发明状态规则。

## Risks / Trade-offs

- [Risk] 老版本插件未上报 `script_checks`，页面信息会少于当前模拟版。→ Mitigation: 显示摘要和“暂无自检明细”，不伪造数据。
- [Risk] 同一主机可能被本机和对端重复上报。→ Mitigation: 后端按 `pair_id + host_id` 覆盖最新状态，并保留 `collect_method/report_host_id` 说明来源。
- [Risk] 日志文件很大导致详情接口变慢。→ Mitigation: 列表不返回完整日志，详情或日志接口按需读取并限制大小。
- [Risk] 前端字段兼容处理过多。→ Mitigation: 主要兼容逻辑放后端，前端只处理数组为空和文本为空。

## Migration Plan

1. 保持现有表结构可用，必要时通过 `ensureHaSchema()` 增加兼容字段。
2. 先改后端规范化输出，保证旧前端仍能读取基本字段。
3. 再改前端移除模拟自检构造，渲染真实 `script_checks` 和 run/event 数据。
4. 使用现有测试数据和插件真实上报数据验证列表、详情、自检、日志。
5. 如出现老数据展示异常，可回退前端文件；后端新增字段保持向后兼容。

## Open Questions

- 插件 `health_detail.script_checks` 的最终字段名是否固定为 `group/name/expected/actual/status/message`，还是需要兼容现有多种形态。
- 是否需要在列表页展示每台主机最近上报时间，还是只在详情页展示。
