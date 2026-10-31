## Why

主机管理和主备管理当前会长期展示最后一次上报携带的“运行中/正常”状态，无法识别数据已经超过 24 小时没有更新；日报虽然有数据缺失和过期检查，但没有与页面共用明确的 24 小时上报异常语义。需要建立统一的上报新鲜度规则，避免失联主机继续显示正常。

## What Changes

- 新增统一的 24 小时上报新鲜度判定：最近上报时间距判定时间达到 24 小时后，状态视为“上报异常”。
- 主机管理列表基于系统状态的最近上报时间计算当前展示状态，区分“已停止”和“超过24小时未上报”。
- 主备管理按关系中的每台机器分别检查 `last_report_at`；任一机器超过 24 小时未上报时，整组关系显示异常并指出具体机器。
- 服务器日报把超过 24 小时未上报的主机和主备机器纳入异常摘要，并使用统一的异常文案和最近上报时间。
- 对从未上报的对象设置 24 小时宽限期：创建或注册不足 24 小时显示“待上报”，达到 24 小时后显示异常。
- 保留日报现有更严格的数据完整性检查；本变更只新增跨模块一致的 24 小时硬异常语义，不放宽已有告警。
- 新鲜度状态在读取和报告生成时动态计算，不覆写原始上报状态或历史记录。

## Capabilities

### New Capabilities

- `reporting-freshness-health`: 定义主机管理、主备管理和服务器日报共用的 24 小时上报新鲜度判定、展示字段和异常摘要行为。

### Modified Capabilities

- `ha-management-ui`: 主备列表和详情需要把单机超过 24 小时未上报视为红色异常，并显示具体机器及最近上报时间。

## Impact

- 影响主机状态读取与列表 API：`class/es/mapper/host_status_mapper.py`、`class/es/service/host_status_service.py`、`class/core/host_api.py`。
- 影响主机管理页面：`route/static/app/host.js`，以及必要时对应模板的静态资源版本。
- 影响主备状态派生与快照输出：`class/core/ha_api.py`、`class/core/ha_read_snapshot.py`。
- 影响主备管理页面：`route/static/app/ha_management.js`，以及必要时 `route/templates/default/ha_management.html`。
- 影响日报分析和总览模板：`scripts/report_analyser.py`、`route/templates/report/host_overview_report.html`。
- 需要为时间边界、从未上报、单侧主备失联、恢复上报和日报摘要增加针对性测试。
- 不新增外部依赖，不修改 Elasticsearch 映射，不对现有 SQLite 状态字段执行数据迁移。
