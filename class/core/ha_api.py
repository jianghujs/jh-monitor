# coding: utf-8

import fcntl
import json
import os
import re
import sqlite3
import tempfile
import time
import uuid

from flask import request

import jh


class ha_api:
    """Cloud reporting API for the local-only HA manager plugin."""

    LOG_ROOT = '/www/server/jh-monitor/logs/ha_switch'
    DB_PATH = '/www/server/jh-monitor/data/default.db'
    PAIR_TYPE = 'local'
    PAIR_FIELDS = 'id,pair_id,pair_name,status,status_text,last_report_at,local_type,sort_id,addtime,update_time'
    HOST_FIELDS = (
        'id,pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,'
        'collect_method,health_detail,switch_task_id,last_report_at,registered_at,addtime,update_time'
    )
    TASK_FIELDS = (
        'id,switch_task_id,pair_id,host_id,target_role,status,status_text,current_step,next_step,'
        'step_summary,log_path,started_at,finished_at,last_report_at,addtime,update_time'
    )
    ID_RE = re.compile(r'^[A-Za-z0-9_-]{1,128}$')
    ROLE_VALUES = ('master', 'standby')
    ONLINE_VALUES = ('online', 'offline')
    HEALTH_VALUES = ('normal', 'warning', 'danger')
    COLLECT_VALUES = ('success', 'failed', 'unknown')
    TASK_VALUES = ('pending', 'running', 'success', 'failed', 'recovered')

    def _now(self):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def _jsonLoads(self, value, default=None):
        if default is None:
            default = {}
        if isinstance(value, (dict, list)):
            return value
        try:
            result = json.loads(value or '')
            return result
        except Exception:
            return default

    def _bodyJson(self):
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
        raw = request.form.get('data', '')
        if raw:
            parsed = self._jsonLoads(raw, {})
            if isinstance(parsed, dict):
                return parsed
        return {key: request.form.get(key) for key in request.form.keys()}

    def _safeText(self, value, max_len=255):
        return str(value or '').replace('\x00', '').strip()[:max_len]

    def _safeInt(self, value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    def _validId(self, value):
        return bool(self.ID_RE.match(self._safeText(value, 128)))

    def _generatePairId(self):
        while True:
            pair_id = 'HA{0}'.format(uuid.uuid4().hex.upper())
            existing = jh.M('ha_pair').where('pair_id=?', (pair_id,)).field('id').find()
            if not (isinstance(existing, dict) and existing.get('id')):
                return pair_id

    def _ensureLogRoot(self):
        os.makedirs(self.LOG_ROOT, mode=0o700, exist_ok=True)
        try:
            os.chmod(self.LOG_ROOT, 0o700)
        except Exception:
            pass

    def _taskPaths(self, switch_task_id):
        task_id = self._safeText(switch_task_id, 128)
        if not self._validId(task_id):
            raise ValueError('switch_task_id无效')
        self._ensureLogRoot()
        base = os.path.realpath(self.LOG_ROOT)
        result = {
            'log_path': os.path.join(base, 'TASK_{0}.log'.format(task_id)),
            'index_path': os.path.join(base, 'TASK_{0}.seq.json'.format(task_id)),
            'lock_path': os.path.join(base, 'TASK_{0}.lock'.format(task_id)),
        }
        for path in result.values():
            if os.path.commonpath([base, os.path.realpath(os.path.dirname(path))]) != base:
                raise ValueError('任务日志路径无效')
        return result

    def ensureHaSchema(self):
        self._ensureLogRoot()
        db = jh.M('ha_pair')
        statements = [
            """CREATE TABLE IF NOT EXISTS ha_pair (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_id TEXT, pair_name TEXT, status TEXT DEFAULT 'unknown', status_text TEXT,
                last_report_at TEXT, local_type TEXT, sort_id INTEGER DEFAULT 0, addtime TEXT, update_time TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS ha_host_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pair_id TEXT, host_id TEXT, host_name TEXT, host_ip TEXT, role TEXT,
                online_status TEXT DEFAULT 'offline', health_status TEXT DEFAULT 'normal',
                collect_status TEXT DEFAULT 'unknown', collect_method TEXT, health_detail TEXT,
                switch_task_id TEXT, last_report_at TEXT, registered_at TEXT, addtime TEXT, update_time TEXT
            )""",
            """CREATE TABLE IF NOT EXISTS ha_switch_task (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                switch_task_id TEXT, pair_id TEXT, host_id TEXT, target_role TEXT, status TEXT,
                status_text TEXT, current_step TEXT, next_step TEXT, step_summary TEXT, log_path TEXT,
                started_at TEXT, finished_at TEXT, last_report_at TEXT, addtime TEXT, update_time TEXT
            )""",
        ]
        for statement in statements:
            if isinstance(db.originExecute(statement), str):
                return False
        columns = {
            'ha_pair': {
                'pair_name': 'TEXT', 'status': "TEXT DEFAULT 'unknown'", 'status_text': 'TEXT',
                'last_report_at': 'TEXT', 'local_type': 'TEXT', 'sort_id': 'INTEGER DEFAULT 0',
                'addtime': 'TEXT', 'update_time': 'TEXT',
            },
            'ha_host_state': {
                'host_name': 'TEXT', 'host_ip': 'TEXT', 'role': 'TEXT', 'online_status': 'TEXT',
                'health_status': 'TEXT', 'collect_status': 'TEXT', 'collect_method': 'TEXT',
                'health_detail': 'TEXT', 'switch_task_id': 'TEXT', 'last_report_at': 'TEXT',
                'registered_at': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT',
            },
            'ha_switch_task': {
                'switch_task_id': 'TEXT', 'pair_id': 'TEXT', 'host_id': 'TEXT', 'target_role': 'TEXT',
                'status': 'TEXT', 'status_text': 'TEXT', 'current_step': 'TEXT', 'next_step': 'TEXT',
                'step_summary': 'TEXT', 'log_path': 'TEXT', 'started_at': 'TEXT', 'finished_at': 'TEXT',
                'last_report_at': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT',
            },
        }
        for table, fields in columns.items():
            info = db.originExecute('PRAGMA table_info({0})'.format(table))
            if isinstance(info, str):
                return False
            existing = {row[1] for row in info.fetchall()}
            for field, definition in fields.items():
                if field not in existing:
                    result = db.originExecute('ALTER TABLE {0} ADD COLUMN {1} {2}'.format(table, field, definition))
                    if isinstance(result, str):
                        return False
        for statement in (
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_pair_pair_id ON ha_pair(pair_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_host_pair_host ON ha_host_state(pair_id,host_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_switch_task_id ON ha_switch_task(switch_task_id)',
            'CREATE INDEX IF NOT EXISTS idx_ha_switch_task_pair_host ON ha_switch_task(pair_id,host_id)',
        ):
            result = db.originExecute(statement)
            if isinstance(result, str):
                return False
        max_sort_row = db.originExecute(
            'SELECT COALESCE(MAX(sort_id), 0) FROM ha_pair WHERE local_type=?', (self.PAIR_TYPE,)
        ).fetchone()
        next_sort = int(max_sort_row[0] or 0) if max_sort_row else 0
        sort_rows = db.originExecute(
            'SELECT id FROM ha_pair WHERE local_type=? AND (sort_id IS NULL OR sort_id <= 0) ORDER BY id DESC',
            (self.PAIR_TYPE,)
        ).fetchall()
        for row in sort_rows:
            next_sort += 1
            db.execute('UPDATE ha_pair SET sort_id=? WHERE id=?', (next_sort, row[0]))
        return True

    def _getPair(self, pair_id):
        self.ensureHaSchema()
        row = jh.M('ha_pair').where('pair_id=? AND local_type=?', (pair_id, self.PAIR_TYPE)).field(self.PAIR_FIELDS).find()
        return row if isinstance(row, dict) else {}

    def _getHost(self, pair_id, host_id):
        row = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).field(self.HOST_FIELDS).find()
        return row if isinstance(row, dict) else {}

    def _getTask(self, task_id):
        row = jh.M('ha_switch_task').where('switch_task_id=?', (task_id,)).field(self.TASK_FIELDS).find()
        return row if isinstance(row, dict) else {}

    def _getHosts(self, pair_id):
        rows = jh.M('ha_host_state').where('pair_id=?', (pair_id,)).field(self.HOST_FIELDS).order('update_time desc,id desc').select()
        return rows if isinstance(rows, list) else []

    def _getTasks(self, pair_id):
        rows = jh.M('ha_switch_task').where('pair_id=?', (pair_id,)).field(self.TASK_FIELDS).order('update_time desc,id desc').select()
        return rows if isinstance(rows, list) else []

    def _validateEnum(self, payload, key, values, required=True, default=''):
        value = self._safeText(payload.get(key), 32).lower()
        if not value and not required:
            return default, ''
        if value not in values:
            return '', '{0}无效'.format(key)
        return value, ''

    def _getReportedPair(self, payload):
        pair_id = self._safeText(payload.get('pair_id'), 128)
        if not self._validId(pair_id):
            return {}, 'pair_id不能为空或格式无效'
        pair = self._getPair(pair_id)
        if not pair:
            return {}, '主备关系不存在'
        return pair, ''

    def _validateHostPayload(self, payload, require_identity=True):
        host_id = self._safeText(payload.get('host_id'), 128)
        if require_identity and not self._validId(host_id):
            return {}, 'host_id无效'
        role, error = self._validateEnum(payload, 'role', self.ROLE_VALUES)
        if error:
            return {}, error
        online_status, error = self._validateEnum(payload, 'online_status', self.ONLINE_VALUES)
        if error:
            return {}, error
        health_status, error = self._validateEnum(payload, 'health_status', self.HEALTH_VALUES)
        if error:
            return {}, error
        collect_status, error = self._validateEnum(payload, 'collect_status', self.COLLECT_VALUES)
        if error:
            return {}, error
        health_detail = payload.get('health_detail') or {}
        if not isinstance(health_detail, (dict, list)):
            return {}, 'health_detail无效'
        return {
            'host_id': host_id,
            'host_name': self._safeText(payload.get('host_name') or host_id, 128),
            'host_ip': self._safeText(payload.get('host_ip'), 64),
            'role': role,
            'online_status': online_status,
            'health_status': health_status,
            'collect_status': collect_status,
            'collect_method': self._safeText(payload.get('collect_method') or 'local', 32),
            'health_detail': health_detail,
            'reported_at': self._safeText(payload.get('reported_at'), 32) or self._now(),
        }, ''

    def _validateTaskPayload(self, raw_task):
        if raw_task is None:
            return {}, ''
        if not isinstance(raw_task, dict):
            return {}, 'switch_task无效'
        task_id = self._safeText(raw_task.get('switch_task_id'), 128)
        if not self._validId(task_id):
            return {}, 'switch_task_id无效'
        target_role, error = self._validateEnum(raw_task, 'target_role', self.ROLE_VALUES)
        if error:
            return {}, error
        status, error = self._validateEnum(raw_task, 'status', self.TASK_VALUES)
        if error:
            return {}, error
        summary = raw_task.get('step_summary') or []
        if not isinstance(summary, (dict, list)):
            return {}, 'step_summary无效'
        return {
            'switch_task_id': task_id,
            'target_role': target_role,
            'status': status,
            'status_text': self._safeText(raw_task.get('status_text'), 512),
            'current_step': self._safeText(raw_task.get('current_step'), 255),
            'next_step': self._safeText(raw_task.get('next_step'), 255),
            'step_summary': summary,
            'started_at': self._safeText(raw_task.get('started_at'), 32),
            'finished_at': self._safeText(raw_task.get('finished_at'), 32),
        }, ''

    def _upsertHost(self, pair_id, host, now, registered=False, task_id=''):
        old = self._getHost(pair_id, host['host_id'])
        fields = (
            host['host_name'], host['host_ip'], host['role'], host['online_status'], host['health_status'],
            host['collect_status'], host['collect_method'], json.dumps(host['health_detail'], ensure_ascii=False),
            task_id if task_id else old.get('switch_task_id', ''), host['reported_at'],
            now if registered else old.get('registered_at', '') or now, now,
        )
        if old:
            jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host['host_id'])).save(
                'host_name,host_ip,role,online_status,health_status,collect_status,collect_method,health_detail,switch_task_id,last_report_at,registered_at,update_time', fields
            )
        else:
            jh.M('ha_host_state').add(
                'pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,collect_method,health_detail,switch_task_id,last_report_at,registered_at,addtime,update_time',
                (pair_id, host['host_id']) + fields[:-1] + (now, fields[-1])
            )

    def _upsertTask(self, pair_id, host_id, task, now):
        old = self._getTask(task['switch_task_id'])
        if old and (old.get('pair_id') != pair_id or old.get('host_id') != host_id):
            return {}, '切换任务不属于当前归属或机器'
        paths = self._taskPaths(task['switch_task_id'])
        values = (
            task['target_role'], task['status'], task['status_text'], task['current_step'], task['next_step'],
            json.dumps(task['step_summary'], ensure_ascii=False), paths['log_path'], task['started_at'], task['finished_at'], now, now,
        )
        if old:
            jh.M('ha_switch_task').where('switch_task_id=?', (task['switch_task_id'],)).save(
                'target_role,status,status_text,current_step,next_step,step_summary,log_path,started_at,finished_at,last_report_at,update_time', values
            )
        else:
            jh.M('ha_switch_task').add(
                'switch_task_id,pair_id,host_id,target_role,status,status_text,current_step,next_step,step_summary,log_path,started_at,finished_at,last_report_at,addtime,update_time',
                (task['switch_task_id'], pair_id, host_id) + values[:-1] + (now, values[-1])
            )
        return self._getTask(task['switch_task_id']), ''

    def _upsertReportSnapshot(self, pair_id, host, task, now):
        """Keep the reported host snapshot and optional task summary consistent."""
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute('BEGIN IMMEDIATE')
            task_id = task.get('switch_task_id') if task else ''
            if task:
                task_row = conn.execute(
                    'SELECT pair_id,host_id FROM ha_switch_task WHERE switch_task_id=?', (task_id,)
                ).fetchone()
                if task_row and (task_row[0] != pair_id or task_row[1] != host['host_id']):
                    raise ValueError('切换任务不属于当前归属或机器')
                log_path = self._taskPaths(task_id)['log_path']
                task_values = (
                    task['target_role'], task['status'], task['status_text'], task['current_step'], task['next_step'],
                    json.dumps(task['step_summary'], ensure_ascii=False), log_path, task['started_at'], task['finished_at'], now, now,
                )
                if task_row:
                    conn.execute(
                        'UPDATE ha_switch_task SET target_role=?,status=?,status_text=?,current_step=?,next_step=?,step_summary=?,log_path=?,started_at=?,finished_at=?,last_report_at=?,update_time=? WHERE switch_task_id=?',
                        task_values + (task_id,)
                    )
                else:
                    conn.execute(
                        'INSERT INTO ha_switch_task (switch_task_id,pair_id,host_id,target_role,status,status_text,current_step,next_step,step_summary,log_path,started_at,finished_at,last_report_at,addtime,update_time) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (task_id, pair_id, host['host_id']) + task_values[:-1] + (now, task_values[-1])
                    )
            host_row = conn.execute(
                'SELECT switch_task_id,registered_at FROM ha_host_state WHERE pair_id=? AND host_id=?',
                (pair_id, host['host_id'])
            ).fetchone()
            if not host_row:
                raise ValueError('当前机器尚未注册')
            current_task_id = task_id or host_row[0] or ''
            registered_at = host_row[1] or now
            conn.execute(
                'UPDATE ha_host_state SET host_name=?,host_ip=?,role=?,online_status=?,health_status=?,collect_status=?,collect_method=?,health_detail=?,switch_task_id=?,last_report_at=?,registered_at=?,update_time=? WHERE pair_id=? AND host_id=?',
                (
                    host['host_name'], host['host_ip'], host['role'], host['online_status'], host['health_status'],
                    host['collect_status'], host['collect_method'], json.dumps(host['health_detail'], ensure_ascii=False),
                    current_task_id, host['reported_at'], registered_at, now, pair_id, host['host_id']
                )
            )
        return task_id

    def _derivePairStatus(self, pair_id):
        hosts = self._getHosts(pair_id)
        if not hosts:
            return 'unknown', '等待当前机器上报'
        host = hosts[0]
        task = self._getTask(host.get('switch_task_id')) if host.get('switch_task_id') else {}
        name = host.get('host_name') or host.get('host_id') or '当前机器'
        if task and task.get('status') in ('pending', 'running'):
            return 'switching', '{0}：{1}'.format(name, task.get('current_step') or task.get('status_text') or '正在切换')
        if task and task.get('status') == 'failed':
            return 'danger', task.get('status_text') or '{0} 最近切换失败'.format(name)
        if host.get('online_status') == 'offline':
            return 'danger', '{0} 已离线'.format(name)
        if host.get('health_status') == 'danger':
            return 'danger', self._healthText(host, '{0} 自检异常'.format(name))
        if host.get('health_status') == 'warning':
            return 'warning', self._healthText(host, '{0} 自检提醒'.format(name))
        role = host.get('role')
        if role == 'master':
            return 'normal', '{0} 当前为主机，状态正常'.format(name)
        if role == 'standby':
            return 'normal', '{0} 当前为备机，状态正常'.format(name)
        return 'unknown', '等待当前机器上报'

    def _healthText(self, host, fallback):
        detail = self._jsonLoads(host.get('health_detail'), {})
        if isinstance(detail, dict):
            text = self._safeText(detail.get('summary') or detail.get('health_text'), 512)
            if text:
                return text
        return fallback

    def _refreshPair(self, pair_id, now=None):
        now = now or self._now()
        status, status_text = self._derivePairStatus(pair_id)
        latest = self._getHosts(pair_id)
        last_report_at = latest[0].get('last_report_at') if latest else ''
        jh.M('ha_pair').where('pair_id=? AND local_type=?', (pair_id, self.PAIR_TYPE)).save(
            'status,status_text,last_report_at,update_time', (status, status_text, last_report_at, now)
        )
        return self._getPair(pair_id)

    def _normalizeHost(self, host):
        result = dict(host)
        result['health_detail'] = self._jsonLoads(result.get('health_detail'), {})
        return result

    def _normalizeTask(self, task):
        result = dict(task)
        result['step_summary'] = self._jsonLoads(result.get('step_summary'), [])
        return result

    def _normalizePair(self, pair, include_tasks=False):
        result = dict(pair)
        hosts = self._getHosts(pair.get('pair_id'))
        result['host'] = self._normalizeHost(hosts[0]) if hosts else None
        if include_tasks:
            result['tasks'] = [self._normalizeTask(task) for task in self._getTasks(pair.get('pair_id'))]
        return result

    def _readSeqIndex(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as fp:
                payload = json.load(fp)
            values = payload.get('received') if isinstance(payload, dict) else []
            return {int(item) for item in values if int(item) > 0}
        except Exception:
            return set()

    def _writeSeqIndex(self, path, values):
        directory = os.path.dirname(path)
        fd, tmp_path = tempfile.mkstemp(prefix='.seq-', suffix='.tmp', dir=directory)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as fp:
                json.dump({'received': sorted(values)}, fp, ensure_ascii=False, separators=(',', ':'))
                fp.flush()
                os.fsync(fp.fileno())
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, path)
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def _validateLogs(self, logs, task_id):
        if logs is None:
            return [], ''
        if not isinstance(logs, list):
            return [], 'logs无效'
        result = []
        for item in logs:
            if not isinstance(item, dict):
                return [], '日志项无效'
            seq = self._safeInt(item.get('seq'), 0)
            if seq <= 0:
                return [], '日志seq必须为正整数'
            item_task_id = self._safeText(item.get('switch_task_id') or task_id, 128)
            if item_task_id != task_id:
                return [], '日志任务与状态任务不一致'
            result.append({
                'seq': seq,
                'timestamp': self._safeText(item.get('timestamp'), 32) or self._now(),
                'level': self._safeText(item.get('level') or 'info', 32),
                'stage': self._safeText(item.get('stage'), 128),
                'step': self._safeText(item.get('step'), 255),
                'message': self._safeText(item.get('message'), 4000),
            })
        return result, ''

    def _appendTaskLogs(self, task_id, logs):
        if not logs:
            return 0
        paths = self._taskPaths(task_id)
        with open(paths['lock_path'], 'a+', encoding='utf-8') as lock_file:
            os.chmod(paths['lock_path'], 0o600)
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                received = self._readSeqIndex(paths['index_path'])
                pending = {item['seq']: item for item in logs if item['seq'] not in received}
                if not pending:
                    return 0
                with open(paths['log_path'], 'a', encoding='utf-8') as fp:
                    os.chmod(paths['log_path'], 0o600)
                    for seq in sorted(pending):
                        item = pending[seq]
                        fp.write('[{0}] [seq:{1}] [{2}] [{3}] [{4}] {5}\n'.format(
                            item['timestamp'], item['seq'], item['level'], item['stage'] or 'switch',
                            item['step'] or '-', item['message']
                        ))
                    fp.flush()
                    os.fsync(fp.fileno())
                received.update(pending.keys())
                self._writeSeqIndex(paths['index_path'], received)
                return len(pending)
            finally:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _removeTaskFiles(self, task_ids):
        for task_id in task_ids:
            try:
                paths = self._taskPaths(task_id)
            except ValueError:
                continue
            for path in paths.values():
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except Exception:
                    pass

    def pairCreateApi(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        pair_name = self._safeText(payload.get('pair_name'), 128)
        if not pair_name:
            return jh.returnJson(False, '主备关系名称不能为空')
        pair_id = self._safeText(payload.get('pair_id'), 128)
        if pair_id:
            if not self._validId(pair_id):
                return jh.returnJson(False, '主备关系 ID 仅支持字母、数字、下划线和连字符，长度不超过128位')
            if jh.M('ha_pair').where('pair_id=?', (pair_id,)).count():
                return jh.returnJson(False, '主备关系 ID 已存在')
        else:
            pair_id = self._generatePairId()
        now = self._now()
        sort_row = jh.M('ha_pair').originExecute(
            'SELECT COALESCE(MAX(sort_id), 0) FROM ha_pair WHERE local_type=?', (self.PAIR_TYPE,)
        ).fetchone()
        sort_id = (int(sort_row[0] or 0) if sort_row else 0) + 1
        result = jh.M('ha_pair').add(
            'pair_id,pair_name,status,status_text,last_report_at,local_type,sort_id,addtime,update_time',
            (pair_id, pair_name, 'unknown', '等待当前机器上报', '', self.PAIR_TYPE, sort_id, now, now)
        )
        if isinstance(result, str):
            return jh.returnJson(False, '添加主备关系失败')
        return jh.returnJson(True, '主备关系已添加', {'pair_id': pair_id, 'pair_name': pair_name})

    def pairDeleteApi(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        pair_id = self._safeText(payload.get('pair_id'), 128)
        if not self._validId(pair_id):
            return jh.returnJson(False, 'pair_id不能为空或格式无效')
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        tasks = self._getTasks(pair_id)
        task_ids = [item.get('switch_task_id') for item in tasks if item.get('switch_task_id')]
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('DELETE FROM ha_switch_task WHERE pair_id=?', (pair_id,))
            conn.execute('DELETE FROM ha_host_state WHERE pair_id=?', (pair_id,))
            conn.execute('DELETE FROM ha_pair WHERE pair_id=? AND local_type=?', (pair_id, self.PAIR_TYPE))
        self._removeTaskFiles(task_ids)
        return jh.returnJson(True, '主备关系已删除', {'pair_id': pair_id})

    def pairSortApi(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        raw_json = request.get_json(silent=True)
        if isinstance(raw_json, list):
            row_ids = raw_json
        else:
            row_ids = request.form.getlist('pair_ids[]') or request.form.getlist('pair_ids')
            row_ids = row_ids or payload.get('pair_ids') or payload.get('row_ids') or []
        if isinstance(row_ids, str):
            row_ids = row_ids.split(',')
        if not isinstance(row_ids, list):
            return jh.returnJson(False, '主备关系排序数据无效')

        pair_ids = []
        for row_id in row_ids:
            pair_id = self._safeText(row_id, 128)
            if not self._validId(pair_id):
                return jh.returnJson(False, '主备关系 ID 无效')
            if pair_id not in pair_ids:
                pair_ids.append(pair_id)
        if not pair_ids:
            return jh.returnJson(False, '请先选择有效的主备关系排序数据')

        rows = jh.M('ha_pair').where('local_type=?', (self.PAIR_TYPE,)).field('id,pair_id').order('sort_id asc,id desc').select()
        rows = rows if isinstance(rows, list) else []
        existing_ids = [item.get('pair_id') for item in rows if isinstance(item, dict) and item.get('pair_id')]
        existing_id_set = set(existing_ids)
        if any(pair_id not in existing_id_set for pair_id in pair_ids):
            return jh.returnJson(False, '主备关系不存在或不属于本地版')

        ordered_ids = pair_ids + [pair_id for pair_id in existing_ids if pair_id not in pair_ids]
        with sqlite3.connect(self.DB_PATH) as conn:
            conn.execute('BEGIN IMMEDIATE')
            for sort_value, pair_id in enumerate(ordered_ids, 1):
                conn.execute(
                    'UPDATE ha_pair SET sort_id=? WHERE pair_id=? AND local_type=?',
                    (sort_value, pair_id, self.PAIR_TYPE)
                )
        return jh.returnJson(True, '主备关系排序已保存')

    def localRegisterApi(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        pair, error = self._getReportedPair(payload)
        if error:
            return jh.returnJson(False, error)
        host, error = self._validateHostPayload(payload)
        if error:
            return jh.returnJson(False, error)
        now = self._now()
        self._upsertHost(pair['pair_id'], host, now, registered=True)
        refreshed = self._refreshPair(pair['pair_id'], now)
        return jh.returnJson(True, '当前机器已注册', {'pair': self._normalizePair(refreshed), 'registered_at': now})

    def localReportApi(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        pair, error = self._getReportedPair(payload)
        if error:
            return jh.returnJson(False, error)
        host, error = self._validateHostPayload(payload)
        if error:
            return jh.returnJson(False, error)
        if not self._getHost(pair['pair_id'], host['host_id']):
            return jh.returnJson(False, '当前机器尚未注册')
        task, error = self._validateTaskPayload(payload.get('switch_task'))
        if error:
            return jh.returnJson(False, error)
        logs = payload.get('logs')
        task_id = task.get('switch_task_id') if task else self._safeText(payload.get('switch_task_id'), 128)
        if logs is not None and not task_id:
            return jh.returnJson(False, '日志必须关联切换任务')
        if task_id:
            existing_task = self._getTask(task_id)
            if existing_task and (existing_task.get('pair_id') != pair['pair_id'] or existing_task.get('host_id') != host['host_id']):
                return jh.returnJson(False, '切换任务不属于当前归属或机器')
        log_items, error = self._validateLogs(logs, task_id) if logs is not None else ([], '')
        if error:
            return jh.returnJson(False, error)
        now = self._now()
        if task_id and not task and not self._getTask(task_id):
            return jh.returnJson(False, '日志任务不存在')
        try:
            self._upsertReportSnapshot(pair['pair_id'], host, task, now)
        except ValueError as e:
            return jh.returnJson(False, str(e))
        appended = self._appendTaskLogs(task_id, log_items) if task_id else 0
        refreshed = self._refreshPair(pair['pair_id'], now)
        return jh.returnJson(True, '状态已上报', {
            'pair': self._normalizePair(refreshed), 'switch_task_id': task_id,
            'accepted_log_count': appended, 'reported_at': now,
        })

    def switchLogApi(self):
        self.ensureHaSchema()
        task_id = self._safeText(request.values.get('switch_task_id'), 128)
        offset_text = self._safeText(request.values.get('offset', '0'), 32)
        if not self._validId(task_id):
            return jh.returnJson(False, 'switch_task_id无效')
        if not re.match(r'^\d+$', offset_text):
            return jh.returnJson(False, 'offset必须为非负整数')
        offset = int(offset_text)
        task = self._getTask(task_id)
        if not task:
            return jh.returnJson(False, '切换任务不存在')
        try:
            expected_path = self._taskPaths(task_id)['log_path']
        except ValueError:
            return jh.returnJson(False, '切换任务日志路径无效')
        if os.path.realpath(task.get('log_path') or expected_path) != os.path.realpath(expected_path):
            return jh.returnJson(False, '切换任务日志路径无效')
        content = b''
        if os.path.exists(expected_path):
            with open(expected_path, 'rb') as fp:
                fp.seek(offset)
                content = fp.read(1024 * 1024)
                next_offset = fp.tell()
        else:
            next_offset = offset
        return jh.returnJson(True, 'ok', {
            'switch_task_id': task_id, 'log_path': expected_path, 'offset': offset,
            'next_offset': next_offset, 'content': content.decode('utf-8', errors='replace'),
        })

    def localListApi(self):
        self.ensureHaSchema()
        rows = jh.M('ha_pair').where('local_type=?', (self.PAIR_TYPE,)).field(self.PAIR_FIELDS).order('sort_id asc,id desc').select()
        pairs = []
        if isinstance(rows, list):
            for item in rows:
                if not isinstance(item, dict):
                    continue
                pairs.append(self._normalizePair(item))
        return jh.returnJson(True, 'ok', {'list': pairs})

    def localDetailApi(self):
        self.ensureHaSchema()
        pair_id = self._safeText(request.values.get('pair_id'), 128)
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '归属不存在')
        return jh.returnJson(True, 'ok', self._normalizePair(pair, include_tasks=True))
