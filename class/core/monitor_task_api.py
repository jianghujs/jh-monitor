# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# 监控任务管理（脚本日志监控）
# ---------------------------------------------------------------------------------

import os
import re
import sys
import time

import jh

try:
    import shlex
except Exception:
    shlex = None

from flask import Flask, request

app = Flask(__name__)


class monitor_task_api:

    field = (
        'id,task_id,task_name,host_id,host_name,host_ip,log_path,check_interval,'
        'grace_seconds,interval_value,interval_unit,'
        'enabled,install_status,install_msg,last_status,last_msg,'
        'last_run_at,last_event_at,last_analyse_at,addtime,update_time'
    )

    # 统一的任务日志根目录，每个任务一个子目录
    LOG_ROOT = '/var/log/jh-monitor/tasks'

    allowed_install_status = ('pending', 'installed', 'failed', 'unknown')
    allowed_analysis_status = ('normal', 'warning', 'error', 'unknown')

    def __init__(self):
        pass

    def _now(self):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def _quoteShell(self, value):
        if value is None:
            value = ''
        value = str(value)
        if shlex:
            return shlex.quote(value)
        return "'" + value.replace("'", "'\\''") + "'"

    def _safeInt(self, value, default=0, min_value=None, max_value=None):
        try:
            value = int(str(value).strip())
        except Exception:
            value = default
        if min_value is not None and value < min_value:
            value = min_value
        if max_value is not None and value > max_value:
            value = max_value
        return value

    def _normalizeEnabled(self, value, default=1):
        text = str(value if value is not None else default).strip().lower()
        if text in ('1', 'true', 'yes', 'on', 'enabled'):
            return 1
        if text in ('0', 'false', 'no', 'off', 'disabled'):
            return 0
        return int(default)

    def _normalizeStatus(self, value, allowed, default):
        value = str(value or '').strip().lower()
        if value in allowed:
            return value
        return default

    def _normalizeLogPath(self, value):
        value = str(value or '').strip()
        value = value.replace('\x00', '')
        return value

    def _getServerUrl(self):
        server_url = request.form.get('server_url', '').strip() or request.args.get('server_url', '').strip()
        if server_url:
            return server_url.rstrip('/')
        return 'http://{0}:10844'.format(jh.getHostAddr())

    def _buildLogPath(self, task_id):
        """根据 task_id 生成统一管理的日志路径，每个任务一个子目录。"""
        task_id = str(task_id or '').strip()
        return '{0}/{1}/task.json.log'.format(self.LOG_ROOT.rstrip('/'), task_id)

    # 检查频率单位换算成秒
    INTERVAL_UNIT_SECONDS = {'day': 86400, 'hour': 3600, 'minute': 60}
    INTERVAL_UNIT_LABELS = {'day': '天', 'hour': '小时', 'minute': '分钟'}
    DEFAULT_INTERVAL_VALUE = 1
    DEFAULT_INTERVAL_UNIT = 'day'

    def _normalizeInterval(self, payload):
        """归一化检查频率：返回 (interval_value, interval_unit)。"""
        unit = str(payload.get('interval_unit', self.DEFAULT_INTERVAL_UNIT) or self.DEFAULT_INTERVAL_UNIT).strip().lower()
        if unit not in self.INTERVAL_UNIT_SECONDS:
            unit = self.DEFAULT_INTERVAL_UNIT
        value = self._safeInt(payload.get('interval_value', self.DEFAULT_INTERVAL_VALUE), self.DEFAULT_INTERVAL_VALUE, 1)
        return value, unit

    def _intervalToSeconds(self, interval_value, interval_unit):
        """把检查频率换算成秒数，用于日报检查该周期内是否有日志。"""
        value = self._safeInt(interval_value, self.DEFAULT_INTERVAL_VALUE, 1)
        unit = str(interval_unit or self.DEFAULT_INTERVAL_UNIT).strip().lower()
        seconds = self.INTERVAL_UNIT_SECONDS.get(unit, 86400)
        return value * seconds

    def _intervalLabel(self, interval_value, interval_unit):
        """把检查频率渲染成中文短文本，如“1天”“6小时”。"""
        value = self._safeInt(interval_value, self.DEFAULT_INTERVAL_VALUE, 1)
        unit = str(interval_unit or self.DEFAULT_INTERVAL_UNIT).strip().lower()
        return '{0}{1}'.format(value, self.INTERVAL_UNIT_LABELS.get(unit, '天'))

    def _deriveGraceSeconds(self, check_interval):
        """按检查周期推导宽限时间：周期的 1/4，限定在 5 分钟到 1 天之间。"""
        check_interval = self._safeInt(check_interval, 86400, 60)
        grace = int(check_interval / 4)
        if grace < 300:
            grace = 300
        if grace > 86400:
            grace = 86400
        return grace

    def ensureMonitorTaskSchema(self):
        task_db = jh.M('monitor_task')
        create_sql = """
CREATE TABLE IF NOT EXISTS monitor_task (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id TEXT,
  task_name TEXT,
  host_id TEXT,
  host_name TEXT,
  host_ip TEXT,
  log_path TEXT,
  check_interval INTEGER DEFAULT 86400,
  grace_seconds INTEGER DEFAULT 0,
  interval_value INTEGER DEFAULT 1,
  interval_unit TEXT DEFAULT 'day',
  enabled INTEGER DEFAULT 1,
  install_status TEXT DEFAULT 'pending',
  install_msg TEXT,
  last_status TEXT DEFAULT 'unknown',
  last_msg TEXT,
  last_run_at TEXT,
  last_event_at TEXT,
  last_analyse_at TEXT,
  addtime TEXT,
  update_time TEXT
)
"""
        result = task_db.originExecute(create_sql)
        if isinstance(result, str):
            return False

        columns = task_db.originExecute('PRAGMA table_info(monitor_task)').fetchall()
        existing = set([column[1] for column in columns])
        column_defs = {
            'task_id': 'TEXT',
            'task_name': 'TEXT',
            'host_id': 'TEXT',
            'host_name': 'TEXT',
            'host_ip': 'TEXT',
            'log_path': 'TEXT',
            'check_interval': 'INTEGER DEFAULT 86400',
            'grace_seconds': 'INTEGER DEFAULT 0',
            'interval_value': 'INTEGER DEFAULT 1',
            'interval_unit': "TEXT DEFAULT 'day'",
            'enabled': 'INTEGER DEFAULT 1',
            'install_status': "TEXT DEFAULT 'pending'",
            'install_msg': 'TEXT',
            'last_status': "TEXT DEFAULT 'unknown'",
            'last_msg': 'TEXT',
            'last_run_at': 'TEXT',
            'last_event_at': 'TEXT',
            'last_analyse_at': 'TEXT',
            'addtime': 'TEXT',
            'update_time': 'TEXT'
        }
        for column, definition in column_defs.items():
            if column not in existing:
                alter_result = task_db.originExecute(
                    'ALTER TABLE monitor_task ADD COLUMN {0} {1}'.format(column, definition)
                )
                if isinstance(alter_result, str):
                    return False
        try:
            task_db.originExecute('CREATE UNIQUE INDEX IF NOT EXISTS idx_monitor_task_task_id ON monitor_task(task_id)')
            task_db.originExecute('CREATE INDEX IF NOT EXISTS idx_monitor_task_host_id ON monitor_task(host_id)')
            task_db.originExecute('CREATE INDEX IF NOT EXISTS idx_monitor_task_enabled ON monitor_task(enabled)')
        except Exception:
            pass
        return True

    def _getHost(self, host_id):
        host_id = str(host_id or '').strip()
        if not host_id:
            return {}
        row = jh.M('host').where('host_id=?', (host_id,)).field(
            'id,host_id,host_name,ip'
        ).find()
        if isinstance(row, dict):
            return row
        return {}

    def _buildTaskId(self):
        return 'MT_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(6))

    def _normalizeTaskRow(self, row):
        if not isinstance(row, dict):
            return row
        for key in ('id', 'check_interval', 'grace_seconds', 'interval_value', 'enabled'):
            row[key] = self._safeInt(row.get(key), 0)
        if not row.get('interval_unit'):
            row['interval_unit'] = self.DEFAULT_INTERVAL_UNIT
        if not row.get('interval_value'):
            row['interval_value'] = self.DEFAULT_INTERVAL_VALUE
        if not row.get('install_status'):
            row['install_status'] = 'pending'
        if not row.get('last_status'):
            row['last_status'] = 'unknown'
        row['enabled_text'] = '启用' if row.get('enabled') else '停用'
        row['interval_label'] = self._intervalLabel(row.get('interval_value'), row.get('interval_unit'))
        return row

    def _validateTaskPayload(self, task_id, is_update=False):
        task_name = request.form.get('task_name', '').strip()
        enabled = self._normalizeEnabled(request.form.get('enabled', 1), 1)
        interval_value, interval_unit = self._normalizeInterval(request.form)

        if not task_name:
            return False, '监控项名称不能为空', None
        if len(task_name) > 100:
            return False, '监控项名称不能超过100个字符', None

        check_interval = self._intervalToSeconds(interval_value, interval_unit)
        grace_seconds = self._deriveGraceSeconds(check_interval)
        log_path = self._buildLogPath(task_id)

        data = {
            'task_name': task_name,
            'log_path': log_path,
            'check_interval': check_interval,
            'grace_seconds': grace_seconds,
            'interval_value': interval_value,
            'interval_unit': interval_unit,
            'enabled': enabled,
            'update_time': self._now()
        }
        return True, 'ok', data

    def getTaskById(self, task_id):
        self.ensureMonitorTaskSchema()
        row = jh.M('monitor_task').where('task_id=?', (task_id,)).field(self.field).find()
        if isinstance(row, dict):
            return self._normalizeTaskRow(row)
        return {}

    def listRows(self, enabled=None, host_id=None):
        self.ensureMonitorTaskSchema()
        task_db = jh.M('monitor_task')
        where = []
        params = []
        if enabled is not None:
            where.append('enabled=?')
            params.append(self._normalizeEnabled(enabled, 1))
        if host_id:
            where.append('host_id=?')
            params.append(str(host_id).strip())
        if where:
            task_db.where(' and '.join(where), tuple(params))
        rows = task_db.field(self.field).order('id desc').select()
        if not isinstance(rows, list):
            return []
        return [self._normalizeTaskRow(row) for row in rows if isinstance(row, dict)]

    def listApi(self):
        self.ensureMonitorTaskSchema()
        limit = self._safeInt(request.form.get('limit', request.args.get('limit', 100)), 100, 1, 1000)
        p = self._safeInt(request.form.get('p', request.args.get('p', 1)), 1, 1)
        search = request.form.get('search', request.args.get('search', '')).strip().lower()
        host_id = request.form.get('host_id', request.args.get('host_id', '')).strip()

        rows = self.listRows(host_id=host_id)
        if search:
            filtered = []
            for row in rows:
                haystack = ' '.join([
                    str(row.get('task_name', '')),
                    str(row.get('task_id', '')),
                    str(row.get('host_name', '')),
                    str(row.get('host_ip', '')),
                    str(row.get('log_path', ''))
                ]).lower()
                if search in haystack:
                    filtered.append(row)
            rows = filtered

        count = len(rows)
        start = (p - 1) * limit
        page_rows = rows[start:start + limit]

        # Enrich with real-time ES data for enabled+installed tasks
        self._enrichRowsWithLatestEvents(page_rows)

        data = {
            'data': page_rows
        }
        page_args = {
            'count': count,
            'tojs': 'getMonitorTaskList',
            'p': p,
            'row': limit
        }
        data['page'] = jh.getPage(page_args)
        return jh.getJson(data)

    def addApi(self):
        self.ensureMonitorTaskSchema()
        task_id = self._buildTaskId()
        ok, msg, data = self._validateTaskPayload(task_id)
        if not ok:
            return jh.returnJson(False, msg)
        now_time = self._now()
        data.update({
            'task_id': task_id,
            'install_status': 'pending',
            'last_status': 'unknown',
            'addtime': now_time,
            'update_time': now_time
        })
        result = jh.M('monitor_task').insert(data)
        if isinstance(result, str):
            return jh.returnJson(False, '添加失败:' + result)
        return jh.returnJson(True, '添加成功', self.getTaskById(data['task_id']))

    def editApi(self):
        self.ensureMonitorTaskSchema()
        task_id = request.form.get('task_id', '').strip()
        if not task_id:
            return jh.returnJson(False, 'task_id不能为空')
        if not self.getTaskById(task_id):
            return jh.returnJson(False, '监控任务不存在')
        ok, msg, data = self._validateTaskPayload(task_id, is_update=True)
        if not ok:
            return jh.returnJson(False, msg)
        result = jh.M('monitor_task').where('task_id=?', (task_id,)).update(data)
        if isinstance(result, str):
            return jh.returnJson(False, '修改失败:' + result)
        return jh.returnJson(True, '修改成功', self.getTaskById(task_id))

    def deleteApi(self):
        self.ensureMonitorTaskSchema()
        task_id = request.form.get('task_id', '').strip()
        if not task_id:
            return jh.returnJson(False, 'task_id不能为空')
        result = jh.M('monitor_task').where('task_id=?', (task_id,)).delete()
        if isinstance(result, str):
            return jh.returnJson(False, '删除失败:' + result)
        return jh.returnJson(True, '删除成功')

    def setEnabledApi(self):
        self.ensureMonitorTaskSchema()
        task_id = request.form.get('task_id', '').strip()
        enabled = self._normalizeEnabled(request.form.get('enabled', 1), 1)
        if not task_id:
            return jh.returnJson(False, 'task_id不能为空')
        result = jh.M('monitor_task').where('task_id=?', (task_id,)).save(
            'enabled,update_time', (enabled, self._now())
        )
        if isinstance(result, str):
            return jh.returnJson(False, '设置失败:' + result)
        return jh.returnJson(True, '设置成功', self.getTaskById(task_id))

    def updateInstallStatus(self, task_id, install_status, install_msg=''):
        self.ensureMonitorTaskSchema()
        install_status = self._normalizeStatus(install_status, self.allowed_install_status, 'unknown')
        result = jh.M('monitor_task').where('task_id=?', (task_id,)).save(
            'install_status,install_msg,update_time',
            (install_status, str(install_msg or ''), self._now())
        )
        return not isinstance(result, str)

    def upsertTaskFromSetup(self, task_data):
        self.ensureMonitorTaskSchema()
        task_id = str(task_data.get('task_id', '') or '').strip()
        if not task_id:
            task_id = self._buildTaskId()
        host = self._getHost(task_data.get('host_id', ''))
        if not host:
            return False, '指定主机不存在', None
        now_time = self._now()
        existing = self.getTaskById(task_id)
        # 日志路径与频率均由服务器统一管理，安装回调只负责绑定主机。
        log_path = self._buildLogPath(task_id)
        data = {
            'task_id': task_id,
            'task_name': str(task_data.get('task_name', '') or '').strip() or (existing.get('task_name') if existing else '') or task_id,
            'host_id': host.get('host_id', ''),
            'host_name': host.get('host_name', ''),
            'host_ip': host.get('ip', ''),
            'log_path': log_path,
            'install_status': self._normalizeStatus(task_data.get('install_status', 'pending'), self.allowed_install_status, 'pending'),
            'update_time': now_time
        }
        if existing:
            result = jh.M('monitor_task').where('task_id=?', (task_id,)).update(data)
        else:
            # 防御性创建：默认每 1 天检查一次
            interval_value, interval_unit = self.DEFAULT_INTERVAL_VALUE, self.DEFAULT_INTERVAL_UNIT
            data['check_interval'] = self._intervalToSeconds(interval_value, interval_unit)
            data['grace_seconds'] = self._deriveGraceSeconds(data['check_interval'])
            data['interval_value'] = interval_value
            data['interval_unit'] = interval_unit
            data['enabled'] = self._normalizeEnabled(task_data.get('enabled', 1), 1)
            data['addtime'] = now_time
            data['last_status'] = 'unknown'
            result = jh.M('monitor_task').insert(data)
        if isinstance(result, str):
            return False, result, None
        return True, 'ok', self.getTaskById(task_id)

    def buildInstallCommand(self, task_row, server_url=None):
        server_url = (server_url or self._getServerUrl()).rstrip('/')
        script_url = server_url + '/pub/get_monitor_task_install_script'
        parts = [
            'wget -O /tmp/install_monitor_task.sh {0}'.format(self._quoteShell(script_url)),
            '&& bash /tmp/install_monitor_task.sh install',
            '--server-url {0}'.format(self._quoteShell(server_url)),
            '--task-id {0}'.format(self._quoteShell(task_row.get('task_id', ''))),
            '--task-name {0}'.format(self._quoteShell(task_row.get('task_name', '')))
        ]
        return ' '.join(parts)

    def buildLogCommand(self, task_row):
        """根据 task_id 生成业务脚本使用的写入日志命令示例，包含成功、异常、提醒三种场景。"""
        task_id = task_row.get('task_id', '')
        tid = self._quoteShell(task_id)
        return (
            'jh-monitor-task-log --task-id {0} --status success --msg "执行成功"\n'
            'jh-monitor-task-log --task-id {0} --status error --msg "连接超时"\n'
            'jh-monitor-task-log --task-id {0} --status warning --msg "耗时偏长"'
        ).format(tid)

    def getInstallCommandApi(self):
        self.ensureMonitorTaskSchema()
        task_id = request.form.get('task_id', request.args.get('task_id', '')).strip()
        if not task_id:
            return jh.returnJson(False, 'task_id不能为空')
        task_row = self.getTaskById(task_id)
        if not task_row:
            return jh.returnJson(False, '监控任务不存在')
        command = self.buildInstallCommand(task_row)
        log_command = self.buildLogCommand(task_row)
        return jh.returnJson(True, 'ok', {
            'command': command,
            'log_command': log_command,
            'task': task_row
        })
    def _enrichRowsWithLatestEvents(self, rows):
        """Enrich task rows with real-time status/msg from ES latest events."""
        if not rows:
            return
        now_ts = int(time.time())
        for row in rows:
            enabled = self._safeInt(row.get('enabled', 1), 1)
            install_status = str(row.get('install_status', '') or '').strip().lower()
            if not enabled:
                row['last_status'] = 'disabled'
                row['last_msg'] = ''
                continue
            if install_status != 'installed':
                row['last_status'] = 'unknown'
                row['last_msg'] = install_status
                continue
            # Reuse _evaluateTaskStatus which queries ES per-task
            try:
                last_status, last_msg, last_run_at, _ = self._evaluateTaskStatus(row)
                row['last_status'] = last_status
                row['last_msg'] = last_msg
                row['last_run_at'] = last_run_at
            except Exception:
                pass

    def _evaluateTaskStatus(self, task_row):
        """Evaluate a single monitor task's status from latest ES event."""
        task_id = task_row.get('task_id', '')
        host_id = task_row.get('host_id', '')
        check_interval = self._safeInt(task_row.get('check_interval', 86400), 86400, 60)
        grace_seconds = self._safeInt(task_row.get('grace_seconds', 0), 0, 0)
        install_status = str(task_row.get('install_status', '') or '').strip().lower()
        enabled = self._safeInt(task_row.get('enabled', 1), 1)
        addtime = str(task_row.get('addtime', '') or '').strip()

        now_ts = int(time.time())
        now_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(now_ts))

        if not enabled:
            return 'disabled', '', '', now_str

        if install_status != 'installed':
            return 'unknown', '', install_status, now_str

        # Query latest event from ES
        try:
            es_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'es')
            if es_dir not in sys.path:
                sys.path.insert(0, es_dir)
            from monitor_task_event_service import getLatestTaskEvent
            latest_event = getLatestTaskEvent(task_id, host_id)
        except Exception:
            latest_event = {}

        if not latest_event:
            # No event yet - check if within first interval
            try:
                add_ts = int(time.mktime(time.strptime(addtime, '%Y-%m-%d %H:%M:%S')))
            except Exception:
                add_ts = now_ts
            if now_ts <= add_ts + check_interval + grace_seconds:
                return 'unknown', '安装后等待首次日志', '', now_str
            else:
                return 'error', '未发现任务日志', '', now_str

        # Parse latest event
        event_status = str(latest_event.get('status', '') or '').strip().lower()
        event_msg = str(latest_event.get('msg', '') or '').strip()
        run_at = str(latest_event.get('run_at', '') or '').strip()
        if not run_at:
            run_at = str(latest_event.get('@timestamp', '') or '').strip()

        # Check freshness
        if run_at:
            try:
                run_ts = int(time.mktime(time.strptime(run_at[:19], '%Y-%m-%d %H:%M:%S')))
            except Exception:
                run_ts = now_ts
            if now_ts > run_ts + check_interval + grace_seconds:
                return 'error', '未按照频率产生日志; ' + event_msg, run_at, now_str

        # Map event status to analysis status
        status_map = {'success': 'normal', 'warning': 'warning', 'error': 'error'}
        analysis_status = status_map.get(event_status, 'unknown')
        return analysis_status, event_msg, run_at, now_str

    def refreshTaskStatusApi(self):
        """Manually refresh a single monitor task's status by querying ES."""
        self.ensureMonitorTaskSchema()
        task_id = request.form.get('task_id', '').strip()
        if not task_id:
            return jh.returnJson(False, 'task_id不能为空')
        task_row = self.getTaskById(task_id)
        if not task_row:
            return jh.returnJson(False, '监控任务不存在')

        try:
            last_status, last_msg, last_run_at, last_analyse_at = self._evaluateTaskStatus(task_row)
            now_time = self._now()
            jh.M('monitor_task').where('task_id=?', (task_id,)).save(
                'last_status,last_msg,last_run_at,last_analyse_at,update_time',
                (last_status, last_msg, last_run_at, last_analyse_at, now_time)
            )
            updated_row = self.getTaskById(task_id)
            return jh.returnJson(True, '监控任务状态已刷新', {
                'task_id': task_id,
                'last_status': last_status,
                'last_msg': last_msg,
                'last_run_at': last_run_at,
                'task': updated_row,
            })
        except Exception as ex:
            import traceback
            traceback.print_exc()
            return jh.returnJson(False, '刷新任务状态失败: {0}'.format(str(ex)))

