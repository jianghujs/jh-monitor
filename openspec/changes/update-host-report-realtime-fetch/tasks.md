## 1. 实施
- [x] 1.1 更新 `scripts/client/get_panel_report.py`，支持 `get_report_data` 输出 JSON。
- [x] 1.2 为 `scripts/client/get_pve_hardware_report.py` 增加 `get_report_data` 模式并输出 JSON。
- [x] 1.3 调整脚本执行辅助方法，支持在目标主机上运行并返回 stdout 以供解析。
- [x] 1.4 更新 `task.py` 主机报告发送流程：执行脚本、解析 JSON、使用现有模板渲染邮件。
- [x] 1.5 脚本执行失败或返回无效 JSON 时发送“获取报告异常”邮件。
- [x] 1.6 当 `is_jhpanel` 与 `is_pve` 同时为真时，按顺序发送两份报告（先面板后 PVE）。

## 2. 验证
- [x] 2.1 执行 `get_panel_report.py get_report_data` 并确认输出 JSON。
- [x] 2.2 执行 `get_pve_hardware_report.py get_report_data` 并确认输出 JSON。
- [ ] 2.3 触发报告发送并验证实时报告邮件（面板和/或 PVE）。
- [ ] 2.4 模拟脚本失败并确认发送异常邮件。
