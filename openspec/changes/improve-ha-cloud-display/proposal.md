## Why

江湖面板 `ha_manager` 插件已经能够周期上报真实主备状态、自检结果和切换日志，但云监控主备管理页面仍保留较多模拟展示逻辑，无法准确反映插件上报的 `health_detail`、主机采集状态和切换阶段。现在需要先把云端展示改为以真实上报数据为准，让运维人员能在云监控中看到和插件一致的主备状态、自检明细与日志线索。

## What Changes

- 云监控主备列表和详情页改为渲染插件真实上报字段，不再用固定模板模拟 MySQL 延迟、lsyncd 异常等状态。
- 后端规范化返回主机自检明细、主机采集来源、主机切换状态、当前切换任务摘要和日志路径。
- 自检状态按插件上报的 `health_detail.script_checks` 或等价结构分组展示；缺失真实明细时只显示未知/暂无上报，不伪造成功或异常。
- 切换状态页使用真实 `ha_switch_run`、`ha_host_state` 和 `ha_switch_event` 数据展示当前阶段、步骤、错误和每台主机参与情况。
- 切换日志按来源主机尽量分组展示，并保留完整日志视图。
- 保留当前登录态管理 API 和插件上报 API，不引入新的存储系统。
- 不在本变更中实现云端触发插件执行切换；切换执行流程由后续变更处理。

## Capabilities

### New Capabilities

- `ha-cloud-real-display`: 云监控 SHALL 基于插件真实上报数据展示主备关系、主机健康、自检明细、切换状态和切换日志。

### Modified Capabilities

- None.

## Impact

- Affected cloud monitor backend: `/www/server/jh-monitor/class/core/ha_api.py` 中列表、详情、日志读取和数据规范化逻辑。
- Affected cloud monitor frontend: `/www/server/jh-monitor/route/static/app/ha_management.js` 和 `/www/server/jh-monitor/route/templates/default/ha_management.html` 中主备列表、详情、自检、切换状态、日志展示。
- Affected data model: 继续使用现有 SQLite 表 `ha_pair`、`ha_host_state`、`ha_switch_run`、`ha_switch_event`，必要时只增加兼容字段或规范化输出字段。
- Tests: 需要补充后端规范化数据测试和前端数据渲染相关的轻量验证。
