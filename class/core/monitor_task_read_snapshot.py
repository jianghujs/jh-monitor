"""Task registration and stored analysis only; no refresh, execution or ES writes."""
import datetime
import sqlite3
from urllib.parse import quote

from ha_read_snapshot import iso_time


def monitor_tasks_snapshot(db_path):
    db = sqlite3.connect('file:' + quote(str(db_path)) + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')
        rows = db.execute('''SELECT task_id,task_name,host_id,host_name,
            enabled,install_status,check_interval,grace_seconds,
            last_status,last_msg,last_run_at,last_event_at,last_analyse_at,
            addtime,update_time FROM monitor_task ORDER BY id''').fetchall()
        tasks = []
        for row in rows:
            item = dict(row)
            value = item['enabled']
            item['enabled'] = None if value is None else str(value).lower() in ('1', 'true')
            for field in ('last_run_at', 'last_event_at', 'last_analyse_at', 'addtime', 'update_time'):
                item[field] = iso_time(item[field])
            tasks.append(item)
        return {
            'schema_version': 1,
            'snapshot_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
            'status_source': 'stored_analysis',
            'events_index_pattern': 'host-monitor-task-event*',
            'total': len(tasks),
            'list': tasks,
        }
    finally:
        db.rollback()
        db.close()
