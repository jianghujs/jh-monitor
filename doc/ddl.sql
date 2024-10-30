
-------------------- 面板内置数据表
CREATE TABLE IF NOT EXISTS `logs` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `type` TEXT,
  `log` TEXT,
  `uid` TEXT,
  `addtime` TEXT
);
ALTER TABLE `logs` ADD COLUMN `uid` INTEGER DEFAULT '1';

CREATE TABLE IF NOT EXISTS `users` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `username` TEXT,
  `password` TEXT,
  `login_ip` TEXT,
  `login_time` TEXT,
  `phone` TEXT,
  `email` TEXT
);

INSERT INTO `users` (`id`, `username`, `password`, `login_ip`, `login_time`, `phone`, `email`) VALUES
(1, 'admin', '21232f297a57a5a743894a0e4a801fc3', '192.168.0.10', '2022-02-02 00:00:00', 0, 'jianghujs@163.com');


CREATE TABLE IF NOT EXISTS `panel` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `title` TEXT,
  `url` TEXT,
  `username` TEXT,
  `password` TEXT,
  `click` INTEGER,
  `addtime` INTEGER
);
--------------------



-------------------- 主机管理

-- 主机
CREATE TABLE IF NOT EXISTS `host` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_name` TEXT,
  `host_group` TEXT,
  `ip` TEXT,
  `os` TEXT,
  `remark` TEXT,
  -- SSH
  `ssh_port` INTEGER,
  `ssh_user` TEXT,
  `ssh_pkey` TEXT,
  `is_jhpanel` BOOLEAN,
  `is_pve` BOOLEAN,
  -- 备用机
  `is_master` BOOLEAN,
  `backup_host_id` INTEGER,
  `backup_host_name` TEXT,
  `backup_ip` TEXT,
  `addtime` TEXT
);

-- 主机分组
CREATE TABLE IF NOT EXISTS `host_group` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT,
  `addtime` TEXT
);

-- 主机状态数据（启动状态、运行天数、CPU型号、资源占用（负载、CPU、内存、流量、磁盘）、网络IO、磁盘IO、备份、备份状态、温度（CPU、磁盘））
CREATE TABLE IF NOT EXISTS `host_detail` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` INTEGER,
  `host_name` TEXT,
  `host_status` TEXT,
  `uptime` TEXT,
  `host_info` TEXT NOT NULL DEFAULT '{}',
  `cpu_info` TEXT NOT NULL DEFAULT '{}',
  `mem_info` TEXT NOT NULL DEFAULT '{}',
  `disk_info` TEXT NOT NULL DEFAULT '[]',
  `net_info` TEXT NOT NULL DEFAULT '[]',
  `load_avg` TEXT NOT NULL DEFAULT '{}',
  `firewall_info` TEXT NOT NULL DEFAULT '{}',
  `port_info` TEXT NOT NULL DEFAULT '{}',
  `backup_info` TEXT NOT NULL DEFAULT '{}',
  `temperature_info` TEXT NOT NULL DEFAULT '{}',  
  `last_update` TEXT, 
  `addtime` TEXT
);

-- 主机告警事件
CREATE TABLE IF NOT EXISTS `host_alarm` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` INTEGER,
  `host_name` TEXT,
  `alarm_type` TEXT,
  `alarm_level` TEXT,
  `alarm_content` TEXT,
  `addtime` TEXT
);

-- 主机危险命令
CREATE TABLE IF NOT EXISTS `host_danger_cmd` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` INTEGER,
  `host_name` TEXT,
  `cmd` TEXT,
  `addtime` TEXT
);

-- 主机日志
CREATE TABLE IF NOT EXISTS `host_log` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` INTEGER,
  `host_name` TEXT,
  `log` TEXT,
  `addtime` TEXT
);


-------------------------------
-- 删除表

DROP TABLE IF EXISTS host;
DROP TABLE IF EXISTS host_group;
DROP TABLE IF EXISTS host_detail;
DROP TABLE IF EXISTS host_alarm;
DROP TABLE IF EXISTS host_danger_cmd;
DROP TABLE IF EXISTS host_log;

-------------------------------

-- 测试数据
INSERT INTO `host` (`host_name`, `host_group`, `ip`, `os`, `remark`, `ssh_port`, `ssh_user`, `ssh_pkey`, `is_jhpanel`, `is_pve`, `is_master`, `backup_host_id`, `backup_host_name`, `backup_ip`, `addtime`) VALUES
('host1', 'group1', '127.0.0.1', 'CentOS 7', 'remark', 22, 'root', '/', true, false, false, 0, '', '', '2022-02-02 00:00:00');

INSERT INTO `host_group` (`name`, `addtime`) VALUES
('group1', '2022-02-02 00:00:00');

INSERT INTO `host_detail` (`host_id`, `host_name`, `host_status`, `uptime`, `host_info`, `cpu_info`, `mem_info`, `disk_info`, `net_info`, `load_avg`, `firewall_info`, `port_info`, `backup_info`, `temperature_info`, `last_update`, `addtime`) VALUES
(1, 'host1', 'running', '1 day', '{}', '{}', '{}', '[]', '[]', '{}', '{}', '{}', '{}', '{}', 1727625601, 1727625601),
(1, 'host1', 'running', '1 day', '{}', '{}', '{}', '[]', '[]', '{}', '{}', '{}', '{}', '{}', 1727625601, 1727625601);

INSERT INTO `host_alarm` (`host_id`, `host_name`, `alarm_type`, `alarm_level`, `alarm_content`, `addtime`) VALUES
(1, 'host1', 'cpu', 'warning', 'CPU usage is too high', 1727625601);