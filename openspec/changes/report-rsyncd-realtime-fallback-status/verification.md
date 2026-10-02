# 实施与验证记录

按最新要求简化为统一最近日志检查，移除独立兜底检测、历史统计、恢复提示和新增采集字段。

## 修改范围

- 面板插件 plugins/rsyncd/tool_check.py：实时与普通定时任务共用最新日志检查；缺失、早于最近 24 小时或内容异常时返回异常。
- 监控端 scripts/report_analyser.py：明细显示两类任务的最近日志结果，沿用既有异常通路并转义任务名称与原因。
- test/test_rsyncd_fallback_report.py：5 组离线检查，含多场景子测试和完整报告模拟发送。

插件 index.py 的本次改动已撤回，执行命令保持原状。采集器、ES 字段及任务调度无需修改。

## 已通过

5 组回归测试全部通过，覆盖两类任务的正常、缺失、过期、窗口边界、超阈值、空日志、权限错误、读取失败、停用任务、容忍警告、最新快照取代旧异常，以及完整单机日报、概览和模拟通知。Python 语法检查及 OpenSpec 严格校验通过。

样例：samples/single-abnormal.html、samples/overview-abnormal.html，使用虚构主机和模拟日志生成。

## 环境限制

前次实际 ES 连接检查返回 Connection refused；使用测试索引执行 test_report_es_persistence.py --host-id H_debian_GsiV --use-test-index --dry-run --send 退出码为 4，模拟发送返回 overview_not_ready。本轮未重复执行已知不可用的环境验证，持久化验收仍待连接恢复后完成。未发真实通知。

## 更新顺序

更新监控端分析器及被采集主机 tool_check.py。常驻任务需要加载新代码时使用 jhm 1 -y；本轮未主动重启服务。回滚恢复这两个文件即可，无需数据迁移或同步计划调整。
