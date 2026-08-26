# ha-cloud-two-stage-switch Specification

## Purpose
TBD - created by archiving change complete-ha-cloud-switch-flow. Update Purpose after archive.
## Requirements
### Requirement: 云端创建预上线任务
云监控 SHALL 支持为插件注册的主备关系创建预上线任务，任务 SHALL 记录目标主机、旧主机、切换选项、日志路径和当前阶段。

#### Scenario: 操作员发起预上线
- **WHEN** 操作员在云监控选择目标主机并提交预上线选项
- **THEN** 系统 SHALL 创建状态为 `pending_prepare` 的切换任务
- **AND** 系统 SHALL 将 `current_phase` 设置为 `prepare_online`
- **AND** 系统 MUST NOT 在此时修改主备关系的 `desired_master_host_id`

#### Scenario: 目标主机无效
- **WHEN** 操作员提交不存在或不属于该主备关系的目标主机
- **THEN** 系统 SHALL 拒绝创建任务并返回明确错误

### Requirement: 插件领取并执行预上线
江湖面板插件 SHALL 通过定时任务轮询云监控，并在发现待预上线动作时自动调用现有 `prepare_switch()` 执行预上线。

#### Scenario: 轮询到待预上线任务
- **WHEN** 插件 `poll_monitor()` 获取到 `action=prepare_switch` 且任务状态为 `pending_prepare`
- **THEN** 插件 SHALL 使用云端下发的 `switch_run_id`、目标角色和选项调用 `prepare_switch()`
- **AND** 插件 SHALL 通过切换事件接口上报预上线日志和结果

#### Scenario: 重复轮询同一预上线动作
- **WHEN** 插件再次轮询到已在本机执行中或已成功执行的同一 `switch_run_id + action`
- **THEN** 插件 MUST NOT 重复启动预上线脚本

### Requirement: 预上线完成后等待人工确认
云监控 SHALL 在预上线成功后将任务置为 `prepared`，并等待操作员人工确认正式上线。

#### Scenario: 预上线成功
- **WHEN** 插件上报 `prepare_online` 成功
- **THEN** 云监控 SHALL 将任务状态更新为 `prepared`
- **AND** 云监控 SHALL 展示预上线完成时间、日志和正式上线入口
- **AND** 云监控 MUST NOT 触发外部回调

#### Scenario: 预上线失败
- **WHEN** 插件上报 `prepare_online` 失败
- **THEN** 云监控 SHALL 将任务状态更新为 `waiting_retry`
- **AND** 云监控 SHALL 保留失败阶段、错误信息和日志

### Requirement: 云端确认正式上线
云监控 SHALL 支持在预上线成功后由操作员确认正式上线，并将任务推进到正式上线待领取状态。

#### Scenario: 操作员确认正式上线
- **WHEN** 操作员对 `prepared` 任务点击正式上线
- **THEN** 系统 SHALL 将任务状态更新为 `pending_finalize`
- **AND** 系统 SHALL 将 `current_phase` 设置为 `offline`
- **AND** 系统 SHALL 将主备关系的 `desired_master_host_id` 更新为目标主机

#### Scenario: 未预上线成功就确认正式上线
- **WHEN** 操作员对非 `prepared` 任务确认正式上线
- **THEN** 系统 SHALL 拒绝操作并返回当前任务状态不允许正式上线

### Requirement: 插件领取并执行正式上线
江湖面板插件 SHALL 在轮询到正式上线动作时自动调用现有 `finalize_switch()`，由插件执行旧主下线和新主正式上线。

#### Scenario: 轮询到待正式上线任务
- **WHEN** 插件 `poll_monitor()` 获取到 `action=finalize_switch` 且任务状态为 `pending_finalize`
- **THEN** 插件 SHALL 使用云端下发的 `switch_run_id`、目标角色和选项调用 `finalize_switch()`
- **AND** 插件 SHALL 上报 `offline`、`online` 和最终 `switch` 事件

#### Scenario: 正式上线成功
- **WHEN** 插件上报正式上线成功并随后上报目标主机为 master
- **THEN** 云监控 SHALL 将任务状态更新为 `success`
- **AND** 云监控 SHALL 更新实际主机状态并触发配置的外部回调

### Requirement: 两段式切换向导
云监控 SHALL 在手动切换入口提供与插件一致的向导式交互，包括选择主机、预上线选项、预上线结果和正式上线确认。

#### Scenario: 操作员完成两段式切换
- **WHEN** 操作员打开切换弹窗
- **THEN** 系统 SHALL 依次展示选择目标主机、配置预上线选项、预上线结果和正式上线按钮
- **AND** 系统 SHALL 在预上线成功前隐藏或禁用正式上线按钮

#### Scenario: 操作员查看执行日志
- **WHEN** 预上线或正式上线正在执行
- **THEN** 系统 SHALL 提供切换日志入口并展示当前任务阶段和最新步骤

### Requirement: 失败重试和取消
云监控 SHALL 支持对两段式切换任务进行失败重试和取消，并保持日志和状态可追踪。

#### Scenario: 重试失败任务
- **WHEN** 操作员对 `waiting_retry` 任务点击重试
- **THEN** 系统 SHALL 根据失败阶段重新设置待领取 action
- **AND** 插件下一次轮询 SHALL 只执行需要重试的阶段动作

#### Scenario: 取消未完成任务
- **WHEN** 操作员取消 `pending_prepare`、`prepared`、`pending_finalize` 或 `waiting_retry` 任务
- **THEN** 系统 SHALL 将任务状态更新为 `cancelled`
- **AND** 插件 SHALL 不再领取该任务动作

