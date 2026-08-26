# ha-plugin-failover-recovery Specification

## Purpose
TBD - created by archiving change support-ha-plugin-coordinated-failover-recovery. Update Purpose after archive.
## Requirements
### Requirement: 插件切换前判断执行模式
主备管理插件 SHALL 在执行主备切换前检查本机与对端的可达性和执行能力，并给出明确的执行模式。

#### Scenario: 本机和对端均可执行
- **WHEN** 本机插件可运行，且本机插件能够通过绑定的 SSH 信息连接对端并触发对端主备管理插件
- **THEN** 插件 SHALL 将执行模式标记为 `full_switch`
- **AND** 系统 SHALL 允许选择任一主机作为切换目标

#### Scenario: 对端不可达且目标为本机
- **WHEN** 本机插件可运行，但对端 SSH 或对端插件不可达，且操作员选择本机作为目标主机
- **THEN** 插件 SHALL 将执行模式标记为 `local_failover`
- **AND** 系统 SHALL 提示本次会跳过对端下线阶段并进入降级运行

#### Scenario: 对端不可达且目标为对端
- **WHEN** 本机插件可运行，但对端 SSH 或对端插件不可达，且操作员选择对端作为目标主机
- **THEN** 插件 SHALL 拒绝创建或执行切换
- **AND** 系统 SHALL 返回目标主机不可达、请到目标机房处理或等待目标恢复的错误说明

### Requirement: 插件协调完整双边切换
当执行模式为 `full_switch` 时，主备管理插件 SHALL 作为协调者复用现有主备切换流程执行完整双边切换。

#### Scenario: 切换到本机
- **WHEN** 执行模式为 `full_switch`，且目标主机是本机
- **THEN** 协调者插件 SHALL 本地执行目标主机上线阶段
- **AND** 协调者插件 SHALL 通过 SSH 触发对端插件执行下线或备机化阶段
- **AND** 插件 SHALL 上报执行方式、阶段日志和最终结果

#### Scenario: 切换到对端
- **WHEN** 执行模式为 `full_switch`，且目标主机是对端
- **THEN** 协调者插件 SHALL 通过 SSH 触发对端插件执行上线阶段
- **AND** 协调者插件 SHALL 本地执行下线或备机化阶段
- **AND** 插件 SHALL 上报执行方式、阶段日志和最终结果

### Requirement: 对端不可达时支持本机故障升主
当执行模式为 `local_failover` 时，主备管理插件 SHALL 允许本机升主并跳过不可达对端的下线阶段。

#### Scenario: 本机故障升主成功
- **WHEN** 操作员确认对端不可达且选择本机升主
- **THEN** 插件 SHALL 执行本机上线或强制升主流程
- **AND** 插件 MUST NOT 等待不可达对端执行下线阶段
- **AND** 插件 SHALL 将主备关系标记为降级运行
- **AND** 插件 SHALL 记录不可达主机、待切换主机、待切换目标角色、协调主机和跳过下线原因

#### Scenario: 本机故障升主失败
- **WHEN** 本机上线或强制升主流程执行失败
- **THEN** 插件 SHALL 保留失败日志和失败原因
- **AND** 系统 MUST NOT 将主备关系标记为正常

### Requirement: 插件持久化降级运行状态和待切换标识
主备管理插件 SHALL 在故障升主后持久化降级运行状态和对端待切换标识，用于后续故障服务器恢复后补全为备机。

#### Scenario: 写入降级状态
- **WHEN** 本机故障升主成功
- **THEN** 插件 SHALL 在本地状态中保存 `mode=degraded_master`、`current_master_host_id`、`pending_switch_host_id`、`pending_switch_role=standby`、`unreachable_host_id`、`coordinator_host_id`、`failover_run_id`、`pending_switch_required=true` 和 `reason`
- **AND** 插件 SHALL 将同等语义的状态上报到云监控用于展示

#### Scenario: 降级状态可被对端读取
- **WHEN** 对端插件恢复后请求当前主插件的协调状态
- **THEN** 当前主插件 SHALL 返回当前主机、待切换主机、待切换目标角色和最近故障切换信息

### Requirement: task 进程触发旧主恢复检查
江湖面板 task 进程 SHALL 通过插件定时任务机制周期触发主备管理插件执行恢复检查，主备管理插件 SHALL 在检查中读取对端角色和待切换标识，并判断本机是否属于故障恢复后的角色不匹配主机。

#### Scenario: task 进程触发恢复检查
- **WHEN** 主备管理插件已安装且江湖面板 task 进程正在运行
- **THEN** task 进程 SHALL 周期性调用主备管理插件的恢复检查入口或等价的定时任务入口
- **AND** task 进程 MUST NOT 自行判断主备角色或执行恢复脚本

