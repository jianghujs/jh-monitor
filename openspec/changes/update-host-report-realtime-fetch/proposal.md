# 变更：改为实时脚本获取主机报告

## 为什么
现有主机报告发送依赖 ES 日志读取，无法保证报告内容实时性。需要在发送时到目标服务器执行脚本获取最新报告，并在失败时通知异常。

## 变更内容
- 在 `task.py` 的主机报告发送流程中改为实时执行脚本获取报告内容。
- 对 `is_jhpanel` 主机执行 `scripts/client/get_panel_report.py get_report_data` 获取报告 JSON。
- 对 `is_pve` 主机执行 `scripts/client/get_pve_hardware_report.py get_report_data` 获取报告 JSON。
- 当两者同时为真时，依次发送两封邮件（先面板报告，后 PVE 报告）。
- 报告脚本执行失败或返回不可解析内容时发送“获取报告异常”邮件。

## 影响范围
- 受影响规格：`specs/deliver-host-report/spec.md`
- 受影响代码：`task.py`、`scripts/client/get_panel_report.py`、`scripts/client/get_pve_hardware_report.py`、`scripts/client/run_script_batch.py`/`scripts/client/run_script_batch.yml`（如需支持定向执行与结果解析）
