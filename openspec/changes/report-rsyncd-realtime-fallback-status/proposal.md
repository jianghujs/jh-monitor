## Why

实时任务被跳过运行日志检查，日志超阈值或异常时日报可能仍显示正常。实时任务应与普通定时任务使用同一套最近日志检查规则。

## What Changes

- 所有已启用同步任务检查最新 run_* 日志是否存在、是否在最近 24 小时内、内容是否正常。
- 实时任务与普通定时任务共用既有日志解析和异常列表，日报展示两类任务的最近同步时间与异常原因。
- 仅根据最新检查结果报告，不统计历史失败次数或恢复状态，不检测独立兜底任务，不修改同步执行入口。

## Capabilities

### New Capabilities

- `rsyncd-realtime-fallback-report`: 实时与普通定时同步任务统一的最近日志检查及日报提醒。

### Modified Capabilities

无。

## Impact

修改面板插件 plugins/rsyncd/tool_check.py 和监控端 scripts/report_analyser.py；复用既有采集、ES 字段与报告发送，不新增数据映射。被采集主机需要更新检查工具。
