
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


-------------------------------
-- 删除表

DROP TABLE IF EXISTS host;
DROP TABLE IF EXISTS host_group;
DROP TABLE IF EXISTS host_detail;
DROP TABLE IF EXISTS host_alarm;
DROP TABLE IF EXISTS host_danger_cmd;
DROP TABLE IF EXISTS host_log;

-------------------------------

-- 视图
CREATE VIEW view01_host AS
SELECT h.*, hg.host_group_name,
hd.host_info, hd.cpu_info, hd.mem_info, hd.disk_info, hd.net_info, hd.load_avg, hd.firewall_info, hd.port_info, hd.backup_info, hd.temperature_info, hd.last_update 
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
--------------------------------

-- 删除视图
DROP VIEW IF EXISTS view01_host;



-------------------------------
-- 测试数据
INSERT INTO `host` (host_id, host_name, host_group_id, host_group_name, ip, os, remark, ssh_port, ssh_user, ssh_pkey, is_jhpanel, is_pve, is_master, backup_host_id, backup_host_name, backup_ip, addtime) VALUES
('H00001', 'Host1', 'HG00001', 'Group1', '192.168.1.10', 'Linux', 'Primary database server', 22, 'root', '/path/to/key', 1, 0, 1, NULL, NULL, NULL, '2023-10-01 12:00:00'),
('H00002', 'Host2', 'HG00001', 'Group1', '192.168.1.11', 'Linux', 'Backup database server', 22, 'root', '/path/to/key', 0, 0, 0, 1, 'Host1', '192.168.1.10', '2023-10-02 12:00:00'),
('H00003', 'Host3', 'HG00002', 'Group2', '192.168.1.12', 'Linux', 'Web server', 22, 'admin', '/path/to/key', 0, 1, 1, NULL, NULL, NULL, '2023-10-04 12:00:00'),
('H00004', 'Host4', 'HG00002', 'Group2', '192.168.1.13', 'Windows', 'File server', 22, 'administrator', '/path/to/key', 0, 0, 0, 3, 'Host3', '192.168.1.12', '2023-10-05 12:00:00'),
('H00005', 'Host5', 'HG00003', 'Group3', '192.168.1.14', 'Linux', 'Application server', 22, 'root', '/path/to/key', 1, 0, 1, NULL, NULL, NULL, '2023-10-06 12:00:00');


INSERT INTO `host_group` (host_group_id, host_group_name, addtime) VALUES
('HG00001', 'Group1', '2023-10-01 12:00:00'),
('HG00002', 'Group2', '2023-10-02 12:00:00'),
('HG00003', 'Group3', '2023-10-06 12:00:00'),
('HG00004', 'Group4', '2023-10-07 12:00:00');


