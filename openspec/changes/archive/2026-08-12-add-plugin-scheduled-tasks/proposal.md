## Why

部分江湖面板插件在安装后需要轻量级周期任务，例如 `ha_manager` 需要轮询云监控的期望主备状态，并定期上报本机和对端主备状态。当前这类调度职责不够清晰：如果每个插件各自创建定时器或守护进程，会重复造调度逻辑；如果依赖人工执行，又无法形成稳定的数据上报链路。

## What Changes

- 在插件 `info.json` 中新增声明式定时任务约定。
- 由 `/www/server/jh-panel/task.py` 发现已安装且声明了定时任务的插件，并按配置间隔自动执行。
- 使用 `func` 和 JSON `args` 描述需要调用的插件 `index.py` 方法及参数。
- 支持单任务超时、启用开关、最小执行间隔和轻量执行状态，避免单个插件任务阻塞面板整体监控。
- 将该约定接入 `ha_manager`：插件已安装且云监控上报已配置时，由江湖面板任务进程触发主备状态上报和期望状态轮询。
- 不为该调度路径新增插件自有 crontab、systemd 服务或额外常驻进程。

## Capabilities

### New Capabilities

- `plugin-scheduled-tasks`：插件可以在 `info.json` 中声明周期性 `index.py` 方法调用，江湖面板任务进程会根据声明为已安装插件执行这些方法。

### Modified Capabilities

无。

## Impact

- 影响江湖面板代码：`/www/server/jh-panel/task.py`、插件元数据解析逻辑，以及选择接入定时任务的插件 `info.json`。
- 影响主备插件配置：`/www/server/jh-panel/plugins/ha_manager/info.json` 声明 `poll_monitor` 和 `report_state` 定时任务；现有 `index.py` 方法继续作为实际执行入口。
- 影响云监控行为：`/www/server/jh-monitor` 通过现有 `/pub/ha_*` API 更稳定地接收主备上报；调度器本身不需要新增云监控 public API。
- 运行数据可能新增轻量调度状态或日志文件，用于记录最近执行时间、失败信息和输出摘要。
