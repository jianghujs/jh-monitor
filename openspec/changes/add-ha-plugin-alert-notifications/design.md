## Context

主备管理插件已经承担主备切换、对端 SSH 检查、降级运行和故障恢复补全的核心职责。异常通知如果放到两个云监控实例中处理，会遇到同一主备关系由哪个云监控发送通知的问题；如果引入 NAS 或中心库只为通知去重，复杂度又超过当前需求。

本设计将主备异常通知放在 `ha_manager` 插件侧。插件通过定时任务读取本机与对端实时状态，按主通知方/备用接管规则决定是否发送通知，并参考江湖面板 `systemTask` 的 active state 思路实现“主备关系从正常进入异常时发送一次，异常期间新增其他异常不重复发送，全部异常恢复时发送一次”。云监控只接收通知事件，用于页面展示和日报汇总。

## Goals / Non-Goals

**Goals:**

- 主备关联后支持指定一个 `primary_notifier_host_id` 作为主通知方。
- 主通知方在线时，只有主通知方插件发送主备异常通知。
- 主通知方连续不可达时，备用通知方进入接管模式并发送通知。
- 异常通知按主备关系整体异常态去重：从无异常变为有异常时发送一次，异常期间新增其他异常不重复发送，全部异常恢复时发送一次恢复通知。
- 插件复用江湖面板已有通知渠道 `mw.notifyMessage`，不新增独立邮件配置。
- 插件将通知事件上报云监控，云监控只展示、归档和日报汇总。

**Non-Goals:**

- 不让云监控直接发送主备异常邮件。
- 不引入 NAS、共享数据库或中心通知服务做强一致去重。
- 不保证网络分区等极端场景下绝对只发送一封通知。
- 不默认把所有自检 warning 都发邮件；第一版聚焦高价值主备异常。
- 不改变主备切换、故障升主和恢复为备机的执行职责。

## Decisions

### 1. 通知由插件发送，云监控只展示

主备异常判断需要本机角色、对端 SSH、对端插件、切换锁、降级状态和恢复保护等上下文，这些上下文在插件侧最准确。云监控只保存上报结果，存在延迟和双实例归属问题。

因此插件负责：检测异常、判断通知负责人、发送异常/恢复通知、保存通知状态、上报通知事件。云监控负责：展示最近通知记录、在日报中汇总通知事件、不直接发邮件。

### 2. 使用固定主通知方和备用接管

主备关系保存单一字段 `primary_notifier_host_id`，其值等于某台插件主机的 `host_id`。插件判断：

| 条件 | 通知行为 |
|---|---|
| 本机 `host_id == primary_notifier_host_id` | 本机是主通知方，负责处理通知状态机 |
| 本机不是主通知方且主通知方可达 | 本机不发送主备异常通知 |
| 本机不是主通知方且主通知方连续不可达达到阈值 | 本机进入备用接管模式，负责处理通知状态机 |

备用接管避免主通知方停机时漏发；固定主通知方避免正常情况下两台插件重复发送。

第一版建议阈值：`alert_check` 每 30 秒执行一次，主通知方连续 3 次不可达后接管，连续 2 次可达后退出接管。

### 3. 参考 systemTask 的整体异常态状态机

插件维护本地通知状态文件，例如 `/www/server/ha_manager/data/alert_state.json`：

```json
{
  "status": "abnormal",
  "first_seen_at": "2026-08-20 10:00:00",
  "last_seen_at": "2026-08-20 10:05:00",
  "last_notify_at": "2026-08-20 10:00:00",
  "active_keys": ["HA_xxx:host_unreachable:H_PANEL_A"],
  "alerts": {
    "HA_xxx:host_unreachable:H_PANEL_A": {
      "message": "主机 BK100-33 不可达",
      "recovery_message": "主机 BK100-33 已恢复可达",
      "level": "danger",
      "alert_type": "host_unreachable",
      "first_seen_at": "2026-08-20 10:00:00",
      "last_seen_at": "2026-08-20 10:00:00"
    }
  }
}
```

每轮 `alert_check` 生成 `current_alerts` 后先判断主备关系整体状态：

```text
previous_abnormal = previous_active_keys 非空
current_abnormal = current_active_keys 非空
```

- `previous_abnormal=false` 且 `current_abnormal=true` 时，合并当前全部异常发送一封异常通知。
- `previous_abnormal=true` 且 `current_abnormal=true` 时，只更新 active alert 明细，不发送通知；即使新增了其他异常也不重复发送。
- `previous_abnormal=true` 且 `current_abnormal=false` 时，合并上一轮活跃异常的恢复文案发送一封恢复通知。
- `previous_abnormal=false` 且 `current_abnormal=false` 时，不发送通知。
- 通知发送后保存当前整体异常态和 active alert 明细；异常通知发送失败时保留上一轮正常态，避免发送失败后误认为已经通知。

