
-------------------- 20241113 

-- sqlite更新view01_host视图
DROP VIEW IF EXISTS view01_host;

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