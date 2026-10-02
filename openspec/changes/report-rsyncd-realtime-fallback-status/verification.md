# 实施与验证记录

已完成实时任务兜底日志检查、日报窗口内异常汇总和恢复提示。实际 ES 映射与持久化验证受环境连接失败阻塞，暂不归档。

## 交付文件

| 仓库 | 文件 | 用途 |
| --- | --- | --- |
| jh-panel | plugins/rsyncd/index.py | 兜底运行记录开始 PID、结束结果和标准错误 |
| jh-panel | plugins/rsyncd/tool_check.py | 最近 24 小时运行证据、当前历史状态及旧字段兼容 |
| jh-monitor | scripts/report_analyser.py | 合并快照、去重、失败恢复判定与日报展示 |
| jh-monitor | test/test_rsyncd_fallback_report.py | 11 项离线回归验证，包含完整报告和模拟发送 |

report_collector.py 已通过大于 8000 字符结构化结果及超时验证，无需修改。task.py、report_sender.py、同步计划及历史索引结构未修改。

## 已通过验证

- Python 语法检查：上述修改文件全部通过。
- python3 test/test_rsyncd_fallback_report.py：11 项通过；覆盖超阈值、预检与连接错误、普通定时检查、23/24 容忍策略、运行中和中断、日志大小上限、跨窗口日志、失败恢复、重复快照、日志清理、旧版与停用任务、HTML 转义、采集截断与超时、完整单机及概览渲染、模拟通知。
- python3 test/test_report_collected_host_name.py：通过。
- python3 test/test_report_analyser_host.py：通过。
- 在 /www/server/jh-panel 下运行 python3 plugins/rsyncd/index.py status '{}'：输出 start。
- 两个仓库的 git diff --check 通过。
- openspec validate report-rsyncd-realtime-fallback-status --strict：通过。

可审阅样例为 samples/single-recovered.html 和 samples/overview-recovered.html，使用虚构主机及模拟运行日志生成，包含“曾异常，已恢复”提示。

## 未完成的环境验证

源码 host-debian-backup 映射允许动态字段，报告仍使用既有字段。当前 ES 适配器从 data/es.json 的 hosts 读取地址，本机配置使用旧 addr 字段，适配器回退到本机端点并被拒绝。另行只读检查旧 addr 指定的 192.168.3.33:9200 也返回 ConnectionError，未修改连接配置或凭据，未能确认实际集群和映射。

已执行：

    python3 test/test_report_es_persistence.py --host-id H_debian_GsiV --use-test-index --dry-run --send

结果：退出码 4，ES Connection refused，测试报告回读不存在，模拟发送流程返回 overview_not_ready，dry_run_messages 为空。真实通知未发送；日志保存于 /tmp/rsyncd-fallback-persistence-check.log。此结果不能作为持久化通过依据。

ES 恢复后应先只读确认目标集群、原始 result 映射及新增字段类型，再使用上述测试索引命令完成持久化验收。任务 1.2 与 4.3 保持未完成。

## 更新与回滚

1. 发布监控端分析器；需要加载常驻任务新代码时使用 jhm 1 -y。当前未主动重启或部署。
2. 被采集主机配套更新 rsyncd/index.py 与 tool_check.py。无需调整既有兜底计划或重新生成同步 cmd。
3. 等待正常采集，确认 result.fallback_check_version 为 1，核对下一次日报。旧插件显示“未提供兜底检查，请更新插件”。
4. 回滚恢复对应代码即可，新增采集字段可以保留；不迁移历史报告，也不主动运行真实同步或发送通知。

日志中的 PID 用于区分新运行的进行中状态；旧日志有明确异常或完整成功汇总时仍可判定，缺少完成证据时提示未知。未曾采集且已被清理的历史日志无法恢复。无运行记录不自动视为计划未执行故障。
