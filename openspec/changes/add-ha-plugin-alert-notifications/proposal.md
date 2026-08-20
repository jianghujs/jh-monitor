## Why

当前主备异常主要在云监控页面展示，缺少由主备管理插件主动发送的异常通知和恢复通知。两套云监控同时存在时，如果由云监控发送通知，会出现谁负责发送、如何避免重复发送的问题；更合适的边界是由主备管理插件基于本机和对端实时状态判断异常并发送通知，云监控只保存、展示并在日报中汇总通知事件。

## What Changes

- 主备管理插件新增异常通知检测任务，周期检查本机状态、对端可达性、主备角色、降级运行、恢复保护和切换卡住等异常。
- 主备关联后支持配置一个 `primary_notifier_host_id` 作为主通知方，正常情况下只由主通知方插件发送主备异常通知。
- 备用通知方在主通知方连续不可达时进入接管模式，并发送主通知方不可达/通知接管类异常。
- 通知状态参考江湖面板 `systemTask` 机制但按主备关系整体异常态合并：从无异常变为有异常时发送一次异常通知，异常期间新增其他异常不再发送，全部异常恢复后发送一次恢复通知。
- 每个异常周期首次通知时确定唯一 `notification_owner_host_id`，该周期内异常通知、异常明细更新和最终恢复通知都由同一个通知方负责，不因主通知方恢复或备用方接管状态变化而更换通知方。
- 插件使用本地 `alert_state.json` 保存主备关系整体异常态、当前活跃异常明细和恢复文案，使用通知接管状态文件记录主通知方可达性和接管状态。
- 插件复用江湖面板现有 `mw.notifyMessage` 通知渠道，不新增独立 SMTP 配置。
- 插件将通知发送、恢复、失败和跳过等事件上报云监控，用于主备管理页面展示和日报汇总。
- 云监控不直接发送主备异常邮件，只展示插件上报的异常通知记录和日报汇总。

## Capabilities

### New Capabilities

- `ha-plugin-alert-notifications`: 定义主备管理插件异常检测、主通知方/备用接管、异常通知与恢复通知、通知事件上报云监控的行为。

### Modified Capabilities

无。

## Impact

- Affected panel plugin: `/www/server/jh-panel/plugins/ha_manager/index.py` 的插件配置、定时任务、状态采集、异常判断、通知发送、通知状态持久化和云监控事件上报。
- Affected panel plugin metadata: `/www/server/jh-panel/plugins/ha_manager/info.json` 新增或调整插件定时任务配置。
- Affected panel plugin UI: `/www/server/jh-panel/plugins/ha_manager/index.html` 或相关前端脚本增加通知主方配置、通知开关、接管状态和最近通知记录展示。
- Affected cloud monitor backend: `/www/server/jh-monitor/class/core/ha_api.py` 接收并保存插件上报的主备异常通知事件。
- Affected cloud monitor frontend/reporting: 主备管理页面展示通知记录，日报中汇总主备异常通知和恢复通知。
- Affected logs/data: `/www/server/ha_manager/data/alert_state.json`、通知接管状态文件、`/www/server/logs` 下主备管理插件交互日志。