#### Scenario: 插件发现待切换标识匹配本机
- **WHEN** 恢复检查发现对端插件声明当前主机不是本机，且对端 `pending_switch_host_id` 等于本机 host_id、`pending_switch_role=standby`
- **AND** 本机仍处于主角色或主角色配置未完成备机化
- **THEN** 主备管理插件 SHALL 判定本机需要补全切换为备用机
- **AND** 插件 SHALL 记录角色不匹配原因、对端角色和待切换标识

### Requirement: 旧主恢复后进入恢复保护或自动恢复
旧主恢复后，主备管理插件 SHALL 优先检查对端协调状态，并在确认本机匹配待切换标识时发送通知，然后进入恢复保护状态或按配置自动恢复为备机。

#### Scenario: 恢复旧主识别待切换状态
- **WHEN** 旧主机器恢复并启动主备管理插件
- **AND** 对端插件返回 `mode=degraded_master` 且 `pending_switch_host_id` 等于本机 host_id、`pending_switch_role=standby`
- **THEN** 本机插件 SHALL 在自动恢复未开启时进入 `recovery_guard` 状态
- **AND** 本机插件 SHALL 阻止本机按正常主机身份继续完成主备闭环
- **AND** 本机插件 SHALL 展示或上报待切换为备机状态

#### Scenario: 发送恢复补全通知
- **WHEN** 本机插件确认本机匹配对端待切换标识，且本机需要切换为备用机
- **THEN** 插件 SHALL 发出邮件通知
- **AND** 通知内容 SHALL 包含当前主机、待切换主机、目标角色、恢复方式和操作入口说明

#### Scenario: 自动恢复配置开启
- **WHEN** 旧主机器恢复并启动主备管理插件
- **AND** 对端插件返回 `mode=degraded_master` 且 `pending_switch_host_id` 等于本机 host_id、`pending_switch_role=standby`
- **AND** 主备关系配置启用了自动恢复为备机
- **THEN** 本机插件 SHALL 直接领取并执行 `recover_as_standby` 流程
- **AND** 本机插件 SHALL 使用本地恢复锁避免重复执行

#### Scenario: 无法确认对端协调状态
- **WHEN** 旧主恢复后无法连接对端插件或无法确认当前主机
- **THEN** 本机插件 SHALL 保持待人工处理状态
- **AND** 本机插件 MUST NOT 自动恢复为主或自动覆盖本机数据

### Requirement: 插件执行恢复为备机流程
主备管理插件 SHALL 在人工确认或自动恢复配置开启后，将恢复旧主执行为备机。

#### Scenario: 人工确认恢复为备机
- **WHEN** 本机处于 `recovery_guard`，且操作员确认恢复为备机
- **THEN** 本机插件 SHALL 执行恢复为备机流程
- **AND** 流程 SHALL 包含停止主角色能力、执行备机化脚本、重建或恢复同步方向、执行自检和上报 `role=standby`

#### Scenario: 自动恢复为备机
- **WHEN** 本机处于 `recovery_guard`，且主备关系配置启用了自动恢复为备机
- **THEN** 本机插件 SHALL 自动执行恢复为备机流程
- **AND** 插件 SHALL 在日志中明确记录自动恢复配置、执行开始、关键步骤和执行结果

#### Scenario: 恢复为备机完成
- **WHEN** 旧主插件恢复为备机成功并上报 `role=standby`
- **THEN** 当前主插件 SHALL 清除待切换主机状态
- **AND** 双方插件 SHALL 在后续上报中体现主备关系恢复正常

### Requirement: 云监控展示插件协调状态
云监控 SHALL 展示插件上报的故障切换和恢复状态，但 MUST NOT 作为旧主恢复为备机的决策来源。

#### Scenario: 展示降级运行
- **WHEN** 插件上报 `mode=degraded_master` 或 `pending_switch_required=true`
- **THEN** 云监控 SHALL 在主备列表和详情中展示当前主机、待切换主机、目标角色、降级原因和最近故障切换时间

#### Scenario: 展示恢复中和恢复完成
- **WHEN** 插件上报 `recovery_guard`、`recovering_standby` 或恢复完成状态
- **THEN** 云监控 SHALL 展示恢复状态和相关日志
- **AND** 云监控 MUST NOT 下发恢复为备机任务作为该流程的唯一触发来源

### Requirement: 故障切换和恢复日志可追踪
主备管理插件 SHALL 记录故障切换、插件间通信和恢复为备机的关键日志，并继续上报到云监控。

#### Scenario: 本地插件日志记录
- **WHEN** 插件执行可达性检查、故障升主、跳过对端下线、进入恢复保护或恢复为备机
- **THEN** 插件 SHALL 在 `/www/server/logs` 下记录时间、动作、执行方式、目标主机、失败原因和结果

#### Scenario: 云监控日志展示
- **WHEN** 插件上报故障切换或恢复事件
- **THEN** 云监控 SHALL 在主备详情日志中展示对应事件
- **AND** 日志 SHALL 能区分完整双边切换、本机故障升主、恢复保护和恢复为备机

