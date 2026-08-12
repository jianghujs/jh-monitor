## ADDED Requirements

### Requirement: 真实主备列表展示
云监控 SHALL 在主备列表中基于插件上报和云端落库的真实数据展示主备关系名称、主机列表、实际主机、期望主机、状态等级、状态说明和最近上报时间。

#### Scenario: 插件已上报主备状态
- **WHEN** 操作员打开云监控主备管理列表
- **THEN** 系统 SHALL 展示插件上报的主机名称、IP、角色、在线状态和最近上报时间
- **AND** 系统 SHALL 根据真实运行中切换任务、实际角色、期望主机、采集状态和健康状态展示状态等级

#### Scenario: 缺少真实上报数据
- **WHEN** 主备关系存在但没有主机状态或自检明细
- **THEN** 系统 SHALL 显示未知、等待上报或暂无自检明细
- **AND** 系统 MUST NOT 生成模拟的 MySQL 延迟、rsync 异常、lsyncd warning 或其他伪造状态

### Requirement: 真实自检明细展示
云监控 SHALL 在主备详情自检页中按主机展示插件上报的自检明细，并保留采集来源和采集状态。

#### Scenario: 插件上报脚本检查项
- **WHEN** 主机状态包含 `script_checks` 或 `health_detail.script_checks`
- **THEN** 系统 SHALL 按检查分组展示检查项名称、期望状态、实际状态、状态等级和说明
- **AND** 系统 SHALL 区分 `pass`、`warning`、`failed`、`unknown` 等结果

#### Scenario: 只有健康摘要
- **WHEN** 主机状态只有 `health_detail.summary` 或服务摘要字段
- **THEN** 系统 SHALL 展示摘要信息和健康等级
- **AND** 系统 SHALL 明确提示暂无逐项自检明细

### Requirement: 真实切换状态展示
云监控 SHALL 在主备详情切换状态页展示当前切换任务和每台主机的真实阶段、状态、当前步骤、下一步、错误信息和日志路径。

#### Scenario: 存在运行中的切换任务
- **WHEN** `ha_switch_run.status` 为 `pending`、`running`、`waiting_retry` 或两段式切换状态
- **THEN** 系统 SHALL 展示 `switch_run_id`、任务状态、当前阶段、当前步骤、下一步、最后错误和日志路径
- **AND** 系统 SHALL 使用主机上报的 `switch_phase`、`switch_status`、`current_step` 补充每台主机参与情况

#### Scenario: 没有运行中的切换任务
- **WHEN** 主备关系没有当前切换任务
- **THEN** 系统 SHALL 展示无执行中任务
- **AND** 系统 SHALL 保留最近一次任务日志入口（如果存在）

### Requirement: 切换日志按来源展示
云监控 SHALL 支持展示完整切换日志，并在存在事件来源信息时按主机来源分组展示日志。

#### Scenario: 切换事件包含来源主机
- **WHEN** `ha_switch_event` 中存在 `origin_host_id`
- **THEN** 系统 SHALL 按来源主机展示对应日志行
- **AND** 系统 SHALL 同时提供完整日志视图

#### Scenario: 只有日志文件内容
- **WHEN** 没有可用的事件来源行但存在日志文件
- **THEN** 系统 SHALL 展示完整日志内容
- **AND** 系统 SHALL 尽量根据日志中的 host_id 或来源标记分组，无法分组时不得隐藏完整日志
