## Context

主备管理插件当前已经有完整的本地切换方法：`prepare_switch()` 执行预上线，`finalize_switch()` 执行旧主下线和新主正式上线，`local_switch()` 一次性串联完整切换。插件 UI 也已经是三步向导：选择主机、预备上线、正式上线。

云监控当前 `requestSwitchApi()` 创建的是单个 pending 任务，并立即把 `desired_master_host_id` 改成目标主机；插件 `poll_monitor()` 只保存云端下发的 run 信息，还没有根据云端任务自动执行 `prepare_switch()` 或 `finalize_switch()`。这会导致云端无法表达“预上线完成但未正式切换”的状态，也无法真正驱动插件执行云端创建的任务。

本变更让云端切换流程尽量与插件一致，并复用插件现有执行能力，不重新实现上下线脚本。

## Goals / Non-Goals

**Goals:**

- 云端提供和插件一致的两段式手动切换：预上线、正式上线。
- 插件定时任务通过 `poll_monitor()` 自动领取云端下发的阶段动作。
- 预上线不改变主备角色和回调状态，正式上线成功后再完成角色切换和外部回调。
- 支持失败重试、取消、日志追踪和重复执行保护。
- 保持旧的 `request_switch` 尽量兼容，降低已有入口断裂风险。

**Non-Goals:**

- 不做自动故障切换。
- 不替换插件的 SSH 编排方式。
- 不在云监控侧直接 SSH 到面板机器执行脚本。
- 不重做展示层真实数据渲染；该能力由 `improve-ha-cloud-display` 处理。

## Decisions

### 1. 以云端任务状态机表达两段式流程

`ha_switch_run.status` 扩展为以下状态：

| 状态 | 含义 |
|---|---|
| `pending_prepare` | 已创建预上线任务，等待插件领取 |
| `preparing` | 插件正在执行预上线 |
| `prepared` | 预上线完成，等待人工确认正式上线 |
| `pending_finalize` | 已确认正式上线，等待插件领取 |
| `finalizing` | 插件正在执行下线和正式上线 |
| `success` | 正式切换完成 |
| `waiting_retry` | 阶段失败，等待重试 |
| `cancelled` | 操作员取消 |

选择显式状态而不是继续复用 `pending/running`，是因为云端需要稳定区分“预上线完成待确认”和“正式上线执行中”。旧状态可以在兼容逻辑中映射。

### 2. 预上线阶段不修改 `desired_master_host_id`

创建预上线任务时写入 `new_master_host_id` 或 `target_host_id`，但不改变 `ha_pair.desired_master_host_id`。只有操作员确认正式上线后，云端才将 `desired_master_host_id` 更新为目标主机。

这样能避免预上线期间云端把“期望和实际不一致”误判成异常。预上线是准备动作，不代表业务主机已经改变。

### 3. 云端下发明确的动作给插件

`/pub/ha_pull_desired_state` 返回的 `switch_run` 增加动作语义：

```json
{
  "switch_run_id": "HSR_xxx",
  "action": "prepare_switch",
  "target_host_id": "H_PANEL_xxx",
  "target_role": "master",
  "status": "pending_prepare",
  "current_phase": "prepare_online",
  "options": {}
}
```

正式上线时返回：

```json
{
  "switch_run_id": "HSR_xxx",
  "action": "finalize_switch",
  "target_host_id": "H_PANEL_xxx",
  "target_role": "master",
  "status": "pending_finalize",
  "current_phase": "offline",
  "options": {}
}
```

插件 `poll_monitor()` 根据 action 调用本地 `prepare_switch()` 或 `finalize_switch()`。当目标主机是对端时，仍由当前插件调用现有方法，让插件内部通过 SSH 编排对端阶段。

### 4. 插件侧做重复执行保护

插件保存最近领取的 `switch_run_id + action` 执行状态。只有云端状态是待领取状态，且本地没有相同 action 正在执行或已成功执行时，才启动执行。

保护层级：

1. 插件现有 `switch.lock` 防止并发脚本。
2. 本地状态文件记录 claimed/running/done 的 action。
3. 云端事件上报和 ack 接口幂等处理重复事件。

### 5. 回调只在正式上线成功且实际状态确认后触发

预上线成功只把 run 置为 `prepared`。正式上线成功后，云端等待插件状态上报确认目标主机成为 master，再执行回调。如果状态上报短时间内未到达，可先标记 `success_pending_report` 或保持 `finalizing`，避免提前回调外部系统。

## Risks / Trade-offs

- [Risk] 插件定时任务可能在两台机器同时领取同一动作。→ Mitigation: 云端按 `report_host_id/host_id` 和任务状态做领取约束，插件本地锁和 action 记录再兜底。
- [Risk] 预上线成功后操作员长时间不正式上线。→ Mitigation: 云端显示 `prepared` 和预上线完成时间，允许取消或重新预上线。
- [Risk] 正式上线过程中旧主下线成功、新主上线失败，进入中间故障态。→ Mitigation: 保留 `waiting_retry`，日志展示失败阶段，重试只重试失败或正式上线阶段，不自动回滚。
- [Risk] 旧版插件不识别 `action` 字段。→ Mitigation: 云端下发前可根据插件上报版本判断；未知版本只展示待执行，不自动领取。
- [Risk] 提前更新 `desired_master_host_id` 会造成误报。→ Mitigation: 设计规定预上线不更新该字段，正式上线确认时才更新。

## Migration Plan

1. 扩展 `ha_switch_run` 表字段，兼容已有 `pending/running/success/waiting_retry` 数据。
2. 新增云端预上线创建和正式上线确认 API，保留旧 `request_switch` 入口兼容。
3. 更新 `/pub/ha_pull_desired_state` 返回 action、目标主机、目标角色和选项。
4. 更新插件 `poll_monitor()` 自动执行 action，并写入本地领取状态。
5. 更新云端 UI 为三步向导，接入预上线和正式上线 API。
6. 验证云端创建预上线、插件执行、云端显示 prepared、人工确认正式上线、插件执行 finalize、状态上报和回调完整链路。

## Open Questions

- 云端是否需要显式“重新预上线”按钮，还是通过失败重试和取消后重建覆盖。
- 正式上线成功后等待实际状态确认的超时时间应配置为多少，建议先使用 60 秒并允许后续调整。
