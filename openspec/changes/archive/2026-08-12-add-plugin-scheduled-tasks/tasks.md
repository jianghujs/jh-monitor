## 1. 调度元数据解析

- [x] 1.1 定义 `info.json.tasks` 的支持字段，包括 `func`、`args`、`interval`、`timeout`、`enabled` 和可选的 `title`。
- [x] 1.2 在 `/www/server/jh-panel/task.py` 中增加安全解析逻辑，扫描插件 `info.json` 并提取有效的定时任务声明。
- [x] 1.3 复用现有插件安装检查语义，确保未安装插件的任务不会被执行。
- [x] 1.4 校验 `func` 名称格式，跳过非法任务声明并记录简短失败摘要。

## 2. 调度执行循环

- [x] 2.1 在 `/www/server/jh-panel/task.py` 中新增一个专门的 daemon 线程用于插件定时任务。
- [x] 2.2 记录每个插件任务的上次执行时间、下一次可执行时间、最近状态和简短错误摘要。
- [x] 2.3 通过 `python3 /www/server/jh-panel/plugins/<plugin>/index.py <func> <args_json>` 执行到期任务。
- [x] 2.4 强制最小间隔、默认超时、配置超时和输出长度上限。
- [x] 2.5 确保失败或超时的插件任务不会停止调度循环，也不会影响其他面板任务线程。

## 3. HA Manager 定时任务接入

- [x] 3.1 更新 `/www/server/jh-panel/plugins/ha_manager/info.json`，声明 `poll_monitor` 和 `report_state` 定时任务。
- [x] 3.2 确保 `poll_monitor` 在云监控地址为空或上报被禁用时能快速、安全退出。
- [x] 3.3 确保 `report_state` 在云监控地址为空或上报被禁用时能快速、安全退出。
- [x] 3.4 确认 `ha_manager` 的定时调用继续使用现有插件配置，不需要 crontab 或 systemd 条目。

## 4. 可观测性与运维

- [x] 4.1 为插件定时任务结果写入轻量调度状态或日志。
- [x] 4.2 补充足够的失败信息，便于定位非法元数据、超时、缺少插件入口和非零退出。
- [x] 4.3 控制调度输出的大小，避免重复失败导致日志无限增长。

## 5. 验证

- [x] 5.1 执行 `python3 -m py_compile /www/server/jh-panel/task.py`。
- [x] 5.2 执行 `python3 -m py_compile /www/server/jh-panel/plugins/ha_manager/index.py`。
- [x] 5.3 校验 `/www/server/jh-panel/plugins/ha_manager/info.json` 的 JSON 格式。
- [x] 5.4 执行 `python3 /www/server/jh-panel/plugins/ha_manager/index.py status '{}'`，确认其能快速返回。
- [x] 5.5 模拟插件已安装和未安装状态，确认调度器只会执行已安装插件的任务。
- [x] 5.6 模拟成功、失败、非法和超时任务，确认失败隔离行为符合预期。
