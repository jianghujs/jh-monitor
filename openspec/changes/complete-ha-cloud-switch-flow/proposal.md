## Why

主备管理插件已经支持“预上线”和“正式上线”两个明确动作，但云监控当前只创建一个一键切换任务，无法表达“预上线已完成、等待人工确认正式上线”的关键中间态。为了让云监控成为可靠的主备切换入口，需要让云端切换流程尽量与插件保持一致，并通过插件定时任务自动领取执行。

## What Changes

- 云监控手动切换从一键创建完整切换任务升级为两段式流程：选择目标主机、执行预上线、确认正式上线。
- 预上线阶段只在切换后的目标主机执行准备动作，不改变实际主备角色，不触发外部回调。
- 正式上线阶段在人工确认后执行旧主下线和新主正式上线，完成后再更新期望主机、实际主机状态并触发回调。
- 云端任务状态增加 `pending_prepare`、`preparing`、`prepared`、`pending_finalize`、`finalizing` 等阶段语义。
- 插件 `poll_monitor()` 根据云端下发的动作自动调用现有 `prepare_switch()` 或 `finalize_switch()`，并避免重复执行同一个切换任务。
- 云端切换向导尽量复用插件相同的选项和文案，包括同步文件、checksum、允许忽略 checksum 差异、恢复网站配置、面板插件配置、执行增量恢复。
- 云端继续支持失败重试、取消、日志追踪和完成回调，但回调只在正式上线成功并确认实际状态后触发。
- 不在本变更中重做云端真实展示的基础能力；该部分由 `improve-ha-cloud-display` 承担。

## Capabilities

### New Capabilities

- `ha-cloud-two-stage-switch`: 云监控 SHALL 支持与主备管理插件一致的预上线和正式上线两段式主备切换流程。

### Modified Capabilities

- None.

## Impact

- Affected cloud monitor backend: `/www/server/jh-monitor/class/core/ha_api.py` 中切换任务创建、确认正式上线、轮询期望状态、事件确认、重试、取消、回调触发逻辑。
- Affected cloud monitor frontend: `/www/server/jh-monitor/route/static/app/ha_management.js` 中手动切换弹框改为三步向导，并展示预上线结果和正式上线入口。
- Affected panel plugin: `/www/server/jh-panel/plugins/ha_manager/index.py` 中 `poll_monitor()` 自动执行云端下发的 `prepare_switch` / `finalize_switch` 动作，并复用现有锁和日志上报。
- Affected scheduled task runtime: 江湖面板插件定时任务机制负责周期调用 `poll_monitor`，不新增插件常驻进程。
- Data: 可能需要为 `ha_switch_run` 增加动作、目标主机、预上线完成时间、正式上线确认时间等字段，保持旧数据兼容。
- Tests: 需要覆盖云端两段任务状态机、插件领取执行去重、预上线不改角色、正式上线后回调等核心流程。
