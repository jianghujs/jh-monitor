## 1. 云端任务模型

- [ ] 1.1 扩展 `class/core/ha_api.py` 的 HA schema，增加两段式切换需要的 action、目标主机、预上线完成时间、正式上线确认时间等兼容字段。
- [ ] 1.2 定义并实现 `pending_prepare`、`preparing`、`prepared`、`pending_finalize`、`finalizing`、`success`、`waiting_retry`、`cancelled` 状态转换。
- [ ] 1.3 调整旧 `pending/running/success/waiting_retry` 数据的读取兼容映射，避免旧任务展示或日志读取异常。

## 2. 云端管理 API

- [ ] 2.1 新增预上线创建 API，校验 pair 和目标主机，创建 `pending_prepare` 任务且不修改 `desired_master_host_id`。
- [ ] 2.2 新增正式上线确认 API，只允许 `prepared` 任务进入 `pending_finalize`，并在此时更新 `desired_master_host_id`。
- [ ] 2.3 调整 `request_switch` 旧入口兼容策略，确保旧调用不会绕过两段式状态机造成数据不一致。
- [ ] 2.4 调整重试 API，根据失败阶段重新设置待领取 action 和状态。
- [ ] 2.5 调整取消 API，确保取消后的任务不会再被插件领取执行。

## 3. 插件轮询与执行

- [ ] 3.1 调整 `/pub/ha_pull_desired_state` 返回 action、目标主机、目标角色、状态、阶段、选项和日志路径。
- [ ] 3.2 在 `/www/server/jh-panel/plugins/ha_manager/index.py` 的 `poll_monitor()` 中识别 `prepare_switch` 和 `finalize_switch` action。
- [ ] 3.3 为插件增加本地 `switch_run_id + action` 领取状态记录，避免定时轮询重复启动同一阶段。
- [ ] 3.4 复用插件现有 `prepare_switch()`、`finalize_switch()`、`switch.lock` 和日志上报逻辑执行云端任务。
- [ ] 3.5 确保云端任务取消或非待领取状态时，插件只更新本地期望信息，不启动脚本。

## 4. 事件、状态和回调

- [ ] 4.1 调整 `publicReportSwitchEvent()` 和/或 `publicAckSwitchPhase()`，将 `prepare_online` 成功映射为 `prepared`。
- [ ] 4.2 将正式上线执行中的 `offline/online` 事件映射为 `finalizing`，失败映射为 `waiting_retry`。
- [ ] 4.3 正式上线成功后等待插件状态上报确认目标主机为 master，再将任务标记为 `success` 并触发回调。
- [ ] 4.4 确保预上线成功不会触发外部回调。

## 5. 云端切换向导

- [ ] 5.1 将 `ha_management.js` 的切换弹框改为选择主机、预上线选项、预上线结果、正式上线确认的向导。
- [ ] 5.2 预上线成功前隐藏或禁用正式上线按钮。
- [ ] 5.3 展示预上线日志入口、正式上线执行状态、失败重试和取消操作。
- [ ] 5.4 复用插件一致的切换选项字段和中文文案。

## 6. 验证

- [ ] 6.1 新增或更新云端 HA API 测试，覆盖预上线创建不改 `desired_master_host_id`。
- [ ] 6.2 新增或更新云端 HA API 测试，覆盖 `prepared` 后确认正式上线才更新期望主机。
- [ ] 6.3 新增或更新插件轮询测试，覆盖 action 领取、重复执行保护、取消不执行。
- [ ] 6.4 新增或更新端到端模拟测试，覆盖预上线、人工确认、正式上线、状态上报和回调。
- [ ] 6.5 运行 `python3 -m py_compile /www/server/jh-monitor/class/core/ha_api.py /www/server/jh-panel/plugins/ha_manager/index.py`。
- [ ] 6.6 运行现有 HA 相关测试脚本并记录结果。