INSERT INTO `host_detail` (host_id, host_name, host_status, uptime, host_info, cpu_info, mem_info, disk_info, net_info, load_avg, firewall_info, port_info, backup_info, temperature_info, last_update, addtime) VALUES
('H00001', 'Host1', 'Running', '15 days', '{"hostName":"debian","kernelArch":"x86_64","kernelVersion":"5.10.0-23-amd64","os":"linux","platform":"debian","platformFamily":"debian","platformVersion":"11.6","procs":97,"upTime":14472}', '{"logicalCores":2,"modelName":"Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz","percent":4.15}', '{"total":4109926400,"free":3076767744,"used":467066880,"usedPercent":11.36,"buffers":65052672,"cached":501039104,"swapFree":1022357504,"swapTotal":1022357504,"swapUsed":0,"swapUsedPercent":0}', '[{"total":19947929600,"free":15416078336,"used":3492610048,"usedPercent":18.47,"fstype":"ext4","ioPercent":0,"ioTime":139824,"iops":0,"mountpoint":"/","name":"/dev/sda1"}]', '[{"name":"enp0s3","recv":145488948,"recv_per_second":1612,"sent":32678885,"sent_per_second":90}]', '{"1min":0.15,"5min":0.10,"15min":0.05}', '{"is_running":true,"rules":[{"access":"ACCEPT","protocol":"tcp","release_port":"22","source":"anywhere"},{"access":"ACCEPT","protocol":"tcp","release_port":"806","source":"anywhere"}],"rule_change":{"add":null,"del":null}}', '{"2129988847542649187":{"ip":"0.0.0.0","port":22,"protocol":"tcp","pne_id":-7672102068318330115},"6588906985071447406":{"ip":"127.0.0.1","port":37177,"protocol":"tcp","pne_id":-4512644645752656383},"6677558488157980451":{"ip":"::","port":806,"protocol":"tcp","pne_id":-7910089643010597800},"344772759478166149":{"ip":"::","port":22,"protocol":"tcp","pne_id":-7672102068318330115}}', '{}', '{}', '2023-10-03 12:00:00', '2023-10-01 12:00:00'),
('H00002', 'Host2', 'Running', '20 days', '{"hostName":"debian","kernelArch":"x86_64","kernelVersion":"5.10.0-23-amd64","os":"linux","platform":"debian","platformFamily":"debian","platformVersion":"11.6","procs":97,"upTime":14472}', '{"logicalCores":2,"modelName":"Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz","percent":4.15}', '{"total":4109926400,"free":3076767744,"used":467066880,"usedPercent":11.36,"buffers":65052672,"cached":501039104,"swapFree":1022357504,"swapTotal":1022357504,"swapUsed":0,"swapUsedPercent":0}', '[{"total":19947929600,"free":15416078336,"used":3492610048,"usedPercent":18.47,"fstype":"ext4","ioPercent":0,"ioTime":139824,"iops":0,"mountpoint":"/","name":"/dev/sda1"}]', '[{"name":"enp0s3","recv":145488948,"recv_per_second":1612,"sent":32678885,"sent_per_second":90}]', '{"1min":0.15,"5min":0.10,"15min":0.05}', '{"is_running":true,"rules":[{"access":"ACCEPT","protocol":"tcp","release_port":"22","source":"anywhere"},{"access":"ACCEPT","protocol":"tcp","release_port":"806","source":"anywhere"}],"rule_change":{"add":null,"del":null}}', '{"2129988847542649187":{"ip":"0.0.0.0","port":22,"protocol":"tcp","pne_id":-7672102068318330115},"6588906985071447406":{"ip":"127.0.0.1","port":37177,"protocol":"tcp","pne_id":-4512644645752656383},"6677558488157980451":{"ip":"::","port":806,"protocol":"tcp","pne_id":-7910089643010597800},"344772759478166149":{"ip":"::","port":22,"protocol":"tcp","pne_id":-7672102068318330115}}', '{}', '{}', '2023-10-03 12:00:00', '2023-10-01 12:00:00'),
('H00003', 'Host3', 'Stopped', '5 days', '{"hostName":"debian","kernelArch":"x86_64","kernelVersion":"5.10.0-23-amd64","os":"linux","platform":"debian","platformFamily":"debian","platformVersion":"11.6","procs":97,"upTime":14472}', '{"logicalCores":2,"modelName":"Intel(R) Core(TM) i7-8700 CPU @ 3.20GHz","percent":4.15}', '{"total":4109926400,"free":3076767744,"used":467066880,"usedPercent":11.36,"buffers":65052672,"cached":501039104,"swapFree":1022357504,"swapTotal":1022357504,"swapUsed":0,"swapUsedPercent":0}', '[{"total":19947929600,"free":15416078336,"used":3492610048,"usedPercent":18.47,"fstype":"ext4","ioPercent":0,"ioTime":139824,"iops":0,"mountpoint":"/","name":"/dev/sda1"}]', '[{"name":"enp0s3","recv":145488948,"recv_per_second":1612,"sent":32678885,"sent_per_second":90}]', '{"1min":0.15,"5min":0.10,"15min":0.05}', '{"is_running":true,"rules":[{"access":"ACCEPT","protocol":"tcp","release_port":"22","source":"anywhere"},{"access":"ACCEPT","protocol":"tcp","release_port":"806","source":"anywhere"}],"rule_change":{"add":null,"del":null}}', '{"2129988847542649187":{"ip":"0.0.0.0","port":22,"protocol":"tcp","pne_id":-7672102068318330115},"6588906985071447406":{"ip":"127.0.0.1","port":37177,"protocol":"tcp","pne_id":-4512644645752656383},"6677558488157980451":{"ip":"::","port":806,"protocol":"tcp","pne_id":-7910089643010597800},"344772759478166149":{"ip":"::","port":22,"protocol":"tcp","pne_id":-7672102068318330115}}', '{}', '{}', '2023-10-03 12:00:00', '2023-10-01 12:00:00');

INSERT INTO `host_alarm` (host_id, host_name, alarm_type, alarm_level, alarm_content, addtime) VALUES
('H00001', 'Host1', 'CPU Usage', 'High', 'CPU usage exceeded 90%', '2023-10-03 14:00:00'),
('H00001', 'Host1', 'Disk Space', 'Medium', 'Disk space usage exceeded 80%', '2023-10-03 15:00:00'),
('H00002', 'Host2', 'Memory Usage', 'Critical', 'Memory usage exceeded 95%', '2023-10-04 15:00:00'),
('H00003', 'Host3', 'Network Latency', 'Low', 'Network latency exceeded 200ms', '2023-10-05 16:00:00'),
('H00001', 'Host1', 'Temperature', 'High', 'CPU temperature exceeded 70°C', '2023-10-03 17:00:00');

INSERT INTO `host_danger_cmd` (host_id, host_name, cmd, addtime) VALUES
('H00001', 'Host1', 'rm -rf /', '2023-10-03 16:00:00'),
('H00002', 'Host2', 'shutdown now', '2023-10-03 17:00:00'),
('H00003', 'Host3', 'mkfs.ext4 /dev/sda1', '2023-10-05 18:00:00'),
('H00001', 'Host1', 'dd if=/dev/zero of=/dev/sda bs=1M count=100', '2023-10-05 19:00:00'),
('H00002', 'Host2', 'reboot', '2023-10-06 20:00:00');


INSERT INTO `host_log` (host_id, host_name, log, addtime) VALUES
('H00001', 'Host1', 'Host rebooted', '2023-10-03 18:00:00'),
('H00002', 'Host2', 'Backup completed successfully', '2023-10-03 19:00:00'),
('H00003', 'Host3', 'Scheduled maintenance completed', '2023-10-05 21:00:00'),
('H00001', 'Host1', 'Security patch applied', '2023-10-06 22:00:00'),
('H00002', 'Host2', 'System backup initiated', '2023-10-07 23:00:00');

