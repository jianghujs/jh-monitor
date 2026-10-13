"""One readonly transaction, explicit public fields; never initializes HA schema."""
import datetime
import sqlite3
from urllib.parse import quote


def iso_time(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
        # Existing collector timestamps are server-local wall clock.
        return parsed.astimezone().isoformat()
    except (ValueError, OverflowError):
        return None


def relationships_snapshot(db_path):
    db = sqlite3.connect('file:' + quote(db_path) + '?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')
        pairs = db.execute("SELECT pair_id,pair_name,status,status_text FROM ha_pair WHERE local_type='local' ORDER BY id").fetchall()
        hosts = db.execute('''SELECT h.pair_id,h.host_id,h.host_name,h.role,h.online_status,
            h.health_status,h.collect_status,h.last_report_at,h.update_time AS received_at,
            t.status AS switch_task_status FROM ha_host_state h
            JOIN ha_pair p ON p.pair_id=h.pair_id AND p.local_type='local'
            LEFT JOIN ha_switch_task t ON t.switch_task_id=h.switch_task_id AND t.pair_id=h.pair_id
            ORDER BY h.id''').fetchall()
        # Pending tasks can precede the next host report, so also include these in the block decision.
        busy = {r[0] for r in db.execute("SELECT DISTINCT pair_id FROM ha_switch_task WHERE status IN ('pending','running')")}
        by_pair = {}
        for row in hosts:
            item = dict(row)
            pair_id = item.pop('pair_id')
            for field in ('last_report_at', 'received_at'):
                item[field] = iso_time(item[field])
            by_pair.setdefault(pair_id, []).append(item)
        result = []
        for row in pairs:
            item = dict(row)
            item['hosts'] = by_pair.get(item['pair_id'], [])
            if item['pair_id'] in busy:
                item['status'] = 'switching'
                item['status_text'] = 'Switch task pending or running'
            result.append(item)
        return {'schema_version': 1, 'snapshot_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'list': result}
    finally:
        db.rollback()
        db.close()
