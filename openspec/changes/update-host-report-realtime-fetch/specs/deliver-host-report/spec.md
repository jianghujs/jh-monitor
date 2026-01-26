## MODIFIED Requirements

### Requirement: 按频率发送主机报告邮件
系统 SHALL 在报告触发时实时执行目标主机上的报告脚本获取报告内容，而不是依赖历史日志。

#### Scenario: 发送面板报告
- **WHEN** 主机 `is_jhpanel` 为真且到达发送频率
- **THEN** 系统在该主机上执行 `scripts/client/get_panel_report.py get_report_data`
- **AND** 使用脚本输出的 JSON 渲染面板报告邮件并发送

#### Scenario: 发送 PVE 报告
- **WHEN** 主机 `is_pve` 为真且到达发送频率
- **THEN** 系统在该主机上执行 `scripts/client/get_pve_hardware_report.py get_report_data`
- **AND** 使用脚本输出的 JSON 渲染 PVE 报告邮件并发送

#### Scenario: 同时发送两类报告
- **WHEN** 主机 `is_jhpanel` 与 `is_pve` 同时为真且到达发送频率
- **THEN** 系统先发送面板报告邮件
- **AND** 随后发送 PVE 报告邮件

## ADDED Requirements

### Requirement: 报告脚本 JSON 输出
系统 SHALL 支持通过 `get_report_data` 参数获取报告 JSON，并将 JSON 输出到 stdout。

#### Scenario: 获取面板报告 JSON
- **WHEN** 执行 `get_panel_report.py get_report_data`
- **THEN** stdout 返回可解析的报告 JSON

#### Scenario: 获取 PVE 报告 JSON
- **WHEN** 执行 `get_pve_hardware_report.py get_report_data`
- **THEN** stdout 返回可解析的报告 JSON

### Requirement: 报告获取异常通知
系统 SHALL 在报告脚本执行失败或报告 JSON 无法解析时发送“获取报告异常”邮件。

#### Scenario: 脚本执行失败
- **WHEN** 报告脚本执行失败
- **THEN** 系统发送“获取报告异常”邮件

#### Scenario: 报告 JSON 无法解析
- **WHEN** 脚本输出无法解析为 JSON
- **THEN** 系统发送“获取报告异常”邮件
