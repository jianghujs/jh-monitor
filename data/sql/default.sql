
CREATE TABLE IF NOT EXISTS `backup` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `type` INTEGER,
  `name` TEXT,
  `pid` INTEGER,
  `filename` TEXT,
  `size` INTEGER,
  `addtime` TEXT
);

CREATE TABLE IF NOT EXISTS `binding` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `pid` INTEGER,
  `domain` TEXT,
  `path` TEXT,
  `port` INTEGER,
  `addtime` TEXT
);


CREATE TABLE IF NOT EXISTS `crontab` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT,
  `type` TEXT,
  `where1` TEXT,
  `where_hour` INTEGER,
  `where_minute` INTEGER,
  `echo` TEXT,
  `addtime` TEXT,
  `status` INTEGER DEFAULT '1',
  `save` INTEGER DEFAULT '{}',
  `backup_to` TEXT DEFAULT 'off', 
  `sname` TEXT,
  `sbody` TEXT,
  'stype' TEXT,
  `urladdress` TEXT
);

CREATE TABLE IF NOT EXISTS `firewall` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `port` TEXT,
  `protocol` TEXT DEFAULT 'tcp',
  `ps` TEXT,
  `addtime` TEXT
);

INSERT INTO `firewall` (`id`, `port`, `ps`, `addtime`) VALUES
(1, '80', '网站默认端口', '0000-00-00 00:00:00'),
(2, '22', 'SSH远程管理服务', '0000-00-00 00:00:00'),
(3, '443', 'HTTPS', '0000-00-00 00:00:00'),
(4, '888', 'phpMyAdmin默认端口', '0000-00-00 00:00:00'),
(5, '10022', 'SSH 新端口', '0000-00-00 00:00:00'),
(6, '33067', 'MYSQL 新端口', '0000-00-00 00:00:00')
;



CREATE TABLE IF NOT EXISTS `logs` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `type` TEXT,
  `log` TEXT,
  `uid` TEXT,
  `addtime` TEXT
);
ALTER TABLE `logs` ADD COLUMN `uid` INTEGER DEFAULT '1';

CREATE TABLE IF NOT EXISTS `sites` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT,
  `path` TEXT,
  `status` TEXT,
  `index` TEXT,
  `type_id` INTEGER,
  `ps` TEXT,
  `edate` TEXT,
  `addtime` TEXT
);

CREATE TABLE IF NOT EXISTS `site_types` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT
);

CREATE TABLE IF NOT EXISTS `domain` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `pid` INTEGER,
  `name` TEXT,
  `port` INTEGER,
  `addtime` TEXT
);

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
(1, 'admin', '21232f297a57a5a743894a0e4a801fc3', '192.168.0.10', '2022-02-02 00:00:00', 0, 'midoks@163.com');


CREATE TABLE IF NOT EXISTS `tasks` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` 			TEXT,
  `type`			TEXT,
  `status` 		TEXT,
  `addtime` 	TEXT,
  `start` 	  INTEGER,
  `end` 	    INTEGER,
  `execstr` 	TEXT
);

CREATE TABLE IF NOT EXISTS `temp_login` (
  `id`  INTEGER PRIMARY KEY AUTOINCREMENT,
  `token` REAL,
  `salt`  REAL,
  `state` INTEGER,
  `login_time`  INTEGER,
  `login_addr`  REAL,
  `logout_time` INTEGER,
  `expire`  INTEGER,
  `addtime` INTEGER
);

CREATE TABLE IF NOT EXISTS `panel` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `title` TEXT,
  `url` TEXT,
  `username` TEXT,
  `password` TEXT,
  `click` INTEGER,
  `addtime` INTEGER
);




-------------------- 主机管理


-- 主机
CREATE TABLE IF NOT EXISTS `host` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` TEXT,
  `host_name` TEXT,
  `host_group_id` TEXT,
  `host_group_name` TEXT,
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
  `host_group_id` TEXT,
  `host_group_name` TEXT,
  `addtime` TEXT
);

-- 主机状态数据（启动状态、运行天数、CPU型号、资源占用（负载、CPU、内存、流量、磁盘）、网络IO、磁盘IO、备份、备份状态、温度（CPU、磁盘））
CREATE TABLE IF NOT EXISTS `host_detail` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` TEXT,
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
  `ssh_user_list` TEXT NOT NULL DEFAULT '{}',
  `last_update` TEXT, 
  `addtime` TEXT
);

-- 主机告警事件
CREATE TABLE IF NOT EXISTS `host_alarm` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` TEXT,
  `host_name` TEXT,
  `alarm_type` TEXT,
  `alarm_level` TEXT,
  `alarm_content` TEXT,
  `addtime` TEXT
);

-- 主机危险命令
CREATE TABLE IF NOT EXISTS `host_danger_cmd` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` TEXT,
  `host_name` TEXT,
  `cmd` TEXT,
  `addtime` TEXT
);

-- 主机日志
CREATE TABLE IF NOT EXISTS `host_log` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `host_id` TEXT,
  `host_name` TEXT,
  `log` TEXT,
  `addtime` TEXT
);


-- 视图

CREATE VIEW view01_host AS
SELECT h.*, hg.host_group_name,
hd.host_status, hd.host_info, hd.cpu_info, hd.mem_info, hd.disk_info, hd.net_info, hd.load_avg, hd.firewall_info, hd.port_info, hd.backup_info, hd.temperature_info, hd.ssh_user_list, hd.addtime AS detail_addtime, hd.last_update AS detail_last_update 
FROM host h 
LEFT JOIN (
    SELECT 
        hd.*
    FROM 
        host_detail hd
    INNER JOIN (
        SELECT 
            host_id, 
            MAX(id) AS max_id
        FROM 
            host_detail
        GROUP BY 
            host_id
    ) latest_hd ON hd.host_id = latest_hd.host_id AND hd.id = latest_hd.max_id
) hd ON hd.host_id = h.host_id
LEFT JOIN 
    host_group hg ON h.host_group_id = hg.host_group_id;