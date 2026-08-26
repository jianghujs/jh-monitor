## Why

现有云监控主备切换主要覆盖两台机器都可达时的正常切换，但真实故障中经常出现旧主停机或对端不可达。此时仍需要由存活的主备管理插件完成临时升主，并在旧主恢复后由两边插件协调把旧主补全为备机，避免依赖云监控参与恢复决策。

## What Changes

- 主备管理插件增加插件间协调能力：本机插件可检查对端 SSH、对端插件、切换锁和当前角色状态。
- 当本机插件能连到对端时，允许云监控从本机房发起完整双边切换，由本机插件作为协调者执行本地阶段并远程触发对端插件阶段。
- 当对端不可达但本机可执行时，允许把本机切换为主，跳过不可达旧主的下线阶段，并进入降级运行状态。
- 降级切换后，插件侧记录对端服务器的待切换标识和当前主备状态；故障服务器恢复后，由 `task.py` 周期触发插件读取对端角色和待切换标识，发现本机应切换为备用机时发送邮件通知，并按人工确认或自动开关执行恢复补全。
- 云监控只作为状态展示、人工入口和日志归档，不作为旧主恢复为备机的状态来源或仲裁者。
- 所有故障升主、跳过下线、邮件通知、恢复为备机、恢复完成的步骤都要写入插件本地日志，并继续上报到云监控展示。

## Capabilities

### New Capabilities

- `ha-plugin-failover-recovery`: 定义主备管理插件之间协调故障切换、降级运行和旧主恢复为备机的行为。

### Modified Capabilities

无。

## Impact

- Affected panel plugin: `/www/server/jh-panel/plugins/ha_manager/index.py` 的主备切换、对端检查、插件间通信、故障升主和恢复为备机流程。
- Affected panel plugin UI: `/www/server/jh-panel/plugins/ha_manager/index.html` 或相关前端脚本中切换弹框、故障提示、恢复为备机入口和状态展示。
- Affected panel task integration: `/www/server/jh-panel/task.py` 通过插件定时任务继续触发状态上报和必要的插件侧协调检查。
- Affected cloud monitor backend: `/www/server/jh-monitor/class/core/ha_api.py` 接收并展示插件上报的降级运行、待切换标识、恢复中和恢复完成状态。
- Affected cloud monitor frontend: `/www/server/jh-monitor/route/static/app/ha_management.js` 展示切换执行方式、降级运行、待切换主机和恢复日志。
- Affected logs: `/www/server/logs` 下新增或扩展主备管理插件与云监控/对端插件交互日志。