### 4. 异常 key 必须稳定且标准化

虽然邮件通知按主备关系整体异常态合并，但插件仍需生成稳定的 `alert_key`，用于记录当前异常明细、构造首次异常通知内容、构造恢复通知内容、上报云监控和页面展示。

建议第一版 key：

| 异常 | key |
|---|---|
| 主机不可达 | `<pair_id>:host_unreachable:<host_id>` |
| 双主异常 | `<pair_id>:double_master` |
| 双备或无主 | `<pair_id>:no_master` |
| 降级运行 | `<pair_id>:degraded_master:<host_id>` |
| 恢复保护 | `<pair_id>:recovery_guard:<host_id>` |
| 切换卡住 | `<pair_id>:switch_stuck:<switch_run_id>` |
| 关键自检失败 | `<pair_id>:health_failed:<host_id>:<check_key>` |

第一版默认通知：主机不可达、双主、双备或无主、降级运行、恢复保护、切换卡住。关键自检失败可配置开启。

### 5. 通知接管状态独立于异常状态

备用方需要记录主通知方可达性和接管状态，例如 `/www/server/ha_manager/data/alert_notifier_state.json`：

```json
{
  "takeover_active": false,
  "primary_unreachable_count": 0,
  "primary_reachable_count": 0,
  "takeover_started_at": "",
  "takeover_recovered_at": ""
}
```

主通知方恢复后，备用方退出接管。是否发送“通知职责切回主通知方”的恢复通知可作为配置项，第一版可以随主通知方不可达 alert 的恢复通知一起表达。

### 6. 配置同步和 UI

为了避免两台插件配置不一致，`primary_notifier_host_id` 应作为主备绑定配置的一部分保存，并在保存绑定或通知设置时通过 SSH 同步到对端插件。UI 只展示一个“主通知方：本机/对端”的选择，而不是两边分别配置布尔值。

插件总览页展示：

- 异常通知开启/关闭。
- 主通知方是本机还是对端。
- 当前是否处于备用接管。
- 最近通知记录和最近恢复记录。

### 7. 云监控通知事件

插件发送通知、恢复通知、发送失败、备用接管等事件应上报云监控。事件字段建议：

```json
{
  "pair_id": "HA_xxx",
  "host_id": "H_PANEL_A",
  "event_type": "ha_alert_notify",
  "alert_key": "HA_xxx:host_unreachable:H_PANEL_B",
  "alert_type": "host_unreachable",
  "alert_level": "danger",
  "status": "sent",
  "title": "主备异常通知：BK100",
  "message": "...",
  "sent_by_host_id": "H_PANEL_A",
  "addtime": "2026-08-20 10:00:00"
}
```

云监控可将这些事件展示在主备详情和日报中，但不根据事件再次发送邮件。

## Risks / Trade-offs

- [Risk] 主通知方异常后，备用方接管时不知道主通知方是否已经发送过当前异常，可能在接管瞬间发送一封重复或接管类通知。→ Mitigation: 备用接管通知内容明确说明“主通知方不可达，备用方接管”；接管后仍按主备关系整体异常态只发送一次。
- [Risk] 网络分区时两边都可能认为对方不可达。→ Mitigation: 允许严重网络分区场景下两边各发风险通知；通知文案明确存在双主/网络分区风险，且本地整体异常态状态机防止持续刷屏。
- [Risk] 两台插件的 `primary_notifier_host_id` 不一致。→ Mitigation: 保存配置时同步对端；自检中增加通知主方配置一致性检查；不一致时展示 warning 并记录日志。
- [Risk] 面板通知配置未开启导致邮件未发送。→ Mitigation: 使用 `mw.notifyMessage` 返回值记录发送失败，上报云监控，UI 展示通知配置异常或发送失败。
- [Risk] 自检 warning 过多导致通知噪音。→ Mitigation: 第一版默认只通知主备高价值异常，关键自检通知使用配置开关。

## Migration Plan

1. 插件默认启用异常通知，默认主通知方为当前 `master`，如果无明确 master 则默认本机或注册时指定主机。
2. 已有关联保存时补齐 `primary_notifier_host_id`，不改变已有主备角色。
3. 新增插件定时任务 `alert_check`，先以观察/记录为主，确认行为后启用通知发送。
4. 云监控后端先兼容通知事件上报，前端和日报逐步展示。
5. 如通知误报或重复，可通过插件配置关闭异常通知或关闭关键自检通知。

## Open Questions

- 默认主通知方是否固定为当前业务主机，还是在绑定页面让用户必须显式选择。
- 关键自检失败是否第一版就允许开启通知，还是只做页面展示。
- 主通知方恢复后是否需要单独发送“通知职责已切回”的通知，还是由主通知方不可达恢复通知覆盖。
