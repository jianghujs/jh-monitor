## 背景
- 主机详情 UI 在 `route/static/app/host.js` 中渲染，基础监控区域位于详情弹框内容里。
- 主机列表中的报告概览由前端根据 `panel_report`/`pve_report` 计算。
- 频率选择控件与开关组件已存在：`route/static/js/jquery-cron-selector.js` 与 `route/static/js/jquery-radio-switch.js`。
- 邮件通知配置存储在 `data/notify.json`，通过 `jh.getNotifyData(True)` 获取。

## 目标 / 非目标
- 目标：单主机维度的报告开关与频率配置；主机列表启用标识；按频率发送报告邮件。
- 非目标：新增通知渠道、重构报告内容格式、为每台主机单独配置收件人。

## 决策
- 决策：将每台主机的报告配置存储在 `data/` 下的 JSON 文件中（以 `host_id` 为键，字段包含 `enabled`、`cron`、`last_sent_at`）。
  - 理由：无需数据库迁移，改动范围小，符合已有文件配置模式。
- 决策：在 `task.py` 中实现按分钟轮询的调度器，根据每台主机的配置判断是否需要发送。
  - 理由：复用已有任务循环，避免为每台主机创建系统级 crontab。
- 决策：频率参数使用现有 cron 选择器数据结构（`type`、`where1`、`hour`、`minute`、`week`），并用轻量判断逻辑进行触发。
  - 理由：复用 UI 组件与参数格式，避免引入新配置格式。
- 决策：发送邮件时直接调用 `jh.notifyMessage`，并复用现有邮件通知配置（`data/notify.json`）作为发送与收件人来源。
  - 理由：保持与现有通知体系一致，减少重复配置。

## 风险 / 权衡
- 文件型配置需要注意并发写入，建议采用读-改-写与临时文件方式保证原子性。
- 轮询调度可能因任务循环阻塞产生漂移，需要用 `last_sent_at` 防重复发送。

## 迁移计划
- 首次访问时若不存在 `data/host_report_cycle.conf` 则创建空配置。
- 不涉及数据库迁移。

## 未决问题
- 无。
