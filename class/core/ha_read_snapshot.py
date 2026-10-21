"""One readonly transaction, explicit public fields; never initializes HA schema."""
import datetime
import json
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


def public_checks(raw):
    """Expose known check fields only, never arbitrary collector/config payloads."""
    try:
        detail = json.loads(raw or '{}')
    except (ValueError, TypeError):
        return {'available': False, 'checks': [], 'components': {}}
    if not isinstance(detail, dict):
        return {'available': False, 'checks': [], 'components': {}}
    components = {}
    for name in ('cloud', 'lock', 'mysql', 'openresty', 'rsync', 'ssh'):
        value = detail.get(name)
        if isinstance(value, dict):
            components[name] = {key: value[key] for key in ('status', 'text')
                                if isinstance(value.get(key), (str, bool, int, float))}
    checks = []
    for field in ('checks', 'script_checks'):
        values = detail.get(field)
        if isinstance(values, list):
            for value in values:
                if isinstance(value, dict):
                    item = {key: value[key] for key in ('group', 'name', 'expected', 'actual', 'status')
                            if isinstance(value.get(key), (str, bool, int, float))}
                    if item and item not in checks:
                        checks.append(item)
    return {'available': bool(components or checks), 'components': components, 'checks': checks}


def relationships_snapshot(db_path, include_checks=False):
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
        check_details = {}
        if include_checks:
            check_details = {
                (row['pair_id'], row['host_id']): public_checks(row['health_detail'])
                for row in db.execute('''SELECT h.pair_id,h.host_id,h.health_detail
                    FROM ha_host_state h JOIN ha_pair p ON p.pair_id=h.pair_id
                    WHERE p.local_type='local' ''')
            }
        # localReportApi writes the host's task pointer and task status atomically.
        # Only that current task is authoritative; historical tasks may retain
        # pending/running after a newer task has already completed.
        busy = {row['pair_id'] for row in hosts if row['switch_task_status'] in ('pending', 'running')}
        by_pair = {}
        for row in hosts:
            item = dict(row)
            pair_id = item.pop('pair_id')
            if include_checks:
                item['self_check'] = check_details[(pair_id, item['host_id'])]
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
