-- 资源增长预测配置（废弃，用一个配置代替）
CREATE TABLE IF NOT EXISTS `host_resource_growth_alarm_config` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `scan_history_hours` INTEGER DEFAULT 5, -- 用于计算的历史数据小时数
  `prediction_percentage_critical` INTEGER DEFAULT 20, -- 紧急告警百分比阈值
  `prediction_percentage_warning` INTEGER DEFAULT 10, -- 高级告警百分比阈值
  `notify_critical_interval` INTEGER DEFAULT 3600, -- 紧急级别通知间隔（秒）
  `notify_warning_interval` INTEGER DEFAULT 7200, -- 警告级别通知间隔（秒）
  `is_enabled` INTEGER DEFAULT 1 -- 是否启用
);


