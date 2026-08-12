## ADDED Requirements

### Requirement: 插件元数据声明定时任务
插件 SHALL 能够在 `info.json` 中通过 `tasks` 数组声明周期任务。每个启用的任务 MUST 使用 `func` 标识需要调用的插件方法，并 MAY 提供 `args`、`interval`、`timeout`、`title` 字段。

#### Scenario: 有效任务声明
- **WHEN** 插件 `info.json` 中存在启用状态的任务，并包含 `func`、`args`、`interval`、`timeout`
- **THEN** 面板调度器按该任务的执行间隔识别其是否可执行

#### Scenario: 缺少任务声明
- **WHEN** 插件 `info.json` 没有 `tasks` 字段，或 `tasks` 数组为空
- **THEN** 面板调度器忽略该插件的定时调度，不报错

#### Scenario: 禁用任务声明
- **WHEN** 插件任务的 `enabled` 设置为 false
- **THEN** 面板调度器 MUST NOT 执行该任务

### Requirement: 调度器只执行已安装插件的任务
面板调度器 SHALL 只在插件根据现有安装检查元数据判定为已安装时，执行该插件声明的定时任务。

#### Scenario: 已安装插件存在到期任务
- **WHEN** 插件已安装，并且启用的声明任务已达到执行间隔
- **THEN** 面板调度器执行该插件声明的方法

#### Scenario: 未安装插件存在任务声明
- **WHEN** 插件存在任务声明，但插件安装检查路径不存在
- **THEN** 面板调度器 MUST NOT 执行该任务

### Requirement: 调度器安全调用插件声明函数
面板调度器 SHALL 通过插件 `index.py` 入口调用声明的 `func`，并传入序列化后的 JSON `args`。调度器 MUST NOT 执行来自 `info.json` 任务声明的任意 shell 命令字符串。

#### Scenario: 根据插件和 func 构造执行入口
- **WHEN** 调度器执行插件 `ha_manager` 的 `report_state` 任务，且参数为空
- **THEN** 调度器调用等价于 `python3 /www/server/jh-panel/plugins/ha_manager/index.py report_state '{}'` 的插件入口

#### Scenario: 非法 func 名称
- **WHEN** 任务声明中的 `func` 不符合允许的插件方法名格式
- **THEN** 调度器跳过该任务，并记录简短的校验失败摘要

### Requirement: 调度器执行间隔和超时控制
面板调度器 SHALL 强制执行每个任务配置的执行间隔和超时时间。当声明缺失或提供无效值时，调度器 MUST 使用安全的最小间隔和默认超时时间。

#### Scenario: 任务尚未到期
- **WHEN** 某任务上次成功执行距离当前时间小于配置的 `interval`
- **THEN** 调度器 MUST NOT 在间隔到达前再次执行该任务

#### Scenario: 任务执行超时
- **WHEN** 插件任务运行时间超过配置的 `timeout`
- **THEN** 调度器终止该执行或停止等待，记录超时结果，并继续处理其他任务

### Requirement: 调度器隔离插件任务失败
插件任务失败 SHALL NOT 停止面板任务进程，也 SHALL NOT 阻止无关的插件定时任务继续执行。

#### Scenario: 单个插件任务失败
- **WHEN** 某个定时插件任务退出错误或触发超时
- **THEN** 调度器记录失败结果，并继续运行调度循环

#### Scenario: 失败后其他插件任务到期
- **WHEN** 上一个任务失败后，另一个有效插件任务到达执行时间
- **THEN** 调度器仍然执行该到期任务

### Requirement: HA manager 声明云监控任务
`ha_manager` 插件 SHALL 使用插件定时任务约定声明轮询云监控期望状态和上报主备状态的任务。

#### Scenario: HA manager 已配置云监控上报
- **WHEN** `ha_manager` 已安装，并且其云监控配置启用了上报
- **THEN** 面板调度器周期性通过插件入口调用 `poll_monitor` 和 `report_state`

#### Scenario: HA manager 云监控地址为空
- **WHEN** `ha_manager` 已安装，但云监控地址为空或上报被禁用
- **THEN** 定时调用不会向云监控上传主备状态，插件调用无需调度器特殊处理即可快速返回
