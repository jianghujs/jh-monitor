"""Public inventory fields in a readonly transaction; no collectors or migrations."""
import datetime
import sqlite3
from urllib.parse import quote


def hosts_snapshot(db_path):
    db = sqlite3.connect('file:' + quote(str(db_path)) + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')
        groups = {
            str(row['host_group_id']): row['host_group_name']
            for row in db.execute('SELECT host_group_id,host_group_name FROM host_group')
            if row['host_group_id'] is not None
        }
        rows = db.execute('''SELECT host_id,host_name,host_group_id,ip,os,
            is_jhpanel,is_pve,is_master,backup_host_id
            FROM host ORDER BY id''').fetchall()
        hosts = []
        for row in rows:
            item = dict(row)
            group_id = str(item['host_group_id'] or '')
            item['host_group_name'] = groups.get(group_id)
            item['group_resolved'] = group_id in groups
            for field in ('is_jhpanel', 'is_pve', 'is_master'):
                value = item[field]
                item[field] = None if value is None else str(value).lower() in ('1', 'true')
            hosts.append(item)
        return {
            'schema_version': 1,
            'snapshot_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'total': len(hosts),
            'list': hosts,
        }
    finally:
        db.rollback()
        db.close()
