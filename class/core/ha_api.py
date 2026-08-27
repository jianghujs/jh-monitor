# coding: utf-8

import hashlib
import hmac
import json
import os
import time
import urllib.request
import urllib.error

from flask import request

import jh


class ha_api:

    LOG_ROOT = '/www/server/jh-monitor/logs/ha_switch'
    SYNC_LOG_ROOT = '/www/server/jh-monitor/logs/ha_sync'
    NONCE_TTL_SECONDS = 600
    REPORT_LOST_SECONDS = 300
    DEFAULT_SECRET = 'jh-monitor-ha-bootstrap-secret'
    MONITOR_SYNC_VERSION = '1.0'
    DEFAULT_SYNC_TYPE = 'ha_management'

    pair_fields = (
        'id,pair_id,pair_name,desired_master_host_id,actual_master_host_id,status,status_text,'
        'last_report_at,current_switch_run_id,callback_url,callback_enabled,callback_status,'
        'api_secret,sort_id,source_monitor_id,sync_update_at,addtime,update_time'
    )

    state_fields = (
        'id,pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,'
        'collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,'
        'current_step,next_step,last_error,log_path,last_report_at,report_batch_id,source_monitor_id,'
        'sync_update_at,addtime,update_time'
    )

    sync_config_fields = (
        'id,sync_id,sync_name,sync_type,peer_monitor_url,peer_monitor_id,peer_monitor_name,'
        'sync_secret,enabled,last_sync_at,last_error,status,addtime,update_time'
    )

    sync_event_fields = (
        'id,event_id,sync_type,source_monitor_id,source_monitor_name,event_type,object_key,'
        'payload_json,seq,addtime'
    )

    run_fields = (
        'id,switch_run_id,pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,'
        'options_json,status,current_phase,current_step,next_step,last_error,step_summary,log_path,'
        'callback_status,callback_error,origin_monitor_id,execution_monitor_id,claimed_by_host_id,'
        'claim_token,claim_expire_at,sync_status,dispatchable,dispatch_reason,source_monitor_id,'
        'sync_update_at,addtime,update_time,finish_time'
    )

    alert_event_fields = (
        'id,pair_id,event_id,event_type,alert_key,alert_type,alert_level,status,title,message,'
        'sent_by_host_id,report_host_id,notifier_mode,alerts_json,addtime'
    )

    def _now(self):
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

    def _jsonLoads(self, text, default=None):
        if default is None:
            default = {}
        if isinstance(text, (dict, list)):
            return text
        try:
            return json.loads(text or '')
        except Exception:
            return default

    def _bodyJson(self):
        data = request.get_json(silent=True)
        if isinstance(data, dict):
            return data
        raw = request.form.get('data', '')
        if raw:
            return self._jsonLoads(raw, {})
        result = {}
        for key in request.form.keys():
            result[key] = request.form.get(key)
        return result

    def _safeText(self, value, max_len=255):
        value = str(value or '').replace('\x00', '').strip()
        if len(value) > max_len:
            value = value[:max_len]
        return value

    def _safeInt(self, value, default=0):
        try:
            return int(str(value).strip())
        except Exception:
            return default

    def _runId(self):
        return 'HSR_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(6))

    def _monitorId(self):
        return 'JHM_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(8))

    def _syncId(self):
        return 'HMS_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(6))

    def _syncEventId(self):
        return 'HSE_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(10))

    def _defaultSwitchOptions(self):
        return {
            'run_checksum': True,
            'sync_files': True,
            'sync_file_dirs': '/www/wwwroot,/www/wwwstorage',
            'sync_ignore_dirs': '.git,node_modules,logs,run',
            'restore_site_setting': False,
            'restore_plugin_setting': False,
            'run_xtrabackup_inc_restore': False,
            'promote_mysql': True,
            'checksum_confirmed': False,
            'allow_checksum_diff': False,
        }

    def _boolValue(self, value):
        return str(value).lower() in ('1', 'true', 'yes', 'on')

    def _switchOptionsSummary(self, options):
        return '切换选项 sync_files={0}, run_checksum={1}, run_xtrabackup_inc_restore={2}, restore_site_setting={3}, restore_plugin_setting={4}, sync_file_dirs={5}, sync_ignore_dirs={6}'.format(
            str(options.get('sync_files')).lower(),
            str(options.get('run_checksum')).lower(),
            str(options.get('run_xtrabackup_inc_restore')).lower(),
            str(options.get('restore_site_setting')).lower(),
            str(options.get('restore_plugin_setting')).lower(),
            self._safeText(options.get('sync_file_dirs'), 500) or '--',
            self._safeText(options.get('sync_ignore_dirs'), 500) or '--',
        )

    def _switchOptionsFromRequest(self):
        request_options = self._bodyJson()
        options = self._defaultSwitchOptions()
        options.update(request_options)
        for key in ('pair_id', 'target_host_id', 'desired_master_host_id', 'action'):
            options.pop(key, None)
        for key in ('local_ip', 'remote_ip', 'remote_ssh_port'):
            options.pop(key, None)
        for key in ('sync_files', 'run_checksum', 'allow_checksum_diff', 'checksum_confirmed', 'restore_site_setting', 'restore_plugin_setting', 'run_xtrabackup_inc_restore', 'confirm_failover'):
            if key in options:
                options[key] = self._boolValue(options.get(key))
        options['promote_mysql'] = True
        return options

    def _masterHostId(self, pair_id, fallback=''):
        states = self._displayStates(self._getStates(pair_id))
        actual = self._actualMasterHostId(states)
        if actual:
            return actual
        return fallback

    def _fallbackOldMasterHostId(self, pair_id, target_host_id, fallback='', allow_any_peer=False):
        target_host_id = self._safeText(target_host_id, 128)
        states = self._displayStates(self._getStates(pair_id))
        for state in states:
            host_id = state.get('host_id') or ''
            if host_id and host_id != target_host_id and state.get('role') == 'master':
                return host_id
        if allow_any_peer:
            for state in states:
                host_id = state.get('host_id') or ''
                if host_id and host_id != target_host_id:
                    return host_id
        return fallback

    def _hostAliases(self, state):
        aliases = state.get('_alias_host_ids') or []
        if state.get('host_id') and state.get('host_id') not in aliases:
            aliases.append(state.get('host_id'))
        detail = self._jsonLoads(state.get('health_detail'), {})
        source_host_id = detail.get('_source_host_id') if isinstance(detail, dict) else ''
        if source_host_id and source_host_id not in aliases:
            aliases.append(source_host_id)
        return aliases

    def _currentMonitorCanExecuteTarget(self, pair_id, target_host_id):
        target_host_id = self._safeText(target_host_id, 128)
        raw_states = self._getStates(pair_id)
        states = self._displayStates(raw_states)
        for state in states:
            if target_host_id not in self._hostAliases(state):
                continue
            if state.get('collect_method') == 'local':
                return True, '目标主机在当前江湖云监控本机房，可本机执行'
            if state.get('collect_method') == 'ssh_peer' and state.get('report_host_id'):
                return True, '当前江湖云监控存在可 SSH 远程触发目标主机的插件'
        for state in raw_states:
            if target_host_id in self._hostAliases(state) and state.get('collect_method') == 'ssh_peer' and state.get('report_host_id'):
                return True, '当前江湖云监控存在可 SSH 远程触发目标主机的插件'
        return False, '当前江湖云监控没有可执行目标主机的本机插件或 ssh_peer 代理'

    def _selectExecutionMonitor(self, pair_id, target_host_id):
        local_monitor = self._localMonitor()
        local_monitor_id = local_monitor.get('monitor_id') or ''
        can_execute, reason = self._currentMonitorCanExecuteTarget(pair_id, target_host_id)
        if can_execute:
            return local_monitor_id, reason
        states = self._displayStates(self._getStates(pair_id))
        for state in states:
            if target_host_id not in self._hostAliases(state):
                continue
            source_monitor_id = state.get('source_monitor_id') or ''
            if source_monitor_id and source_monitor_id != local_monitor_id:
                return source_monitor_id, reason + '；同步状态显示目标主机来自对端江湖云监控'
        rows = jh.M('ha_sync_config').where('enabled=? AND sync_type=?', (1, self.DEFAULT_SYNC_TYPE)).field(self.sync_config_fields).select()
        if isinstance(rows, list):
            for row in rows:
                if row.get('peer_monitor_id'):
                    return row.get('peer_monitor_id'), reason + '；使用已启用同步配置的对端江湖云监控执行'
        return local_monitor_id, reason

    def _createSwitchRun(self, pair, target_host_id, phase, current_step, next_step, status, options, action_text, old_master_host_id='', execution_monitor_id='', dispatch_reason=''):
        pair_id = pair.get('pair_id')
        switch_run_id = self._runId()
        old_master = old_master_host_id or self._masterHostId(pair_id, pair.get('actual_master_host_id') or '')
        log_path = self._monthLogPath(switch_run_id)
        now = self._now()
        monitor_id = self._localMonitor().get('monitor_id')
        execution_monitor_id = execution_monitor_id or monitor_id
        jh.M('ha_switch_run').add(
            'switch_run_id,pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,options_json,status,current_phase,current_step,next_step,log_path,callback_status,origin_monitor_id,execution_monitor_id,sync_status,dispatchable,dispatch_reason,source_monitor_id,addtime,update_time',
            (switch_run_id, pair_id, old_master, target_host_id, target_host_id, json.dumps(options, ensure_ascii=False), status, phase, current_step, next_step, log_path, 'pending', monitor_id, execution_monitor_id, 'local', 1, dispatch_reason, monitor_id, now, now)
        )
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).save(
            'desired_master_host_id,current_switch_run_id,status,status_text,update_time',
            (target_host_id, switch_run_id, 'switching', current_step, now)
        )
        self._appendLog(log_path, '[{0}] [system] [pending] 创建切换任务 {1}，动作 {2}，目标主机 {3}'.format(now, switch_run_id, action_text, target_host_id))
        self._appendLog(log_path, '[{0}] [system] [pending] {1}'.format(now, self._switchOptionsSummary(options)))
        if execution_monitor_id != monitor_id:
            self._appendLog(log_path, '[{0}] [system] [pending] 当前江湖云监控不可直接执行，任务将同步到执行方江湖云监控 {1}；原因：{2}'.format(now, execution_monitor_id, dispatch_reason or '对端有可执行插件'))
        run = self._getRun(switch_run_id)
        self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_switch_run', switch_run_id, {'run': self._normalizeRun(run)})
        self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_pair', pair_id, {'pair': self._getPair(pair_id)})
        return {'switch_run_id': switch_run_id, 'log_path': log_path}

    def ensureHaSchema(self):
        db = jh.M('ha_pair')
        statements = [
            """
CREATE TABLE IF NOT EXISTS ha_pair (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair_id TEXT,
  pair_name TEXT,
  desired_master_host_id TEXT,
  actual_master_host_id TEXT,
  status TEXT DEFAULT 'unknown',
  status_text TEXT,
  last_report_at TEXT,
  current_switch_run_id TEXT,
  callback_url TEXT,
  callback_enabled INTEGER DEFAULT 0,
  callback_status TEXT,
  api_secret TEXT,
  sort_id INTEGER DEFAULT 0,
  addtime TEXT,
  update_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_host_state (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair_id TEXT,
  host_id TEXT,
  host_name TEXT,
  host_ip TEXT,
  role TEXT,
  online_status TEXT DEFAULT 'unknown',
  health_status TEXT DEFAULT 'unknown',
  collect_status TEXT DEFAULT 'unknown',
  collect_method TEXT,
  report_host_id TEXT,
  site_scope TEXT,
  health_detail TEXT,
  switch_run_id TEXT,
  switch_phase TEXT,
  switch_status TEXT,
  current_step TEXT,
  next_step TEXT,
  last_error TEXT,
  log_path TEXT,
  last_report_at TEXT,
  report_batch_id TEXT,
  addtime TEXT,
  update_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_switch_run (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  switch_run_id TEXT,
  pair_id TEXT,
  old_master_host_id TEXT,
  new_master_host_id TEXT,
  desired_master_host_id TEXT,
  options_json TEXT,
  status TEXT DEFAULT 'pending',
  current_phase TEXT,
  current_step TEXT,
  next_step TEXT,
  last_error TEXT,
  step_summary TEXT,
  log_path TEXT,
  callback_status TEXT,
  callback_error TEXT,
  addtime TEXT,
  update_time TEXT,
  finish_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_switch_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  switch_run_id TEXT,
  pair_id TEXT,
  event_id TEXT,
  origin_host_id TEXT,
  report_host_id TEXT,
  collect_method TEXT,
  seq INTEGER DEFAULT 0,
  phase TEXT,
  step TEXT,
  status TEXT,
  log_text TEXT,
  addtime TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_alert_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair_id TEXT,
  event_id TEXT,
  event_type TEXT,
  alert_key TEXT,
  alert_type TEXT,
  alert_level TEXT,
  status TEXT,
  title TEXT,
  message TEXT,
  sent_by_host_id TEXT,
  report_host_id TEXT,
  notifier_mode TEXT,
  alerts_json TEXT,
  addtime TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_callback_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  pair_id TEXT,
  switch_run_id TEXT,
  callback_url TEXT,
  status TEXT,
  error_msg TEXT,
  request_body TEXT,
  response_body TEXT,
  addtime TEXT,
  update_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_api_nonce (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nonce TEXT,
  pair_id TEXT,
  addtime INTEGER
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_monitor_identity (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  monitor_id TEXT,
  monitor_name TEXT,
  addtime TEXT,
  update_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_sync_config (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sync_id TEXT,
  sync_name TEXT,
  sync_type TEXT DEFAULT 'ha_management',
  peer_monitor_url TEXT,
  peer_monitor_id TEXT,
  peer_monitor_name TEXT,
  sync_secret TEXT,
  enabled INTEGER DEFAULT 0,
  last_sync_at TEXT,
  last_error TEXT,
  status TEXT,
  addtime TEXT,
  update_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_sync_event (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT,
  sync_type TEXT,
  source_monitor_id TEXT,
  source_monitor_name TEXT,
  event_type TEXT,
  object_key TEXT,
  payload_json TEXT,
  seq INTEGER DEFAULT 0,
  addtime TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_sync_cursor (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sync_id TEXT,
  sync_type TEXT,
  peer_monitor_id TEXT,
  last_seq INTEGER DEFAULT 0,
  last_event_id TEXT,
  last_sync_at TEXT,
  last_error TEXT,
  addtime TEXT,
  update_time TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_sync_applied (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  event_id TEXT,
  sync_id TEXT,
  sync_type TEXT,
  source_monitor_id TEXT,
  object_key TEXT,
  status TEXT,
  error_msg TEXT,
  addtime TEXT
)
""",
            """
CREATE TABLE IF NOT EXISTS ha_sync_nonce (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nonce TEXT,
  sync_id TEXT,
  addtime INTEGER
)
"""
        ]
        for sql in statements:
            result = db.originExecute(sql)
            if isinstance(result, str):
                return False
        table_columns = {
            'ha_pair': {
                'pair_id': 'TEXT', 'pair_name': 'TEXT', 'desired_master_host_id': 'TEXT',
                'actual_master_host_id': 'TEXT', 'status': "TEXT DEFAULT 'unknown'", 'status_text': 'TEXT',
                'last_report_at': 'TEXT', 'current_switch_run_id': 'TEXT', 'callback_url': 'TEXT',
                'callback_enabled': 'INTEGER DEFAULT 0', 'callback_status': 'TEXT', 'api_secret': 'TEXT',
                'sort_id': 'INTEGER DEFAULT 0', 'source_monitor_id': 'TEXT', 'sync_update_at': 'TEXT',
                'addtime': 'TEXT', 'update_time': 'TEXT'
            },
            'ha_host_state': {
                'pair_id': 'TEXT', 'host_id': 'TEXT', 'host_name': 'TEXT', 'host_ip': 'TEXT',
                'role': 'TEXT', 'online_status': "TEXT DEFAULT 'unknown'", 'health_status': "TEXT DEFAULT 'unknown'",
                'collect_status': "TEXT DEFAULT 'unknown'", 'collect_method': 'TEXT', 'report_host_id': 'TEXT',
                'site_scope': 'TEXT', 'health_detail': 'TEXT', 'switch_run_id': 'TEXT', 'switch_phase': 'TEXT', 'switch_status': 'TEXT',
                'current_step': 'TEXT', 'next_step': 'TEXT', 'last_error': 'TEXT', 'log_path': 'TEXT',
                'last_report_at': 'TEXT', 'report_batch_id': 'TEXT', 'source_monitor_id': 'TEXT',
                'sync_update_at': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT'
            },
            'ha_switch_run': {
                'switch_run_id': 'TEXT', 'pair_id': 'TEXT', 'old_master_host_id': 'TEXT',
                'new_master_host_id': 'TEXT', 'desired_master_host_id': 'TEXT', 'options_json': 'TEXT',
                'status': "TEXT DEFAULT 'pending'", 'current_phase': 'TEXT', 'current_step': 'TEXT',
                'next_step': 'TEXT', 'last_error': 'TEXT', 'step_summary': 'TEXT', 'log_path': 'TEXT',
                'callback_status': 'TEXT', 'callback_error': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT',
                'finish_time': 'TEXT', 'origin_monitor_id': 'TEXT', 'execution_monitor_id': 'TEXT',
                'claimed_by_host_id': 'TEXT', 'claim_token': 'TEXT', 'claim_expire_at': 'INTEGER DEFAULT 0',
                'sync_status': 'TEXT', 'dispatchable': 'INTEGER DEFAULT 1', 'dispatch_reason': 'TEXT',
                'source_monitor_id': 'TEXT', 'sync_update_at': 'TEXT'
            },
            'ha_switch_event': {
                'switch_run_id': 'TEXT', 'pair_id': 'TEXT', 'event_id': 'TEXT', 'origin_host_id': 'TEXT',
                'report_host_id': 'TEXT', 'collect_method': 'TEXT', 'seq': 'INTEGER DEFAULT 0', 'phase': 'TEXT',
                'step': 'TEXT', 'status': 'TEXT', 'log_text': 'TEXT', 'addtime': 'TEXT'
            },
            'ha_alert_event': {
                'pair_id': 'TEXT', 'event_id': 'TEXT', 'event_type': 'TEXT', 'alert_key': 'TEXT',
                'alert_type': 'TEXT', 'alert_level': 'TEXT', 'status': 'TEXT', 'title': 'TEXT',
                'message': 'TEXT', 'sent_by_host_id': 'TEXT', 'report_host_id': 'TEXT',
                'notifier_mode': 'TEXT', 'alerts_json': 'TEXT', 'addtime': 'TEXT'
            },
            'ha_callback_record': {
                'pair_id': 'TEXT', 'switch_run_id': 'TEXT', 'callback_url': 'TEXT', 'status': 'TEXT',
                'error_msg': 'TEXT', 'request_body': 'TEXT', 'response_body': 'TEXT', 'addtime': 'TEXT',
                'update_time': 'TEXT'
            },
            'ha_api_nonce': {'nonce': 'TEXT', 'pair_id': 'TEXT', 'addtime': 'INTEGER'},
            'ha_monitor_identity': {'monitor_id': 'TEXT', 'monitor_name': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT'},
            'ha_sync_config': {
                'sync_id': 'TEXT', 'sync_name': 'TEXT', 'sync_type': "TEXT DEFAULT 'ha_management'",
                'peer_monitor_url': 'TEXT', 'peer_monitor_id': 'TEXT', 'peer_monitor_name': 'TEXT',
                'sync_secret': 'TEXT', 'enabled': 'INTEGER DEFAULT 0', 'last_sync_at': 'TEXT',
                'last_error': 'TEXT', 'status': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT'
            },
            'ha_sync_event': {
                'event_id': 'TEXT', 'sync_type': 'TEXT', 'source_monitor_id': 'TEXT', 'source_monitor_name': 'TEXT',
                'event_type': 'TEXT', 'object_key': 'TEXT', 'payload_json': 'TEXT', 'seq': 'INTEGER DEFAULT 0', 'addtime': 'TEXT'
            },
            'ha_sync_cursor': {
                'sync_id': 'TEXT', 'sync_type': 'TEXT', 'peer_monitor_id': 'TEXT', 'last_seq': 'INTEGER DEFAULT 0',
                'last_event_id': 'TEXT', 'last_sync_at': 'TEXT', 'last_error': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT'
            },
            'ha_sync_applied': {
                'event_id': 'TEXT', 'sync_id': 'TEXT', 'sync_type': 'TEXT', 'source_monitor_id': 'TEXT',
                'object_key': 'TEXT', 'status': 'TEXT', 'error_msg': 'TEXT', 'addtime': 'TEXT'
            },
            'ha_sync_nonce': {'nonce': 'TEXT', 'sync_id': 'TEXT', 'addtime': 'INTEGER'}
        }
        for table, columns in table_columns.items():
            info = db.originExecute('PRAGMA table_info({0})'.format(table))
            if isinstance(info, str):
                return False
            existing = set([row[1] for row in info.fetchall()])
            for column, definition in columns.items():
                if column not in existing:
                    result = db.originExecute('ALTER TABLE {0} ADD COLUMN {1} {2}'.format(table, column, definition))
                    if isinstance(result, str):
                        return False
        indexes = [
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_pair_pair_id ON ha_pair(pair_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_host_pair_host ON ha_host_state(pair_id,host_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_switch_run_id ON ha_switch_run(switch_run_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_switch_event_event_id ON ha_switch_event(event_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_switch_event_seq ON ha_switch_event(switch_run_id,origin_host_id,seq)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_alert_event_event_id ON ha_alert_event(event_id)',
            'CREATE INDEX IF NOT EXISTS idx_ha_alert_event_pair_time ON ha_alert_event(pair_id,addtime)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_api_nonce_nonce ON ha_api_nonce(nonce)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_monitor_identity_id ON ha_monitor_identity(monitor_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_sync_config_sync_id ON ha_sync_config(sync_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_sync_event_event_id ON ha_sync_event(event_id)',
            'CREATE INDEX IF NOT EXISTS idx_ha_sync_event_type_seq ON ha_sync_event(sync_type,seq)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_sync_cursor_key ON ha_sync_cursor(sync_id,sync_type)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_sync_applied_event ON ha_sync_applied(event_id)',
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_sync_nonce_nonce ON ha_sync_nonce(nonce)'
        ]
        for sql in indexes:
            try:
                db.originExecute(sql)
            except Exception:
                pass
        self._ensurePairSortOrder()
        self._ensureMonitorIdentity()
        return True

    def _ensurePairSortOrder(self):
        db = jh.M('ha_pair')
        try:
            sort_count_row = db.originExecute(
                'SELECT COUNT(*) FROM ha_pair WHERE sort_id IS NOT NULL AND sort_id > 0'
            ).fetchone()
            sort_count = sort_count_row[0] if sort_count_row else 0
            if sort_count == 0:
                rows = db.originExecute('SELECT id FROM ha_pair ORDER BY id DESC').fetchall()
                sort_value = 1
                for row in rows:
                    db.execute('UPDATE ha_pair SET sort_id=? WHERE id=?', (sort_value, row[0]))
                    sort_value += 1
                return
            max_row = db.originExecute('SELECT MAX(sort_id) FROM ha_pair').fetchone()
            sort_value = (int(max_row[0]) if max_row and max_row[0] else 0) + 1
            rows = db.originExecute('SELECT id FROM ha_pair WHERE sort_id IS NULL OR sort_id <= 0 ORDER BY id DESC').fetchall()
            for row in rows:
                db.execute('UPDATE ha_pair SET sort_id=? WHERE id=?', (sort_value, row[0]))
                sort_value += 1
        except Exception:
            pass

    def _nextPairSortId(self):
        try:
            row = jh.M('ha_pair').originExecute('SELECT MAX(sort_id) FROM ha_pair').fetchone()
            return (int(row[0]) if row and row[0] else 0) + 1
        except Exception:
            return 1

    def _ensureMonitorIdentity(self):
        row = jh.M('ha_monitor_identity').field('id,monitor_id,monitor_name').order('id asc').limit('1').find()
        now = self._now()
        if isinstance(row, dict) and row.get('monitor_id'):
            monitor_name = row.get('monitor_name') or jh.getConfig('title') or '江湖云监控'
            if monitor_name != row.get('monitor_name'):
                jh.M('ha_monitor_identity').where('id=?', (row.get('id'),)).save('monitor_name,update_time', (monitor_name, now))
            return {'monitor_id': row.get('monitor_id'), 'monitor_name': monitor_name}
        monitor_id = self._monitorId()
        monitor_name = jh.getConfig('title') or '江湖云监控'
        jh.M('ha_monitor_identity').add('monitor_id,monitor_name,addtime,update_time', (monitor_id, monitor_name, now, now))
        return {'monitor_id': monitor_id, 'monitor_name': monitor_name}

    def _localMonitor(self):
        self.ensureHaSchema()
        return self._ensureMonitorIdentity()

    def _appendSyncLog(self, line):
        if not os.path.exists(self.SYNC_LOG_ROOT):
            os.makedirs(self.SYNC_LOG_ROOT, mode=0o755, exist_ok=True)
        log_path = os.path.join(self.SYNC_LOG_ROOT, time.strftime('%Y-%m') + '.log')
        with open(log_path, 'a', encoding='utf-8') as fp:
            fp.write('[{0}] {1}\n'.format(self._now(), line.rstrip('\n')))

    def _getSyncConfig(self, sync_id):
        row = jh.M('ha_sync_config').where('sync_id=?', (sync_id,)).field(self.sync_config_fields).find()
        return row if isinstance(row, dict) else {}

    def _normalizeSyncConfig(self, row):
        return {
            'id': row.get('id') or '',
            'sync_id': row.get('sync_id') or '',
            'sync_name': row.get('sync_name') or '',
            'sync_type': row.get('sync_type') or self.DEFAULT_SYNC_TYPE,
            'sync_types': self._syncConfigTypes(row),
            'peer_monitor_url': row.get('peer_monitor_url') or '',
            'peer_monitor_id': row.get('peer_monitor_id') or '',
            'peer_monitor_name': row.get('peer_monitor_name') or '',
            'enabled': self._safeInt(row.get('enabled'), 0) == 1,
            'last_sync_at': row.get('last_sync_at') or '',
            'last_error': row.get('last_error') or '',
            'status': row.get('status') or '',
            'addtime': row.get('addtime') or '',
            'update_time': row.get('update_time') or ''
        }

    def _normalizeSyncType(self, value):
        value = self._safeText(value or self.DEFAULT_SYNC_TYPE, 64)
        if value != self.DEFAULT_SYNC_TYPE:
            return ''
        return value

    def _normalizeSyncTypes(self, values):
        if values is None:
            values = []
        if isinstance(values, str):
            values = values.replace(';', ',').split(',')
        elif not isinstance(values, list):
            values = [values]
        result = []
        for value in values:
            sync_type = self._normalizeSyncType(value)
            if sync_type and sync_type not in result:
                result.append(sync_type)
        return result

    def _syncConfigTypes(self, sync_config):
        sync_types = self._normalizeSyncTypes(sync_config.get('sync_type') or self.DEFAULT_SYNC_TYPE)
        return sync_types or [self.DEFAULT_SYNC_TYPE]

    def _syncConfigSupports(self, sync_config, sync_type):
        return self._normalizeSyncType(sync_type) in self._syncConfigTypes(sync_config)

    def _normalizePeerUrl(self, value):
        value = self._safeText(value, 512).rstrip('/')
        if value and not value.startswith('http://') and not value.startswith('https://'):
            value = 'http://' + value
        return value

    def _bodyHash(self, payload):
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        return hashlib.sha256(body.encode('utf-8')).hexdigest()

    def _syncSignatureHeaders(self, payload, secret):
        timestamp = str(int(time.time()))
        nonce = '{0}_{1}'.format(timestamp, jh.getRandomString(16))
        body_hash = self._bodyHash(payload)
        sign_text = '\n'.join([timestamp, nonce, body_hash])
        signature = hmac.new(str(secret).encode('utf-8'), sign_text.encode('utf-8'), hashlib.sha256).hexdigest()
        return {
            'Content-Type': 'application/json',
            'X-JHM-Timestamp': timestamp,
            'X-JHM-Nonce': nonce,
            'X-JHM-Body-Hash': body_hash,
            'X-JHM-Signature': signature
        }

    def _postSyncJson(self, sync_config, path, payload, timeout=10):
        url = self._normalizePeerUrl(sync_config.get('peer_monitor_url')) + path
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = self._syncSignatureHeaders(payload, sync_config.get('sync_secret') or '')
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode('utf-8', errors='replace')
        return self._jsonLoads(content, {})

    def _verifyMonitorSyncRequest(self, payload):
        sync_id = self._safeText(payload.get('sync_id'), 128)
        timestamp = self._safeText(request.headers.get('X-JHM-Timestamp') or payload.get('timestamp'), 32)
        nonce = self._safeText(request.headers.get('X-JHM-Nonce') or payload.get('nonce'), 128)
        signature = self._safeText(request.headers.get('X-JHM-Signature') or payload.get('signature'), 128)
        body_hash = self._safeText(request.headers.get('X-JHM-Body-Hash') or payload.get('body_hash'), 128)
        if not timestamp or not nonce or not signature:
            return False, '签名参数不完整', {}
        try:
            ts = int(timestamp)
        except Exception:
            return False, 'timestamp无效', {}
        if abs(int(time.time()) - ts) > self.NONCE_TTL_SECONDS:
            return False, 'timestamp已过期', {}
        expected_body_hash = self._bodyHash(payload)
        if body_hash and body_hash != expected_body_hash:
            return False, 'body_hash不匹配', {}
        sign_text = '\n'.join([timestamp, nonce, body_hash or expected_body_hash])
        candidates = []
        if sync_id:
            sync_config = self._getSyncConfig(sync_id)
            if sync_config:
                candidates.append(sync_config)
        if not candidates:
            sync_type = self._normalizeSyncType(payload.get('sync_type') or self.DEFAULT_SYNC_TYPE)
            rows = jh.M('ha_sync_config').where('enabled=?', (1,)).field(self.sync_config_fields).select()
            candidates = [row for row in rows if isinstance(row, dict) and self._syncConfigSupports(row, sync_type)] if isinstance(rows, list) else []
        sync_config = {}
        for item in candidates:
            if self._safeInt(item.get('enabled'), 0) != 1:
                continue
            if payload.get('sync_type') and not self._syncConfigSupports(item, payload.get('sync_type')):
                continue
            expected = hmac.new(str(item.get('sync_secret') or '').encode('utf-8'), sign_text.encode('utf-8'), hashlib.sha256).hexdigest()
            if hmac.compare_digest(signature, expected):
                sync_config = item
                break
        if not sync_config:
            return False, '同步配置不存在或签名错误', {}
        exists = jh.M('ha_sync_nonce').where('nonce=?', (nonce,)).field('id').find()
        if isinstance(exists, dict) and exists.get('id'):
            return False, 'nonce已使用', sync_config
        now = int(time.time())
        jh.M('ha_sync_nonce').add('nonce,sync_id,addtime', (nonce, sync_config.get('sync_id') or sync_id, now))
        try:
            jh.M('ha_sync_nonce').where('addtime<?', (now - self.NONCE_TTL_SECONDS,)).delete()
        except Exception:
            pass
        return True, 'ok', sync_config

    def _writeSyncEvent(self, sync_type, event_type, object_key, payload):
        sync_type = self._normalizeSyncType(sync_type)
        if not sync_type:
            return ''
        monitor = self._localMonitor()
        event_id = self._syncEventId()
        seq_row = jh.M('ha_sync_event').originExecute('SELECT MAX(seq) FROM ha_sync_event WHERE sync_type=?', (sync_type,)).fetchone()
        seq = (int(seq_row[0]) if seq_row and seq_row[0] else 0) + 1
        now = self._now()
        full_payload = dict(payload or {})
        full_payload['_sync_meta'] = {
            'event_id': event_id,
            'sync_type': sync_type,
            'event_type': event_type,
            'source_monitor_id': monitor.get('monitor_id'),
            'source_monitor_name': monitor.get('monitor_name'),
            'seq': seq,
            'addtime': now
        }
        jh.M('ha_sync_event').add(
            'event_id,sync_type,source_monitor_id,source_monitor_name,event_type,object_key,payload_json,seq,addtime',
            (event_id, sync_type, monitor.get('monitor_id'), monitor.get('monitor_name'), event_type, object_key, json.dumps(full_payload, ensure_ascii=False), seq, now)
        )
        return event_id

    def getMonitorIdentityApi(self):
        return jh.returnJson(True, 'ok', self._localMonitor())

    def getSyncConfigListApi(self):
        self.ensureHaSchema()
        rows = jh.M('ha_sync_config').field(self.sync_config_fields).order('id desc').select()
        if not isinstance(rows, list):
            rows = []
        return jh.returnJson(True, 'ok', {
            'monitor': self._localMonitor(),
            'list': [self._normalizeSyncConfig(row) for row in rows]
        })

    def saveSyncConfigApi(self):
        self.ensureHaSchema()
        sync_id = self._safeText(request.form.get('sync_id'), 128)
        sync_name = self._safeText(request.form.get('sync_name'), 128)
        sync_types = self._normalizeSyncTypes(request.form.getlist('sync_types[]') or request.form.getlist('sync_type[]') or request.form.get('sync_types') or request.form.get('sync_type'))
        sync_type = ','.join(sync_types)
        peer_monitor_url = self._normalizePeerUrl(request.form.get('peer_monitor_url'))
        peer_monitor_id = self._safeText(request.form.get('peer_monitor_id'), 128)
        peer_monitor_name = self._safeText(request.form.get('peer_monitor_name'), 128)
        sync_secret = self._safeText(request.form.get('sync_secret'), 255)
        enabled = 1 if self._boolValue(request.form.get('enabled', '0')) else 0
        if not sync_name:
            return jh.returnJson(False, '同步名称不能为空')
        if not sync_types:
            return jh.returnJson(False, '请至少选择一个同步类型')
        if not peer_monitor_url:
            return jh.returnJson(False, '对端江湖云监控地址不能为空')
        now = self._now()
        if sync_id:
            exists = self._getSyncConfig(sync_id)
            if not exists:
                return jh.returnJson(False, '同步配置不存在')
            if not sync_secret:
                sync_secret = exists.get('sync_secret') or ''
        if not sync_secret:
            return jh.returnJson(False, '同步密钥不能为空')
        if sync_id:
            jh.M('ha_sync_config').where('sync_id=?', (sync_id,)).save(
                'sync_name,sync_type,peer_monitor_url,peer_monitor_id,peer_monitor_name,sync_secret,enabled,update_time',
                (sync_name, sync_type, peer_monitor_url, peer_monitor_id, peer_monitor_name, sync_secret, enabled, now)
            )
        else:
            sync_id = self._syncId()
            jh.M('ha_sync_config').add(
                'sync_id,sync_name,sync_type,peer_monitor_url,peer_monitor_id,peer_monitor_name,sync_secret,enabled,status,addtime,update_time',
                (sync_id, sync_name, sync_type, peer_monitor_url, peer_monitor_id, peer_monitor_name, sync_secret, enabled, 'pending', now, now)
            )
        return jh.returnJson(True, '同步配置已保存', self._normalizeSyncConfig(self._getSyncConfig(sync_id)))

    def deleteSyncConfigApi(self):
        self.ensureHaSchema()
        sync_id = self._safeText(request.form.get('sync_id'), 128)
        if not sync_id:
            return jh.returnJson(False, 'sync_id不能为空')
        jh.M('ha_sync_config').where('sync_id=?', (sync_id,)).delete()
        jh.M('ha_sync_cursor').where('sync_id=?', (sync_id,)).delete()
        return jh.returnJson(True, '同步配置已删除')

    def setSyncEnabledApi(self):
        self.ensureHaSchema()
        sync_id = self._safeText(request.form.get('sync_id'), 128)
        enabled = 1 if self._boolValue(request.form.get('enabled', '0')) else 0
        if not self._getSyncConfig(sync_id):
            return jh.returnJson(False, '同步配置不存在')
        jh.M('ha_sync_config').where('sync_id=?', (sync_id,)).save('enabled,update_time', (enabled, self._now()))
        return jh.returnJson(True, '同步配置已更新')

    def testSyncConfigApi(self):
        self.ensureHaSchema()
        sync_id = self._safeText(request.form.get('sync_id'), 128)
        sync_config = self._getSyncConfig(sync_id)
        if not sync_config:
            form_secret = self._safeText(request.form.get('sync_secret'), 255)
            sync_config = {
                'sync_id': sync_id or 'handshake_test',
                'sync_secret': form_secret,
                'peer_monitor_url': self._normalizePeerUrl(request.form.get('peer_monitor_url')),
                'sync_type': ','.join(self._normalizeSyncTypes(request.form.getlist('sync_types[]') or request.form.getlist('sync_type[]') or request.form.get('sync_types') or request.form.get('sync_type')) or [self.DEFAULT_SYNC_TYPE])
            }
        ok, msg, data = self._handshakeSyncConfig(sync_config)
        return jh.returnJson(ok, msg, data)

    def runSyncNowApi(self):
        self.ensureHaSchema()
        sync_id = self._safeText(request.form.get('sync_id'), 128)
        result = self.runMonitorSync(sync_id=sync_id)
        return jh.returnJson(result.get('status') in ('ok', 'partial'), result.get('msg') or '同步完成', result)

    def _handshakeSyncConfig(self, sync_config):
        if not sync_config.get('peer_monitor_url') or not sync_config.get('sync_secret'):
            return False, '请先填写对端地址和同步密钥', {}
        monitor = self._localMonitor()
        payload = {
            'sync_id': sync_config.get('sync_id'),
            'sync_type': sync_config.get('sync_type') or self.DEFAULT_SYNC_TYPE,
            'monitor_id': monitor.get('monitor_id'),
            'monitor_name': monitor.get('monitor_name'),
            'sync_version': self.MONITOR_SYNC_VERSION
        }
        try:
            result = self._postSyncJson(sync_config, '/pub/ha_monitor_sync_handshake', payload)
            if not result.get('status'):
                return False, result.get('msg') or '握手失败', result
            data = result.get('data') or {}
            if sync_config.get('sync_id') and sync_config.get('sync_id') != 'handshake_test':
                now = self._now()
                jh.M('ha_sync_config').where('sync_id=?', (sync_config.get('sync_id'),)).save(
                    'peer_monitor_id,peer_monitor_name,last_error,status,update_time',
                    (data.get('monitor_id') or '', data.get('monitor_name') or '', '', 'handshake_ok', now)
                )
            return True, '握手成功', data
        except Exception as e:
            msg = str(e)
            if sync_config.get('sync_id') and sync_config.get('sync_id') != 'handshake_test':
                jh.M('ha_sync_config').where('sync_id=?', (sync_config.get('sync_id'),)).save('last_error,status,update_time', (msg, 'handshake_failed', self._now()))
            return False, '握手失败: ' + msg, {}

    def publicMonitorSyncHandshake(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        ok, msg, sync_config = self._verifyMonitorSyncRequest(payload)
        if not ok:
            return jh.returnJson(False, msg)
        peer_monitor_id = self._safeText(payload.get('monitor_id'), 128)
        peer_monitor_name = self._safeText(payload.get('monitor_name'), 128)
        if peer_monitor_id or peer_monitor_name:
            jh.M('ha_sync_config').where('sync_id=?', (sync_config.get('sync_id'),)).save(
                'peer_monitor_id,peer_monitor_name,status,last_error,update_time',
                (peer_monitor_id, peer_monitor_name, 'handshake_ok', '', self._now())
            )
        monitor = self._localMonitor()
        return jh.returnJson(True, 'ok', {
            'monitor_id': monitor.get('monitor_id'),
            'monitor_name': monitor.get('monitor_name'),
            'sync_version': self.MONITOR_SYNC_VERSION,
            'sync_type': payload.get('sync_type') or self.DEFAULT_SYNC_TYPE
        })

    def publicMonitorSyncPull(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        ok, msg, sync_config = self._verifyMonitorSyncRequest(payload)
        if not ok:
            return jh.returnJson(False, msg)
        sync_type = self._normalizeSyncType(payload.get('sync_type') or sync_config.get('sync_type'))
        if not sync_type:
            return jh.returnJson(False, '同步类型暂只支持 ha_management')
        after_seq = max(0, self._safeInt(payload.get('after_seq'), 0))
        limit = max(1, min(200, self._safeInt(payload.get('limit'), 100)))
        local_monitor = self._localMonitor()
        rows = jh.M('ha_sync_event').where('sync_type=? AND seq>? AND source_monitor_id!=?', (sync_type, after_seq, payload.get('monitor_id') or '')).field(self.sync_event_fields).order('seq asc,id asc').limit(str(limit)).select()
        if not isinstance(rows, list):
            rows = []
        events = []
        max_seq = after_seq
        for row in rows:
            max_seq = max(max_seq, self._safeInt(row.get('seq'), 0))
            payload_json = self._jsonLoads(row.get('payload_json'), {})
            events.append({
                'event_id': row.get('event_id') or '',
                'sync_type': row.get('sync_type') or '',
                'source_monitor_id': row.get('source_monitor_id') or '',
                'source_monitor_name': row.get('source_monitor_name') or '',
                'event_type': row.get('event_type') or '',
                'object_key': row.get('object_key') or '',
                'payload': payload_json,
                'seq': self._safeInt(row.get('seq'), 0),
                'addtime': row.get('addtime') or ''
            })
        return jh.returnJson(True, 'ok', {
            'monitor_id': local_monitor.get('monitor_id'),
            'monitor_name': local_monitor.get('monitor_name'),
            'sync_type': sync_type,
            'after_seq': after_seq,
            'max_seq': max_seq,
            'has_more': len(events) >= limit,
            'events': events
        })

    def publicMonitorSyncAck(self):
        self.ensureHaSchema()
        payload = self._bodyJson()
        ok, msg, sync_config = self._verifyMonitorSyncRequest(payload)
        if not ok:
            return jh.returnJson(False, msg)
        return jh.returnJson(True, 'ok', {
            'monitor_id': self._localMonitor().get('monitor_id'),
            'acked_seq': self._safeInt(payload.get('acked_seq'), 0),
            'sync_type': payload.get('sync_type') or sync_config.get('sync_type') or self.DEFAULT_SYNC_TYPE
        })

    def _cursorForConfig(self, sync_config, sync_type=''):
        sync_id = sync_config.get('sync_id')
        sync_type = self._normalizeSyncType(sync_type or self.DEFAULT_SYNC_TYPE) or self.DEFAULT_SYNC_TYPE
        row = jh.M('ha_sync_cursor').where('sync_id=? AND sync_type=?', (sync_id, sync_type)).field('id,sync_id,sync_type,peer_monitor_id,last_seq,last_event_id,last_sync_at,last_error,addtime,update_time').find()
        if isinstance(row, dict) and row.get('id'):
            return row
        now = self._now()
        jh.M('ha_sync_cursor').add('sync_id,sync_type,peer_monitor_id,last_seq,last_event_id,addtime,update_time', (sync_id, sync_type, sync_config.get('peer_monitor_id') or '', 0, '', now, now))
        return jh.M('ha_sync_cursor').where('sync_id=? AND sync_type=?', (sync_id, sync_type)).field('id,sync_id,sync_type,peer_monitor_id,last_seq,last_event_id,last_sync_at,last_error,addtime,update_time').find()

    def runMonitorSync(self, sync_id=''):
        self.ensureHaSchema()
        if sync_id:
            rows = [self._getSyncConfig(sync_id)]
        else:
            rows = jh.M('ha_sync_config').where('enabled=?', (1,)).field(self.sync_config_fields).select()
        if not isinstance(rows, list):
            rows = []
        rows = [row for row in rows if isinstance(row, dict) and row.get('sync_id')]
        results = []
        ok_count = 0
        for sync_config in rows:
            if self._safeInt(sync_config.get('enabled'), 0) != 1:
                continue
            for sync_type in self._syncConfigTypes(sync_config):
                item = self._runOneMonitorSync(sync_config, sync_type)
                results.append(item)
                if item.get('status') == 'ok':
                    ok_count += 1
        status = 'ok' if ok_count == len(results) else ('partial' if ok_count > 0 else 'failed')
        if not results:
            status = 'ok'
        return {'status': status, 'msg': '同步完成', 'items': results}

    def _runOneMonitorSync(self, sync_config, sync_type=''):
        sync_id = sync_config.get('sync_id')
        sync_type = self._normalizeSyncType(sync_type or self.DEFAULT_SYNC_TYPE) or self.DEFAULT_SYNC_TYPE
        cursor = self._cursorForConfig(sync_config, sync_type)
        after_seq = self._safeInt(cursor.get('last_seq'), 0)
        monitor = self._localMonitor()
        payload = {
            'sync_id': sync_id,
            'sync_type': sync_type,
            'monitor_id': monitor.get('monitor_id'),
            'monitor_name': monitor.get('monitor_name'),
            'after_seq': after_seq,
            'limit': 100
        }
        try:
            result = self._postSyncJson(sync_config, '/pub/ha_monitor_sync_pull', payload, timeout=15)
            if not result.get('status'):
                raise Exception(result.get('msg') or 'pull failed')
            data = result.get('data') or {}
            events = data.get('events') if isinstance(data.get('events'), list) else []
            max_seq = after_seq
            for event in events:
                self._applySyncEvent(sync_config, event)
                max_seq = max(max_seq, self._safeInt(event.get('seq'), 0))
            now = self._now()
            jh.M('ha_sync_cursor').where('sync_id=? AND sync_type=?', (sync_id, sync_type)).save(
                'peer_monitor_id,last_seq,last_event_id,last_sync_at,last_error,update_time',
                (data.get('monitor_id') or sync_config.get('peer_monitor_id') or '', max_seq, events[-1].get('event_id') if events else cursor.get('last_event_id') or '', now, '', now)
            )
            jh.M('ha_sync_config').where('sync_id=?', (sync_id,)).save(
                'peer_monitor_id,peer_monitor_name,last_sync_at,last_error,status,update_time',
                (data.get('monitor_id') or sync_config.get('peer_monitor_id') or '', data.get('monitor_name') or sync_config.get('peer_monitor_name') or '', now, '', 'ok', now)
            )
            if events:
                try:
                    self._postSyncJson(sync_config, '/pub/ha_monitor_sync_ack', {
                        'sync_id': sync_id,
                        'sync_type': sync_type,
                        'monitor_id': monitor.get('monitor_id'),
                        'monitor_name': monitor.get('monitor_name'),
                        'acked_seq': max_seq
                    }, timeout=8)
                except Exception:
                    pass
            self._appendSyncLog('sync ok sync_id={0} type={1} events={2} seq={3}->{4}'.format(sync_id, sync_type, len(events), after_seq, max_seq))
            return {'sync_id': sync_id, 'status': 'ok', 'count': len(events), 'last_seq': max_seq}
        except Exception as e:
            msg = str(e)
            now = self._now()
            jh.M('ha_sync_cursor').where('sync_id=? AND sync_type=?', (sync_id, sync_type)).save('last_error,update_time', (msg, now))
            jh.M('ha_sync_config').where('sync_id=?', (sync_id,)).save('last_error,status,update_time', (msg, 'failed', now))
            self._appendSyncLog('sync failed sync_id={0} type={1} after_seq={2} error={3}'.format(sync_id, sync_type, after_seq, msg))
            return {'sync_id': sync_id, 'status': 'failed', 'error': msg, 'last_seq': after_seq}

    def _applySyncEvent(self, sync_config, event):
        event_id = self._safeText(event.get('event_id'), 128)
        if not event_id:
            raise Exception('同步事件缺少 event_id')
        exists = jh.M('ha_sync_applied').where('event_id=?', (event_id,)).field('id').find()
        if isinstance(exists, dict) and exists.get('id'):
            return False
        payload = event.get('payload') if isinstance(event.get('payload'), dict) else {}
        event_type = self._safeText(event.get('event_type'), 64)
        if event_type == 'ha_pair':
            self._applySyncPair(payload, event)
        elif event_type == 'ha_host_state':
            self._applySyncHostState(payload, event)
        elif event_type == 'ha_switch_run':
            self._applySyncSwitchRun(payload, event)
        elif event_type == 'ha_switch_event':
            self._applySyncSwitchEvent(payload, event)
        elif event_type == 'ha_alert_event':
            self._applySyncAlertEvent(payload, event)
        else:
            raise Exception('不支持的同步事件类型: ' + event_type)
        jh.M('ha_sync_applied').add('event_id,sync_id,sync_type,source_monitor_id,object_key,status,error_msg,addtime', (event_id, sync_config.get('sync_id'), event.get('sync_type') or self.DEFAULT_SYNC_TYPE, event.get('source_monitor_id') or '', event.get('object_key') or '', 'success', '', self._now()))
        return True

    def _sourceMeta(self, event):
        return event.get('source_monitor_id') or '', self._now()

    def _applySyncPair(self, payload, event):
        pair = payload.get('pair') if isinstance(payload.get('pair'), dict) else payload
        pair_id = self._safeText(pair.get('pair_id'), 128)
        if not pair_id:
            return
        source_monitor_id, sync_update_at = self._sourceMeta(event)
        now = self._now()
        fields = {
            'pair_name': self._safeText(pair.get('pair_name'), 128),
            'desired_master_host_id': self._safeText(pair.get('desired_master_host_id'), 128),
            'actual_master_host_id': self._safeText(pair.get('actual_master_host_id'), 128),
            'status': self._safeText(pair.get('status') or 'unknown', 32),
            'status_text': self._safeText(pair.get('status_text'), 512),
            'last_report_at': self._safeText(pair.get('last_report_at'), 32),
            'current_switch_run_id': self._safeText(pair.get('current_switch_run_id'), 128),
            'callback_url': self._safeText(pair.get('callback_url'), 512),
            'callback_enabled': self._safeInt(pair.get('callback_enabled'), 0),
            'callback_status': self._safeText(pair.get('callback_status'), 64),
            'api_secret': self._safeText(pair.get('api_secret'), 128),
            'source_monitor_id': source_monitor_id,
            'sync_update_at': sync_update_at,
            'update_time': now
        }
        exists = self._getPair(pair_id)
        if exists:
            if self._reportTimestamp(fields) < self._reportTimestamp(exists):
                return
            keys = ','.join(fields.keys())
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save(keys, tuple(fields.values()))
        else:
            sort_id = self._nextPairSortId()
            jh.M('ha_pair').add(
                'pair_id,pair_name,desired_master_host_id,actual_master_host_id,status,status_text,last_report_at,current_switch_run_id,callback_url,callback_enabled,callback_status,api_secret,sort_id,source_monitor_id,sync_update_at,addtime,update_time',
                (pair_id, fields['pair_name'], fields['desired_master_host_id'], fields['actual_master_host_id'], fields['status'], fields['status_text'], fields['last_report_at'], fields['current_switch_run_id'], fields['callback_url'], fields['callback_enabled'], fields['callback_status'], fields['api_secret'] or self.DEFAULT_SECRET, sort_id, source_monitor_id, sync_update_at, now, now)
            )

    def _applySyncHostState(self, payload, event):
        state = payload.get('state') if isinstance(payload.get('state'), dict) else payload
        pair_id = self._safeText(state.get('pair_id'), 128)
        host_id = self._safeText(state.get('host_id'), 128)
        if not pair_id or not host_id:
            return
        source_monitor_id, sync_update_at = self._sourceMeta(event)
        local_monitor_id = self._localMonitor().get('monitor_id') or ''
        exists = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).field(self.state_fields).find()
        if isinstance(exists, dict) and exists.get('id'):
            new_ts = self._reportTimestamp(state)
            old_ts = self._reportTimestamp(exists)
            if new_ts < old_ts:
                return
            if new_ts == old_ts and exists.get('collect_method') == 'local' and state.get('collect_method') != 'local':
                return
        now = self._now()
        site_scope = self._safeText(state.get('site_scope') or '', 32)
        if isinstance(exists, dict) and exists.get('id'):
            exists_source_monitor_id = exists.get('source_monitor_id') or local_monitor_id
            if exists.get('site_scope') == 'local' or (exists_source_monitor_id == local_monitor_id and exists.get('collect_method') == 'local'):
                site_scope = 'local'
            elif source_monitor_id and source_monitor_id != local_monitor_id:
                site_scope = 'remote'
        elif source_monitor_id and source_monitor_id != local_monitor_id:
            site_scope = 'remote'
        values = (
            self._safeText(state.get('host_name') or state.get('name') or host_id, 128),
            self._safeText(state.get('host_ip') or state.get('ip'), 64),
            self._safeText(state.get('role') or 'unknown', 32),
            self._safeText(state.get('online_status') or state.get('online') or 'unknown', 32),
            self._safeText(state.get('health_status') or 'unknown', 32),
            self._safeText(state.get('collect_status') or 'unknown', 32),
            self._safeText(state.get('collect_method') or '', 32),
            self._safeText(state.get('report_host_id') or '', 128),
            site_scope,
            state.get('health_detail') if isinstance(state.get('health_detail'), str) else json.dumps(state.get('health_detail') or {}, ensure_ascii=False),
            self._safeText(state.get('switch_run_id') or '', 128),
            self._safeText(state.get('switch_phase') or '', 64),
            self._safeText(state.get('switch_status') or '', 64),
            self._safeText(state.get('current_step') or '', 255),
            self._safeText(state.get('next_step') or '', 255),
            self._safeText(state.get('last_error') or '', 512),
            self._safeText(state.get('log_path') or '', 512),
            self._safeText(state.get('last_report_at') or now, 32),
            self._safeText(state.get('report_batch_id') or '', 128),
            source_monitor_id,
            sync_update_at,
            now
        )
        if isinstance(exists, dict) and exists.get('id'):
            jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).save(
                'host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,current_step,next_step,last_error,log_path,last_report_at,report_batch_id,source_monitor_id,sync_update_at,update_time', values
            )
        else:
            jh.M('ha_host_state').add(
                'pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,current_step,next_step,last_error,log_path,last_report_at,report_batch_id,source_monitor_id,sync_update_at,addtime,update_time',
                (pair_id, host_id) + values[:-1] + (now, values[-1])
            )

    def _applySyncSwitchRun(self, payload, event):
        run = payload.get('run') if isinstance(payload.get('run'), dict) else payload
        switch_run_id = self._safeText(run.get('switch_run_id'), 128)
        if not switch_run_id:
            return
        pair_id = self._safeText(run.get('pair_id'), 128)
        exists = self._getRun(switch_run_id)
        source_monitor_id, sync_update_at = self._sourceMeta(event)
        now = self._now()
        origin_monitor_id = self._safeText(run.get('origin_monitor_id') or source_monitor_id, 128)
        execution_monitor_id = self._safeText(run.get('execution_monitor_id') or origin_monitor_id, 128)
        active = jh.M('ha_switch_run').where('pair_id=? AND switch_run_id!=? AND status IN (?,?,?,?,?,?,?)', (pair_id, switch_run_id, 'pending', 'pending_prepare', 'pending_finalize', 'pending_online', 'running', 'waiting_retry', 'prepare_success')).field('switch_run_id,status').find() if pair_id else {}
        dispatchable = self._safeInt(run.get('dispatchable'), 1)
        dispatch_reason = self._safeText(run.get('dispatch_reason') or '', 512)
        status = self._safeText(run.get('status') or 'pending', 64)
        if not exists and isinstance(active, dict) and active.get('switch_run_id'):
            dispatchable = 0
            status = 'conflict'
            dispatch_reason = '同步任务与本地未完成切换任务冲突: {0}'.format(active.get('switch_run_id'))
        values = (
            pair_id,
            self._safeText(run.get('old_master_host_id'), 128),
            self._safeText(run.get('new_master_host_id'), 128),
            self._safeText(run.get('desired_master_host_id'), 128),
            run.get('options_json') if isinstance(run.get('options_json'), str) else json.dumps(run.get('options') or {}, ensure_ascii=False),
            status,
            self._safeText(run.get('current_phase'), 64),
            self._safeText(run.get('current_step'), 255),
            self._safeText(run.get('next_step'), 255),
            self._safeText(run.get('last_error'), 1000),
            run.get('step_summary') if isinstance(run.get('step_summary'), str) else json.dumps(run.get('step_summary') or [], ensure_ascii=False),
            self._safeText(run.get('log_path') or self._monthLogPath(switch_run_id), 512),
            self._safeText(run.get('callback_status'), 64),
            self._safeText(run.get('callback_error'), 1000),
            origin_monitor_id,
            execution_monitor_id,
            self._safeText(run.get('claimed_by_host_id'), 128),
            self._safeText(run.get('claim_token'), 128),
            self._safeInt(run.get('claim_expire_at'), 0),
            self._safeText(run.get('sync_status') or 'synced', 64),
            dispatchable,
            dispatch_reason,
            source_monitor_id,
            sync_update_at,
            self._safeText(run.get('finish_time'), 32),
            now
        )
        if exists:
            jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save(
                'pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,options_json,status,current_phase,current_step,next_step,last_error,step_summary,log_path,callback_status,callback_error,origin_monitor_id,execution_monitor_id,claimed_by_host_id,claim_token,claim_expire_at,sync_status,dispatchable,dispatch_reason,source_monitor_id,sync_update_at,finish_time,update_time', values
            )
        else:
            jh.M('ha_switch_run').add(
                'switch_run_id,pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,options_json,status,current_phase,current_step,next_step,last_error,step_summary,log_path,callback_status,callback_error,origin_monitor_id,execution_monitor_id,claimed_by_host_id,claim_token,claim_expire_at,sync_status,dispatchable,dispatch_reason,source_monitor_id,sync_update_at,finish_time,addtime,update_time',
                (switch_run_id,) + values + (now,)
            )

    def _applySyncSwitchEvent(self, payload, event):
        row = payload.get('event') if isinstance(payload.get('event'), dict) else payload
        event_id = self._safeText(row.get('event_id') or event.get('event_id'), 128)
        switch_run_id = self._safeText(row.get('switch_run_id'), 128)
        origin_host_id = self._safeText(row.get('origin_host_id') or row.get('host_id'), 128)
        seq = self._safeInt(row.get('seq'), 0)
        if event_id:
            exists = jh.M('ha_switch_event').where('event_id=?', (event_id,)).field('id').find()
        else:
            exists = jh.M('ha_switch_event').where('switch_run_id=? AND origin_host_id=? AND seq=?', (switch_run_id, origin_host_id, seq)).field('id').find()
            event_id = '{0}:{1}:{2}'.format(switch_run_id, origin_host_id, seq)
        if isinstance(exists, dict) and exists.get('id'):
            return
        now = self._safeText(row.get('addtime'), 32) or self._now()
        jh.M('ha_switch_event').add(
            'switch_run_id,pair_id,event_id,origin_host_id,report_host_id,collect_method,seq,phase,step,status,log_text,addtime',
            (switch_run_id, self._safeText(row.get('pair_id'), 128), event_id, origin_host_id, self._safeText(row.get('report_host_id'), 128), self._safeText(row.get('collect_method'), 32), seq, self._safeText(row.get('phase'), 64), self._safeText(row.get('step'), 255), self._safeText(row.get('status'), 64), self._safeText(row.get('log_text') or row.get('message'), 4000), now)
        )
        run = self._getRun(switch_run_id)
        if run:
            line = '[{0}] [{1}] [{2}] [{3}] {4}'.format(now, origin_host_id or 'sync', row.get('phase') or 'event', row.get('status') or 'info', row.get('log_text') or row.get('step') or '')
            self._appendLog(run.get('log_path') or self._monthLogPath(switch_run_id), line)

    def _applySyncAlertEvent(self, payload, event):
        row = payload.get('alert') if isinstance(payload.get('alert'), dict) else payload
        event_id = self._safeText(row.get('event_id') or event.get('event_id'), 128)
        if not event_id:
            return
        exists = jh.M('ha_alert_event').where('event_id=?', (event_id,)).field('id').find()
        if isinstance(exists, dict) and exists.get('id'):
            return
        alerts = row.get('alerts') if isinstance(row.get('alerts'), list) else self._jsonLoads(row.get('alerts_json'), [])
        jh.M('ha_alert_event').add(
            'pair_id,event_id,event_type,alert_key,alert_type,alert_level,status,title,message,sent_by_host_id,report_host_id,notifier_mode,alerts_json,addtime',
            (self._safeText(row.get('pair_id'), 128), event_id, self._safeText(row.get('event_type'), 64), self._safeText(row.get('alert_key'), 255), self._safeText(row.get('alert_type'), 64), self._safeText(row.get('alert_level'), 32), self._safeText(row.get('status'), 32), self._safeText(row.get('title'), 255), self._safeText(row.get('message'), 4000), self._safeText(row.get('sent_by_host_id') or row.get('host_id'), 128), self._safeText(row.get('report_host_id') or row.get('host_id'), 128), self._safeText(row.get('notifier_mode'), 64), json.dumps(alerts, ensure_ascii=False), self._safeText(row.get('addtime'), 32) or self._now())
        )

    def _getPair(self, pair_id):
        self.ensureHaSchema()
        row = jh.M('ha_pair').where('pair_id=?', (pair_id,)).field(self.pair_fields).find()
        return row if isinstance(row, dict) else {}

    def _getStates(self, pair_id):
        rows = jh.M('ha_host_state').where('pair_id=?', (pair_id,)).field(self.state_fields).select()
        return rows if isinstance(rows, list) else []

    def _getEvents(self, switch_run_id, limit=500):
        if not switch_run_id:
            return []
        rows = jh.M('ha_switch_event').where('switch_run_id=?', (switch_run_id,)).field(
            'id,switch_run_id,pair_id,event_id,origin_host_id,report_host_id,collect_method,seq,phase,step,status,log_text,addtime'
        ).order('seq asc,id asc').limit(str(max(1, int(limit)))).select()
        return rows if isinstance(rows, list) else []

    def _normalizeCheckStatus(self, status):
        status = self._safeText(status, 32).lower()
        if status in ('ok', 'success', 'normal', 'pass', 'passed'):
            return 'pass'
        if status in ('warn', 'warning'):
            return 'warning'
        if status in ('fail', 'failed', 'error', 'danger'):
            return 'failed'
        if status in ('skip', 'skipped'):
            return 'skipped'
        return status or 'unknown'

    def _normalizeScriptChecks(self, detail):
        if not isinstance(detail, dict):
            return []
        raw = detail.get('script_checks')
        if raw is None:
            raw = detail.get('checks')
        if isinstance(raw, dict):
            items = []
            for group, checks in raw.items():
                if isinstance(checks, list):
                    for check in checks:
                        if isinstance(check, dict):
                            item = dict(check)
                            item.setdefault('group', group)
                            items.append(item)
                elif isinstance(checks, dict):
                    item = dict(checks)
                    item.setdefault('group', group)
                    items.append(item)
            raw = items
        if not isinstance(raw, list):
            return []
        result = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = self._safeText(item.get('name') or item.get('title') or item.get('key'), 128)
            if not name:
                continue
            result.append({
                'group': self._safeText(item.get('group') or item.get('category') or '其他', 64) or '其他',
                'name': name,
                'expected': self._safeText(item.get('expected') or item.get('expect') or '', 255),
                'actual': self._safeText(item.get('actual') or item.get('value') or item.get('text') or '', 255),
                'status': self._normalizeCheckStatus(item.get('status')),
                'message': self._safeText(item.get('message') or item.get('msg') or item.get('summary') or '', 512)
            })
        return result

    def _normalizeRun(self, run):
        if not isinstance(run, dict) or not run.get('switch_run_id'):
            return {}
        options = self._jsonLoads(run.get('options_json'), {})
        summary = self._jsonLoads(run.get('step_summary'), [])
        return {
            'switch_run_id': run.get('switch_run_id') or '',
            'pair_id': run.get('pair_id') or '',
            'old_master_host_id': run.get('old_master_host_id') or '',
            'new_master_host_id': run.get('new_master_host_id') or '',
            'desired_master_host_id': run.get('desired_master_host_id') or '',
            'options': options if isinstance(options, dict) else {},
            'status': run.get('status') or '',
            'current_phase': run.get('current_phase') or '',
            'current_step': run.get('current_step') or '',
            'next_step': run.get('next_step') or '',
            'last_error': run.get('last_error') or '',
            'step_summary': summary if isinstance(summary, list) else [],
            'log_path': run.get('log_path') or '',
            'callback_status': run.get('callback_status') or '',
            'callback_error': run.get('callback_error') or '',
            'origin_monitor_id': run.get('origin_monitor_id') or '',
            'execution_monitor_id': run.get('execution_monitor_id') or '',
            'claimed_by_host_id': run.get('claimed_by_host_id') or '',
            'claim_token': run.get('claim_token') or '',
            'claim_expire_at': self._safeInt(run.get('claim_expire_at'), 0),
            'sync_status': run.get('sync_status') or '',
            'dispatchable': self._safeInt(run.get('dispatchable'), 1),
            'dispatch_reason': run.get('dispatch_reason') or '',
            'source_monitor_id': run.get('source_monitor_id') or '',
            'sync_update_at': run.get('sync_update_at') or '',
            'addtime': run.get('addtime') or '',
            'update_time': run.get('update_time') or '',
            'finish_time': run.get('finish_time') or ''
        }

    def _getRuns(self, pair_id, page=1, page_size=20):
        if not pair_id:
            return {'list': [], 'page': 1, 'page_size': page_size, 'total': 0, 'total_page': 1}
        page = max(1, self._safeInt(page, 1))
        page_size = max(1, min(100, self._safeInt(page_size, 20)))
        total = jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).count()
        total_page = max(1, int((total + page_size - 1) / page_size))
        if page > total_page:
            page = total_page
        offset = (page - 1) * page_size
        rows = jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).field(self.run_fields).order('id desc').limit('{0},{1}'.format(offset, page_size)).select()
        if not isinstance(rows, list):
            rows = []
        return {'list': [self._normalizeRun(row) for row in rows], 'page': page, 'page_size': page_size, 'total': total, 'total_page': total_page}

    def _normalizeEvent(self, row):
        return {
            'event_id': row.get('event_id') or '',
            'switch_run_id': row.get('switch_run_id') or '',
            'pair_id': row.get('pair_id') or '',
            'origin_host_id': row.get('origin_host_id') or '',
            'report_host_id': row.get('report_host_id') or '',
            'collect_method': row.get('collect_method') or '',
            'seq': self._safeInt(row.get('seq'), 0),
            'phase': row.get('phase') or '',
            'step': row.get('step') or '',
            'status': row.get('status') or '',
            'log_text': row.get('log_text') or '',
            'addtime': row.get('addtime') or ''
        }

    def _normalizeAlertEvent(self, row):
        return {
            'id': row.get('id') or '',
            'pair_id': row.get('pair_id') or '',
            'event_id': row.get('event_id') or '',
            'event_type': row.get('event_type') or '',
            'alert_key': row.get('alert_key') or '',
            'alert_type': row.get('alert_type') or '',
            'alert_level': row.get('alert_level') or '',
            'status': row.get('status') or '',
            'title': row.get('title') or '',
            'message': row.get('message') or '',
            'sent_by_host_id': row.get('sent_by_host_id') or '',
            'report_host_id': row.get('report_host_id') or '',
            'notifier_mode': row.get('notifier_mode') or '',
            'alerts': self._jsonLoads(row.get('alerts_json'), []),
            'addtime': row.get('addtime') or ''
        }

    def _getAlertEvents(self, pair_id, limit=20):
        if not pair_id:
            return []
        rows = jh.M('ha_alert_event').where('pair_id=?', (pair_id,)).field(self.alert_event_fields).order('id desc').limit(str(max(1, min(100, int(limit))))).select()
        return [self._normalizeAlertEvent(row) for row in rows] if isinstance(rows, list) else []

    def _isPlaceholderHost(self, row):
        host_id = row.get('host_id') or ''
        host_name = row.get('host_name') or ''
        collect_method = row.get('collect_method') or ''
        return (host_id.startswith('H_PEER_') or host_name.startswith('对端 ')) and collect_method == ''

    def _hostStateScore(self, row):
        detail = self._jsonLoads(row.get('health_detail'), {})
        score = 0
        if row.get('online_status') == 'online':
            score += 100
        if row.get('collect_status') == 'success':
            score += 50
        if row.get('collect_method') == 'local':
            score += 30
        elif row.get('collect_method') == 'ssh_peer':
            score += 20
        if isinstance(detail, dict) and detail:
            score += 10
        if isinstance(detail, dict) and detail.get('script_checks'):
            score += 20
        if self._isPlaceholderHost(row):
            score -= 100
        return score

    def _reportTimestamp(self, row):
        last_report_at = row.get('last_report_at') or row.get('update_time') or row.get('addtime') or ''
        try:
            return int(time.mktime(time.strptime(last_report_at, '%Y-%m-%d %H:%M:%S')))
        except Exception:
            return 0

    def _selectDisplayState(self, rows):
        if not rows:
            return {}
        latest_ts = max([self._reportTimestamp(row) for row in rows])
        candidates = [row for row in rows if self._reportTimestamp(row) == latest_ts]
        if not candidates:
            candidates = rows
        selected = candidates[0]
        for row in candidates[1:]:
            row_score = self._hostStateScore(row)
            selected_score = self._hostStateScore(selected)
            if row_score > selected_score or (row_score == selected_score and row.get('collect_method') == 'local' and selected.get('collect_method') != 'local'):
                selected = row
        return selected

    def _displayStates(self, states):
        local_monitor_id = self._localMonitor().get('monitor_id') or ''
        latest_batch_by_source = {}
        for row in states:
            batch_id = row.get('report_batch_id') or ''
            if not batch_id:
                continue
            source_key = row.get('source_monitor_id') or local_monitor_id or 'local'
            batch_ts = self._reportTimestamp(row)
            current = latest_batch_by_source.get(source_key) or {'batch_id': '', 'ts': -1}
            if batch_ts > current.get('ts', -1):
                latest_batch_by_source[source_key] = {'batch_id': batch_id, 'ts': batch_ts}
        if latest_batch_by_source:
            filtered = []
            for row in states:
                batch_id = row.get('report_batch_id') or ''
                if not batch_id:
                    filtered.append(row)
                    continue
                source_key = row.get('source_monitor_id') or local_monitor_id or 'local'
                latest = latest_batch_by_source.get(source_key) or {}
                if batch_id == latest.get('batch_id'):
                    filtered.append(row)
            states = filtered
        local_host_key_by_ip = {}
        local_host_ids_by_ip = {}
        local_host_ids = set()
        real_host_key_by_ip = {}
        for row in states:
            if row.get('collect_method') == 'local' and row.get('host_id'):
                local_host_ids.add(row.get('host_id'))
            if row.get('collect_method') == 'local' and row.get('host_ip') and row.get('host_id') and row.get('host_ip') not in local_host_key_by_ip:
                local_host_key_by_ip[row.get('host_ip')] = row.get('host_id')
            if row.get('collect_method') == 'local' and row.get('host_ip') and row.get('host_id'):
                local_host_ids_by_ip.setdefault(row.get('host_ip'), []).append(row.get('host_id'))
            if not self._isPlaceholderHost(row) and row.get('host_ip') and row.get('host_id') and row.get('host_ip') not in real_host_key_by_ip:
                real_host_key_by_ip[row.get('host_ip')] = row.get('host_id')
        grouped = {}
        for row in states:
            detail = self._jsonLoads(row.get('health_detail'), {})
            source_host_id = detail.get('_source_host_id') if isinstance(detail, dict) else ''
            if row.get('host_id', '').startswith('H_ALIAS_') and source_host_id:
                key = source_host_id
            elif row.get('collect_method') == 'ssh_peer' and (source_host_id or row.get('host_id')) in local_host_ids and row.get('host_ip') in local_host_key_by_ip:
                key = local_host_key_by_ip.get(row.get('host_ip'))
            elif self._isPlaceholderHost(row) and row.get('host_ip'):
                key = real_host_key_by_ip.get(row.get('host_ip')) or ('placeholder_ip:' + row.get('host_ip'))
            else:
                key = row.get('host_id') or row.get('host_ip') or str(row.get('id'))
            grouped.setdefault(key, []).append(row)
        result = []
        for rows in grouped.values():
            selected = self._selectDisplayState(rows)
            item = dict(selected)
            item_source_monitor_id = item.get('source_monitor_id') or local_monitor_id
            if item.get('collect_method') == 'ssh_peer' and item_source_monitor_id == local_monitor_id:
                item['site_scope'] = 'remote'
            if item.get('source_monitor_id') and item.get('source_monitor_id') != local_monitor_id and item.get('site_scope') != 'local':
                item['site_scope'] = 'remote'
            if item.get('collect_method') == 'ssh_peer' and item.get('host_id') not in local_host_ids and item.get('site_scope') != 'local':
                item['site_scope'] = 'remote'
            alias_ids = []
            alias_names = []
            alias_roles = []
            alias_collect_methods = []
            for row in rows:
                if row.get('host_id') and row.get('host_id') not in alias_ids:
                    alias_ids.append(row.get('host_id'))
                detail = self._jsonLoads(row.get('health_detail'), {})
                source_host_id = detail.get('_source_host_id') if isinstance(detail, dict) else ''
                if source_host_id and source_host_id not in alias_ids:
                    alias_ids.append(source_host_id)
                if row.get('host_name') and row.get('host_name') not in alias_names:
                    alias_names.append(row.get('host_name'))
                if row.get('role') and row.get('role') not in alias_roles:
                    alias_roles.append(row.get('role'))
                if row.get('collect_method') and row.get('collect_method') not in alias_collect_methods:
                    alias_collect_methods.append(row.get('collect_method'))
            item['_alias_host_ids'] = alias_ids
            item['_alias_host_names'] = alias_names
            item['_alias_roles'] = alias_roles
            item['_alias_collect_methods'] = alias_collect_methods
            result.append(item)
        return result

    def _displayHostName(self, row, pair=None):
        name = row.get('host_name') or row.get('host_id') or ''
        ip = row.get('host_ip') or ''
        pair_name = pair.get('pair_name') if isinstance(pair, dict) else ''
        if pair_name and ip and (not name or name.startswith('对端 ')):
            last = ip.split('.')[-1] if '.' in ip else ip
            return pair_name + '-' + last
        return name

    def _normalizeHost(self, row, pair=None):
        detail = self._jsonLoads(row.get('health_detail'), {})
        failover = detail.get('ha_failover') if isinstance(detail, dict) else {}
        if not isinstance(failover, dict):
            failover = {}
        role = row.get('role') or 'unknown'
        script_checks = self._normalizeScriptChecks(detail)
        display_name = self._displayHostName(row, pair)
        local_monitor_id = self._localMonitor().get('monitor_id') or ''
        source_monitor_id = row.get('source_monitor_id') or ''
        data_source = 'sync' if source_monitor_id and source_monitor_id != local_monitor_id else 'local'
        return {
            'host_id': row.get('host_id') or '',
            'host_alias_ids': row.get('_alias_host_ids') or [row.get('host_id') or ''],
            'host_alias_names': row.get('_alias_host_names') or [row.get('host_name') or row.get('host_id') or ''],
            'host_alias_roles': row.get('_alias_roles') or [role],
            'host_alias_collect_methods': row.get('_alias_collect_methods') or ([row.get('collect_method')] if row.get('collect_method') else []),
            'name': display_name,
            'host_name': display_name,
            'raw_host_name': row.get('host_name') or row.get('host_id') or '',
            'ip': row.get('host_ip') or '',
            'host_ip': row.get('host_ip') or '',
            'role': role,
            'online': row.get('online_status') or 'unknown',
            'online_status': row.get('online_status') or 'unknown',
            'health_status': row.get('health_status') or 'unknown',
            'collect_status': row.get('collect_status') or 'unknown',
            'collect_method': row.get('collect_method') or '',
            'report_host_id': row.get('report_host_id') or '',
            'site_scope': row.get('site_scope') or '',
            'health_detail': detail,
            'failover': failover,
            'mode': failover.get('mode') or 'normal',
            'pending_switch_required': bool(failover.get('pending_switch_required')),
            'pending_switch_host_id': failover.get('pending_switch_host_id') or '',
            'pending_switch_role': failover.get('pending_switch_role') or '',
            'recovery_status': failover.get('recovery_status') or '',
            'script_checks': script_checks,
            'switch_run_id': row.get('switch_run_id') or '',
            'switch_phase': row.get('switch_phase') or '',
            'switch_status': row.get('switch_status') or '',
            'current_step': row.get('current_step') or '',
            'next_step': row.get('next_step') or '',
            'last_error': row.get('last_error') or '',
            'log_path': row.get('log_path') or '',
            'last_report_at': row.get('last_report_at') or '',
            'source_monitor_id': source_monitor_id,
            'sync_update_at': row.get('sync_update_at') or '',
            'data_source': data_source,
            'data_source_text': '江湖云监控同步' if data_source == 'sync' else '本地上报'
        }

    def _stateFailover(self, row):
        detail = self._jsonLoads(row.get('health_detail'), {})
        failover = detail.get('ha_failover') if isinstance(detail, dict) else {}
        return failover if isinstance(failover, dict) else {}

    def _isRecoveryGuardState(self, row):
        return self._stateFailover(row).get('recovery_status') == 'recovery_guard'

    def _effectiveMasterStates(self, states):
        active = [x for x in states if x.get('role') == 'master' and not self._isRecoveryGuardState(x)]
        return active if active else [x for x in states if x.get('role') == 'master']

    def _actualMasterHostId(self, states):
        for state in self._effectiveMasterStates(states):
            if state.get('role') == 'master':
                return state.get('host_id') or ''
        return ''

    def _pendingSwitchTargetText(self, failover, states):
        target_id = failover.get('pending_switch_host_id') or ''
        if not target_id:
            return '对端'
        for state in states:
            alias_ids = state.get('_alias_host_ids') or []
            if state.get('host_id') not in alias_ids:
                alias_ids.append(state.get('host_id'))
            if target_id in alias_ids:
                return self._displayHostName(state) or state.get('host_ip') or target_id
        return target_id

    def deriveStatus(self, pair, states):
        current_run_id = pair.get('current_switch_run_id') or ''
        if current_run_id:
            running = self._getRun(current_run_id)
            if isinstance(running, dict) and running.get('status') == 'prepare_success':
                return 'normal', running.get('next_step') or '预上线完成，等待正式上线'
            if isinstance(running, dict) and running.get('status') in ('pending', 'pending_prepare', 'pending_finalize', 'pending_online', 'running', 'waiting_retry'):
                return 'switching', running.get('current_step') or running.get('current_phase') or '切换中'
        if not states:
            return 'unknown', '等待插件上报'
        masters = self._effectiveMasterStates(states)
        online = dict([(x.get('host_id'), x.get('online_status')) for x in states])
        warnings = []
        degraded = []
        danger = []
        if len(masters) > 1:
            danger.append('双主异常')
        if len(masters) == 0:
            danger.append('双备或无主异常')
        for item in states:
            last_report_at = item.get('last_report_at') or ''
            if last_report_at:
                try:
                    ts = time.mktime(time.strptime(last_report_at, '%Y-%m-%d %H:%M:%S'))
                    if int(time.time() - ts) > self.REPORT_LOST_SECONDS and item.get('role') == 'master' and item.get('collect_method') == 'local':
                        danger.append('{0} 插件失联'.format(self._displayHostName(item, pair)))
                except Exception:
                    pass
            if item.get('role') == 'master' and item.get('online_status') == 'offline':
                danger.append('{0} 主机离线'.format(self._displayHostName(item, pair)))
            if item.get('collect_status') in ('failed', 'partial'):
                warnings.append('{0} SSH采集异常'.format(self._displayHostName(item, pair)))
            detail = self._jsonLoads(item.get('health_detail'), {})
            failover = self._stateFailover(item)
            if isinstance(failover, dict):
                if failover.get('recovery_status') == 'recovery_guard':
                    degraded.append('{0} 恢复保护，待恢复为备机'.format(self._displayHostName(item, pair)))
                elif failover.get('mode') == 'degraded_master' or failover.get('pending_switch_required'):
                    degraded.append('{0} 降级运行，待 {1} 切换为 {2}'.format(self._displayHostName(item, pair), self._pendingSwitchTargetText(failover, states), failover.get('pending_switch_role') or '备机'))
            failed_checks = [x for x in self._normalizeScriptChecks(detail) if x.get('status') == 'failed']
            if item.get('health_status') in ('warning', 'danger', 'failed') or failed_checks:
                summary = detail.get('summary') if isinstance(detail, dict) else ''
                if not summary and failed_checks:
                    names = [x.get('name') for x in failed_checks if x.get('name')]
                    summary = '{0} 自检异常 {1} 项'.format(self._displayHostName(item, pair), len(failed_checks))
                    if names:
                        summary += '：' + '、'.join(names[:3])
                        if len(names) > 3:
                            summary += '等'
                warnings.append(summary or '{0} 自检提醒'.format(self._displayHostName(item, pair)))
        desired = pair.get('desired_master_host_id') or ''
        actual_aliases = []
        if len(masters) == 1:
            actual_aliases = masters[0].get('_alias_host_ids') or []
            if masters[0].get('host_id') not in actual_aliases:
                actual_aliases.append(masters[0].get('host_id'))
        if desired and actual_aliases and desired not in actual_aliases:
            danger.append('期望主机和实际主机不一致')
        if danger:
            return 'danger', '；'.join(danger[:3])
        if degraded:
            return 'warning', '；'.join(degraded[:3])
        if warnings:
            return 'warning', '；'.join(warnings[:3])
        if any([v == 'offline' for v in online.values()]):
            return 'warning', '备用机或对端离线'
        return 'normal', '状态正常'

    def _normalizePair(self, pair, include_log=False, include_events=False):
        states = self._displayStates(self._getStates(pair.get('pair_id')))
        status, status_text = self.deriveStatus(pair, states)
        hosts = [self._normalizeHost(x, pair) for x in states]
        actual_master = ''
        for host in hosts:
            if host.get('role') == 'master':
                actual_master = host.get('host_id')
                break
        effective_actual_master = self._actualMasterHostId(states)
        if effective_actual_master:
            actual_master = effective_actual_master
        desired_master = pair.get('desired_master_host_id') or actual_master
        for host in hosts:
            if host.get('role') == 'master' and desired_master in (host.get('host_alias_ids') or []):
                desired_master = host.get('host_id')
                break
        else:
            for host in hosts:
                if desired_master in (host.get('host_alias_ids') or []):
                    desired_master = host.get('host_id')
                    break
        data = dict(pair)
        data['status'] = status
        data['status_text'] = status_text
        data['hosts'] = hosts
        data['actual_master_host_id'] = actual_master or pair.get('actual_master_host_id') or ''
        data['desired_master_host_id'] = desired_master or data['actual_master_host_id']
        data['switch_run_id'] = pair.get('current_switch_run_id') or ''
        data['log_path'] = ''
        data['switch_run'] = {}
        data['switch_runs'] = []
        data['switch_events'] = []
        data['alert_events'] = []
        latest_alert_events = self._getAlertEvents(pair.get('pair_id'), 1)
        data['latest_alert_event'] = latest_alert_events[0] if latest_alert_events else {}
        data['source_monitor_id'] = pair.get('source_monitor_id') or ''
        data['sync_update_at'] = pair.get('sync_update_at') or ''
        if data['switch_run_id']:
            run = self._getRun(data['switch_run_id'])
            data['switch_run'] = self._normalizeRun(run)
            data['log_path'] = run.get('log_path') or ''
            if include_events:
                data['switch_events'] = [self._normalizeEvent(x) for x in self._getEvents(data['switch_run_id'])]
        if include_log or include_events:
            data['switch_runs'] = self._getRuns(pair.get('pair_id'), 1, 20)
            data['alert_events'] = self._getAlertEvents(pair.get('pair_id'), 20)
        data['health'] = self._summaryHealth(hosts)
        data['warnings'] = [] if status == 'normal' else status_text.split('；')
        data['log'] = self._readLogText(data.get('log_path')) if include_log and data.get('log_path') else ''
        data['last_report_at'] = pair.get('last_report_at') or ''
        return data

    def _summaryHealth(self, hosts):
        result = {'mysql': '未知', 'rsync': '未知', 'openresty': '未知'}
        for host in hosts:
            detail = host.get('health_detail') or {}
            for key in result.keys():
                item = detail.get(key)
                if isinstance(item, dict):
                    result[key] = item.get('text') or item.get('status') or result[key]
                elif item:
                    result[key] = str(item)
        return result

    def _getRun(self, switch_run_id):
        row = jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).field(self.run_fields).find()
        return row if isinstance(row, dict) else {}

    def getListApi(self):
        if not self.ensureHaSchema():
            return jh.returnJson(False, 'HA表结构初始化失败')
        rows = jh.M('ha_pair').field(self.pair_fields).order('sort_id asc,id desc').select()
        if not isinstance(rows, list):
            rows = []
        return jh.returnJson(True, 'ok', {'list': [self._normalizePair(row, include_log=False, include_events=False) for row in rows]})

    def saveListSortApi(self):
        if not self.ensureHaSchema():
            return jh.returnJson(False, 'HA表结构初始化失败')
        row_ids = request.form.getlist('row_ids[]')
        if len(row_ids) == 0:
            row_ids = request.form.getlist('row_ids')
        if len(row_ids) == 0:
            row_ids_text = request.form.get('row_ids', '').strip()
            if row_ids_text:
                row_ids = row_ids_text.split(',')

        normalized_ids = []
        for row_id in row_ids:
            if isinstance(row_id, str) and ',' in row_id:
                for item in row_id.split(','):
                    try:
                        item_id = int(str(item).strip())
                    except Exception:
                        continue
                    if item_id not in normalized_ids:
                        normalized_ids.append(item_id)
                continue
            try:
                row_id = int(str(row_id).strip())
            except Exception:
                continue
            if row_id not in normalized_ids:
                normalized_ids.append(row_id)

        if len(normalized_ids) == 0:
            return jh.returnJson(False, '请先选择有效的主备关系排序数据!')

        sort_value = 1
        for row_id in normalized_ids:
            jh.M('ha_pair').where('id=?', (row_id,)).setField('sort_id', sort_value)
            sort_value += 1
        return jh.returnJson(True, '主备关系排序已保存!')

    def getDetailApi(self):
        pair_id = request.form.get('pair_id', '').strip()
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        return jh.returnJson(True, 'ok', self._normalizePair(pair, include_log=True, include_events=True))

    def getLogsApi(self):
        pair_id = request.form.get('pair_id', '').strip()
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        page = self._safeInt(request.form.get('page', 1), 1)
        page_size = self._safeInt(request.form.get('page_size', 20), 20)
        return jh.returnJson(True, 'ok', self._getRuns(pair_id, page, page_size))

    def deletePairApi(self):
        self.ensureHaSchema()
        pair_id = request.form.get('pair_id', '').strip()
        if not pair_id:
            return jh.returnJson(False, '主备关系不能为空')
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        runs = jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).field('switch_run_id').select()
        run_ids = []
        if isinstance(runs, list):
            run_ids = [row.get('switch_run_id') for row in runs if isinstance(row, dict) and row.get('switch_run_id')]
        jh.M('ha_switch_event').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_alert_event').where('pair_id=?', (pair_id,)).delete()
        for switch_run_id in run_ids:
            jh.M('ha_switch_event').where('switch_run_id=?', (switch_run_id,)).delete()
        jh.M('ha_callback_record').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_host_state').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_switch_run').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_api_nonce').where('pair_id=?', (pair_id,)).delete()
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).delete()
        return jh.returnJson(True, '主备关系已删除', {'pair_id': pair_id})

    def _monthLogPath(self, switch_run_id):
        month = time.strftime('%Y-%m')
        directory = os.path.join(self.LOG_ROOT, month)
        if not os.path.exists(directory):
            os.makedirs(directory, mode=0o755, exist_ok=True)
        return os.path.join(directory, switch_run_id + '.log')

    def _appendLog(self, log_path, line):
        directory = os.path.dirname(log_path)
        if not os.path.exists(directory):
            os.makedirs(directory, mode=0o755, exist_ok=True)
        with open(log_path, 'a', encoding='utf-8') as fp:
            fp.write(line.rstrip('\n') + '\n')

    def _readLogText(self, log_path, offset=0, limit=200000):
        if not log_path or not os.path.exists(log_path):
            return ''
        with open(log_path, 'rb') as fp:
            fp.seek(max(0, int(offset)))
            data = fp.read(max(1, int(limit)))
        return data.decode('utf-8', errors='replace')

    def _advanceSwitchRun(self, run, phase, phase_status, step):
        now = self._now()
        if phase not in ('prepare_online', 'offline', 'online'):
            if run.get('status') in ('success', 'prepare_success'):
                return run.get('status') or 'running'
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('current_step,update_time', (step, now))
            return run.get('status') or 'running'
        if phase_status in ('failed', 'error'):
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,last_error,claimed_by_host_id,claim_token,claim_expire_at,update_time', ('waiting_retry', phase, step, step, '', '', 0, now))
            return 'waiting_retry'
        if phase_status not in ('done', 'success'):
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,update_time', ('running', phase, step, now))
            return 'running'
        if phase == 'prepare_online':
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,next_step,claimed_by_host_id,claim_token,claim_expire_at,update_time,finish_time', ('prepare_success', phase, step or '预上线完成', '等待操作员执行正式上线', '', '', 0, now, now))
            jh.M('ha_pair').where('pair_id=?', (run.get('pair_id'),)).save('status,status_text,last_report_at,update_time', ('normal', '预上线完成，等待正式上线', now, now))
            return 'prepare_success'
        if phase == 'offline':
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,next_step,claimed_by_host_id,claim_token,claim_expire_at,update_time', ('pending_online', 'online', '等待目标主机领取上线阶段', '目标主机正式上线', '', '', 0, now))
            return 'pending_online'
        if phase == 'online':
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,last_error,claimed_by_host_id,claim_token,claim_expire_at,update_time,finish_time', ('success', phase, step or '正式上线完成', '', '', '', 0, now, now))
            jh.M('ha_pair').where('pair_id=?', (run.get('pair_id'),)).save('actual_master_host_id,desired_master_host_id,current_switch_run_id,status,status_text,last_report_at,update_time', (run.get('new_master_host_id'), run.get('new_master_host_id'), '', 'normal', '状态正常', now, now))
            self._executeCallbacks(run.get('pair_id'), run.get('switch_run_id'))
            return 'success'
        return 'running'

    def requestSwitchApi(self):
        self.ensureHaSchema()
        pair_id = request.form.get('pair_id', '').strip()
        target_host_id = request.form.get('target_host_id', '').strip() or request.form.get('desired_master_host_id', '').strip()
        action = request.form.get('action', '').strip() or 'finalize'
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        if not target_host_id:
            return jh.returnJson(False, '目标主机不能为空')
        if action not in ('prepare', 'finalize'):
            return jh.returnJson(False, '切换动作无效')
        options = self._switchOptionsFromRequest()
        execution_monitor_id, execution_reason = self._selectExecutionMonitor(pair_id, target_host_id)
        if action == 'prepare':
            data = self._createSwitchRun(pair, target_host_id, 'prepare_online', '等待目标主机领取预上线阶段', '预上线完成后执行正式上线', 'pending_prepare', options, '预上线', execution_monitor_id=execution_monitor_id, dispatch_reason=execution_reason)
            return jh.returnJson(True, '预上线任务已创建', data)
        old_master_host_id = ''
        finalize_target_host_id = target_host_id
        current_run_id = pair.get('current_switch_run_id') or ''
        if current_run_id:
            current_run = self._getRun(current_run_id)
            if current_run and current_run.get('status') == 'prepare_success':
                old_master_host_id = current_run.get('old_master_host_id') or ''
                finalize_target_host_id = current_run.get('new_master_host_id') or current_run.get('desired_master_host_id') or finalize_target_host_id
        if not old_master_host_id:
            old_master_host_id = pair.get('actual_master_host_id') or self._masterHostId(pair_id, '')
        if not finalize_target_host_id:
            finalize_target_host_id = pair.get('desired_master_host_id') or target_host_id
        should_promote_mysql = True
        if not old_master_host_id or old_master_host_id == finalize_target_host_id:
            old_master_host_id = self._fallbackOldMasterHostId(pair_id, finalize_target_host_id, '', True)
            should_promote_mysql = False
        if old_master_host_id:
            if not should_promote_mysql:
                options['promote_mysql'] = False
            execution_monitor_id, execution_reason = self._selectExecutionMonitor(pair_id, finalize_target_host_id)
            data = self._createSwitchRun(pair, finalize_target_host_id, 'offline', '等待旧主机领取下线阶段', '目标主机上线阶段', 'pending_finalize', options, '正式上线', old_master_host_id, execution_monitor_id, execution_reason)
            if not should_promote_mysql:
                self._appendLog(data.get('log_path'), '[{0}] [system] [pending] 未检测到当前旧主机，按选择目标执行：目标主机正式上线，另一台主机下线，跳过数据库主从提升'.format(self._now()))
        else:
            options['promote_mysql'] = False
            execution_monitor_id, execution_reason = self._selectExecutionMonitor(pair_id, finalize_target_host_id)
            data = self._createSwitchRun(pair, finalize_target_host_id, 'online', '未检测到旧主机，等待目标主机直接领取正式上线阶段', '目标主机正式上线', 'pending_online', options, '正式上线', '', execution_monitor_id, execution_reason)
            self._appendLog(data.get('log_path'), '[{0}] [system] [pending] 当前主备关系未检测到另一台主机，跳过下线阶段，直接执行目标主机正式上线，并跳过数据库主从提升'.format(self._now()))
        return jh.returnJson(True, '正式上线任务已创建', data)

    def retrySwitchApi(self):
        switch_run_id = request.form.get('switch_run_id', '').strip()
        run = self._getRun(switch_run_id)
        if not run:
            return jh.returnJson(False, '切换任务不存在')
        now = self._now()
        jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save('status,last_error,update_time', ('waiting_retry', '', now))
        self._appendLog(run.get('log_path'), '[{0}] [system] [retry] 操作员请求重试失败阶段'.format(now))
        return jh.returnJson(True, '已标记重试')

    def cancelSwitchApi(self):
        switch_run_id = request.form.get('switch_run_id', '').strip()
        run = self._getRun(switch_run_id)
        if not run:
            return jh.returnJson(False, '切换任务不存在')
        now = self._now()
        jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save('status,current_step,update_time,finish_time', ('cancelled', '操作员取消', now, now))
        self._appendLog(run.get('log_path'), '[{0}] [system] [cancelled] 操作员取消切换任务'.format(now))
        return jh.returnJson(True, '已取消')

    def readLogApi(self):
        switch_run_id = request.form.get('switch_run_id', '').strip()
        offset = self._safeInt(request.form.get('offset', 0), 0)
        run = self._getRun(switch_run_id)
        if not run:
            return jh.returnJson(False, '切换任务不存在')
        log_path = run.get('log_path') or ''
        text = self._readLogText(log_path, offset)
        next_offset = offset + len(text.encode('utf-8'))
        return jh.returnJson(True, 'ok', {
            'run': self._normalizeRun(run),
            'log_path': log_path,
            'offset': offset,
            'next_offset': next_offset,
            'content': text
        })

    def saveCallbackConfigApi(self):
        self.ensureHaSchema()
        pair_id = request.form.get('pair_id', '').strip()
        callback_url = request.form.get('callback_url', '').strip()
        enabled = 1 if str(request.form.get('callback_enabled', '0')).lower() in ('1', 'true', 'yes', 'on') else 0
        if not self._getPair(pair_id):
            return jh.returnJson(False, '主备关系不存在')
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('callback_url,callback_enabled,update_time', (callback_url, enabled, self._now()))
        return jh.returnJson(True, '回调配置已保存')

    def _pairSecret(self, pair_id):
        pair = self._getPair(pair_id)
        return pair.get('api_secret') or self.DEFAULT_SECRET

    def _verifySignedRequest(self, payload):
        pair_id = self._safeText(payload.get('pair_id'), 128)
        timestamp = self._safeText(request.headers.get('X-JH-Timestamp') or payload.get('timestamp'), 32)
        nonce = self._safeText(request.headers.get('X-JH-Nonce') or payload.get('nonce'), 128)
        signature = self._safeText(request.headers.get('X-JH-Signature') or payload.get('signature'), 128)
        body_hash = self._safeText(request.headers.get('X-JH-Body-Hash') or payload.get('body_hash'), 128)
        if not pair_id:
            return False, 'pair_id不能为空'
        if not timestamp or not nonce or not signature:
            return False, '签名参数不完整'
        try:
            ts = int(timestamp)
        except Exception:
            return False, 'timestamp无效'
        if abs(int(time.time()) - ts) > self.NONCE_TTL_SECONDS:
            return False, 'timestamp已过期'
        body = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
        expected_body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()
        if body_hash and body_hash != expected_body_hash:
            return False, 'body_hash不匹配'
        secret = self._pairSecret(pair_id)
        sign_text = '\n'.join([timestamp, nonce, body_hash or expected_body_hash])
        expected = hmac.new(secret.encode('utf-8'), sign_text.encode('utf-8'), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False, '签名错误'
        exists = jh.M('ha_api_nonce').where('nonce=?', (nonce,)).field('id').find()
        if isinstance(exists, dict) and exists.get('id'):
            return False, 'nonce已使用'
        now = int(time.time())
        jh.M('ha_api_nonce').add('nonce,pair_id,addtime', (nonce, pair_id, now))
        try:
            jh.M('ha_api_nonce').where('addtime<?', (now - self.NONCE_TTL_SECONDS,)).delete()
        except Exception:
            pass
        return True, 'ok'

    def _publicPayload(self, verify=True):
        self.ensureHaSchema()
        payload = self._bodyJson()
        if not verify:
            return True, payload, 'ok'
        ok, msg = self._verifySignedRequest(payload)
        return ok, payload, msg

    def publicRegisterPair(self):
        ok, payload, msg = self._publicPayload(False)
        pair_id = self._safeText(payload.get('pair_id'), 128)
        pair_name = self._safeText(payload.get('pair_name') or payload.get('name'), 128)
        local = payload.get('local_host') or {}
        peer = payload.get('peer_host') or {}
        if not pair_id:
            pair_id = 'HA_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(4))
        if not pair_name:
            return jh.returnJson(False, '主备关系名称不能为空')
        now = self._now()
        api_secret = self._safeText(payload.get('api_secret'), 128) or self.DEFAULT_SECRET
        exist = self._getPair(pair_id)
        master_id = self._safeText(payload.get('desired_master_host_id') or local.get('host_id'), 128)
        if exist:
            stored_secret = exist.get('api_secret') or ''
            if not stored_secret:
                stored_secret = api_secret
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('pair_name,desired_master_host_id,api_secret,update_time', (pair_name, master_id, stored_secret, now))
            api_secret = stored_secret
        else:
            sort_id = self._nextPairSortId()
            jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,sort_id,addtime,update_time', (pair_id, pair_name, master_id, api_secret, 'unknown', '等待插件上报', sort_id, now, now))
        if isinstance(local, dict) and local.get('host_id'):
            local.setdefault('collect_method', 'local')
            local.setdefault('report_host_id', local.get('host_id'))
            local.setdefault('site_scope', 'local')
        if isinstance(peer, dict) and peer.get('host_id'):
            peer.setdefault('collect_method', 'ssh_peer')
            peer.setdefault('report_host_id', local.get('host_id') if isinstance(local, dict) else '')
            peer.setdefault('site_scope', 'remote')
        for host in (local, peer):
            if isinstance(host, dict) and host.get('host_id'):
                self._upsertState(pair_id, host, host.get('role') or ('master' if host.get('host_id') == master_id else 'standby'), now)
        return jh.returnJson(True, '注册成功', {'pair_id': pair_id, 'api_secret': api_secret})

    def _upsertState(self, pair_id, host, role, now):
        host_id = self._safeText(host.get('host_id'), 128)
        host_name = self._safeText(host.get('host_name') or host.get('name') or host_id, 128)
        host_ip = self._safeText(host.get('host_ip') or host.get('ip'), 64)
        collect_method = self._safeText(host.get('collect_method') or '', 32)
        report_host_id = self._safeText(host.get('report_host_id') or '', 128)
        last_report_at = self._safeText(host.get('last_report_at') or now, 32)
        report_batch_id = self._safeText(host.get('report_batch_id') or '', 128)
        original_host_id = host_id
        health_detail = host.get('health_detail') or {}
        source_monitor_id = self._safeText(host.get('source_monitor_id') or self._localMonitor().get('monitor_id'), 128)
        if collect_method == 'ssh_peer' and isinstance(health_detail, dict) and original_host_id:
            health_detail.setdefault('_source_host_id', original_host_id)
        exists = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).field('id,collect_method').find()
        if collect_method == 'ssh_peer' and isinstance(exists, dict) and exists.get('collect_method') == 'local':
            source = '{0}:{1}:{2}'.format(report_host_id, host_ip, host_id)
            host_id = 'H_ALIAS_' + hashlib.sha1(source.encode('utf-8')).hexdigest()[:8].upper()
            exists = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).field('id,collect_method').find()
        values = (
            host_name,
            host_ip,
            self._safeText(role, 32),
            self._safeText(host.get('online_status') or host.get('online') or 'unknown', 32),
            self._safeText(host.get('health_status') or 'unknown', 32),
            self._safeText(host.get('collect_status') or 'unknown', 32),
            collect_method,
            report_host_id,
            self._safeText(host.get('site_scope') or '', 32),
            json.dumps(health_detail, ensure_ascii=False),
            self._safeText(host.get('switch_run_id') or '', 128),
            self._safeText(host.get('switch_phase') or '', 64),
            self._safeText(host.get('switch_status') or '', 64),
            self._safeText(host.get('current_step') or '', 255),
            self._safeText(host.get('next_step') or '', 255),
            self._safeText(host.get('last_error') or '', 512),
            self._safeText(host.get('log_path') or '', 512),
            last_report_at,
            report_batch_id,
            source_monitor_id,
            self._safeText(host.get('sync_update_at') or '', 32),
            now
        )
        if isinstance(exists, dict) and exists.get('id'):
            result = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).save(
                'host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,current_step,next_step,last_error,log_path,last_report_at,report_batch_id,source_monitor_id,sync_update_at,update_time', values
            )
        else:
            result = jh.M('ha_host_state').add(
                'pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,current_step,next_step,last_error,log_path,last_report_at,report_batch_id,source_monitor_id,sync_update_at,addtime,update_time',
                (pair_id, host_id) + values + (now,)
            )
        if isinstance(result, str) and result.startswith('error:'):
            self._appendSyncLog('upsert host state failed pair_id={0} host_id={1} error={2}'.format(pair_id, host_id, result))
        if report_batch_id:
            jh.M('ha_host_state').originExecute(
                'UPDATE ha_host_state SET report_batch_id=?, update_time=? WHERE pair_id=? AND host_id=?',
                (report_batch_id, now, pair_id, host_id)
            )

    def publicPullDesiredState(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        host_id = self._safeText(payload.get('host_id'), 128)
        pair = self._getPair(payload.get('pair_id'))
        if not pair:
            return jh.returnJson(False, 'unknown pair_id')
        raw_states = self._getStates(pair.get('pair_id'))
        states = self._displayStates(raw_states)

        def resolve_executor(target_host_id):
            target_host_id = self._safeText(target_host_id, 128)
            if not target_host_id:
                return '', ''
            for state in states:
                alias_ids = state.get('_alias_host_ids') or []
                if state.get('host_id') not in alias_ids:
                    alias_ids.append(state.get('host_id'))
                if target_host_id not in alias_ids:
                    continue
                if state.get('collect_method') == 'ssh_peer' and state.get('report_host_id'):
                    return state.get('report_host_id'), 'ssh_peer'
                break
            if host_id == target_host_id:
                return target_host_id, 'local'
            for state in raw_states:
                detail = self._jsonLoads(state.get('health_detail'), {})
                alias_ids = [state.get('host_id')]
                source_host_id = detail.get('_source_host_id') if isinstance(detail, dict) else ''
                if source_host_id:
                    alias_ids.append(source_host_id)
                if target_host_id not in alias_ids:
                    continue
                if state.get('collect_method') == 'ssh_peer' and state.get('report_host_id') == host_id:
                    return host_id, 'ssh_peer'
            return '', ''

        run = {}
        if pair.get('current_switch_run_id'):
            run = self._getRun(pair.get('current_switch_run_id'))
            if run:
                local_monitor_id = self._localMonitor().get('monitor_id')
                execution_monitor_id = run.get('execution_monitor_id') or local_monitor_id
                if execution_monitor_id and execution_monitor_id != local_monitor_id:
                    run['execute_phase'] = ''
                    run['execute_method'] = ''
                    run['execute_target_host_id'] = ''
                    run['dispatch_reason'] = '当前江湖云监控不是该任务执行方，任务执行方为 {0}'.format(execution_monitor_id)
                    return jh.returnJson(True, 'ok', {'desired_master_host_id': pair.get('desired_master_host_id'), 'switch_run': run})
                if self._safeInt(run.get('dispatchable'), 1) != 1:
                    run['execute_phase'] = ''
                    run['execute_method'] = ''
                    run['execute_target_host_id'] = ''
                    run['dispatch_reason'] = run.get('dispatch_reason') or '当前切换任务不可下发执行'
                    return jh.returnJson(True, 'ok', {'desired_master_host_id': pair.get('desired_master_host_id'), 'switch_run': run})
                if run.get('current_phase') == 'offline' and not run.get('old_master_host_id'):
                    repaired_old_master = self._fallbackOldMasterHostId(pair.get('pair_id'), run.get('new_master_host_id') or run.get('desired_master_host_id') or '', '', True)
                    if repaired_old_master:
                        options = self._jsonLoads(run.get('options_json'), {})
                        if not isinstance(options, dict):
                            options = {}
                        options['promote_mysql'] = False
                        run['old_master_host_id'] = repaired_old_master
                        run['options_json'] = json.dumps(options, ensure_ascii=False)
                        jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('old_master_host_id,options_json,update_time', (repaired_old_master, run.get('options_json'), self._now()))
                        self._appendLog(run.get('log_path'), '[{0}] [system] [repair] 未检测到当前旧主机，设置另一台主机为下线目标 old_master_host_id={1}，并跳过数据库主从提升'.format(self._now(), repaired_old_master))
                    else:
                        now = self._now()
                        options = self._jsonLoads(run.get('options_json'), {})
                        if not isinstance(options, dict):
                            options = {}
                        options['promote_mysql'] = False
                        run['current_phase'] = 'online'
                        run['status'] = 'pending_online'
                        run['options_json'] = json.dumps(options, ensure_ascii=False)
                        jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,next_step,options_json,update_time', ('pending_online', 'online', '未检测到旧主机，跳过下线阶段，等待目标主机领取正式上线阶段', '目标主机正式上线', run.get('options_json'), now))
                        self._appendLog(run.get('log_path'), '[{0}] [system] [repair] 未检测到旧主机，跳过下线阶段，推进到目标主机正式上线'.format(now))
                phase = run.get('current_phase') or ''
                target_host_id = ''
                if phase == 'prepare_online':
                    target_host_id = run.get('new_master_host_id')
                    run['execute_role'] = 'master'
                elif phase == 'offline':
                    target_host_id = run.get('old_master_host_id')
                    run['execute_role'] = 'standby'
                elif phase == 'online':
                    target_host_id = run.get('new_master_host_id')
                    run['execute_role'] = 'master'
                executor_host_id, execute_method = resolve_executor(target_host_id)
                run['execute_phase'] = phase if executor_host_id == host_id and phase in ('prepare_online', 'offline', 'online') else ''
                run['execute_method'] = execute_method
                run['execute_target_host_id'] = target_host_id
                if not target_host_id:
                    run['dispatch_reason'] = '当前阶段目标主机为空，无法下发执行；请检查切换任务 old_master_host_id/new_master_host_id'
                elif not executor_host_id:
                    run['dispatch_reason'] = '未找到可执行主机：目标主机 {0} 不在当前云监控可用上报主机或 ssh_peer 代理关系中'.format(target_host_id)
                elif executor_host_id != host_id:
                    run['dispatch_reason'] = '任务由主机 {0} 执行，当前轮询主机 {1} 不执行'.format(executor_host_id, host_id)
                else:
                    run['dispatch_reason'] = '任务已下发给当前主机执行'
                    claim_expire_at = self._safeInt(run.get('claim_expire_at'), 0)
                    claimed_by_host_id = run.get('claimed_by_host_id') or ''
                    if claimed_by_host_id and claimed_by_host_id != host_id and claim_expire_at > int(time.time()):
                        run['execute_phase'] = ''
                        run['dispatch_reason'] = '任务阶段已由主机 {0} 领取，当前主机不重复执行'.format(claimed_by_host_id)
                    else:
                        claim_token = '{0}_{1}'.format(run.get('switch_run_id'), jh.getRandomString(12))
                        claim_expire_at = int(time.time()) + 120
                        run['claimed_by_host_id'] = host_id
                        run['claim_token'] = claim_token
                        run['claim_expire_at'] = claim_expire_at
                        jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save(
                            'claimed_by_host_id,claim_token,claim_expire_at,dispatch_reason,update_time',
                            (host_id, claim_token, claim_expire_at, run['dispatch_reason'], self._now())
                        )
        return jh.returnJson(True, 'ok', {'desired_master_host_id': pair.get('desired_master_host_id'), 'switch_run': run})

    def publicReportState(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        pair_id = payload.get('pair_id')
        if not self._getPair(pair_id):
            return jh.returnJson(False, 'unknown pair_id')
        now = self._now()
        hosts = payload.get('hosts') if isinstance(payload.get('hosts'), list) else [payload]
        report_batch_id = self._safeText(payload.get('report_batch_id') or '', 128)
        if not report_batch_id and len(hosts) > 1:
            report_batch_id = 'HRB_{0}_{1}'.format(time.strftime('%Y%m%d%H%M%S'), jh.getRandomString(6))
        for host in hosts:
            if report_batch_id and isinstance(host, dict) and not host.get('report_batch_id'):
                host['report_batch_id'] = report_batch_id
            self._upsertState(pair_id, host, host.get('role') or host.get('actual_role') or 'unknown', now)
        states = self._displayStates(self._getStates(pair_id))
        pair = self._getPair(pair_id)
        status, status_text = self.deriveStatus(pair, states)
        actual = self._actualMasterHostId(states)
        desired = self._safeText(payload.get('desired_master_host_id') or '', 128)
        current_run = self._getRun(pair.get('current_switch_run_id') or '') if pair.get('current_switch_run_id') else {}
        if current_run.get('status') == 'prepare_success':
            desired = ''
        if not desired and actual and not pair.get('current_switch_run_id'):
            desired = actual
        if desired:
            pair['desired_master_host_id'] = desired
            status, status_text = self.deriveStatus(pair, states)
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('desired_master_host_id,actual_master_host_id,status,status_text,last_report_at,update_time', (desired, actual, status, status_text, now, now))
        else:
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('actual_master_host_id,status,status_text,last_report_at,update_time', (actual, status, status_text, now, now))
        self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_pair', pair_id, {'pair': self._getPair(pair_id)})
        for state in self._getStates(pair_id):
            self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_host_state', '{0}:{1}'.format(pair_id, state.get('host_id') or ''), {'state': state})
        return jh.returnJson(True, '状态已上报')

    def publicReportSwitchEvent(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        pair_id = payload.get('pair_id')
        switch_run_id = payload.get('switch_run_id')
        run = self._getRun(switch_run_id)
        if not run:
            return jh.returnJson(False, 'unknown switch_run_id')
        event_id = self._safeText(payload.get('event_id'), 128)
        origin_host_id = self._safeText(payload.get('origin_host_id') or payload.get('host_id'), 128)
        seq = self._safeInt(payload.get('seq'), 0)
        if event_id:
            exists = jh.M('ha_switch_event').where('event_id=?', (event_id,)).field('id').find()
        else:
            exists = jh.M('ha_switch_event').where('switch_run_id=? AND origin_host_id=? AND seq=?', (switch_run_id, origin_host_id, seq)).field('id').find()
            event_id = '{0}:{1}:{2}'.format(switch_run_id, origin_host_id, seq)
        if isinstance(exists, dict) and exists.get('id'):
            return jh.returnJson(True, '重复事件已忽略', {'duplicate': True})
        now = self._now()
        phase = self._safeText(payload.get('phase'), 64)
        step = self._safeText(payload.get('step'), 255)
        status = self._safeText(payload.get('status'), 64)
        log_text = self._safeText(payload.get('log_text') or payload.get('message'), 4000)
        jh.M('ha_switch_event').add(
            'switch_run_id,pair_id,event_id,origin_host_id,report_host_id,collect_method,seq,phase,step,status,log_text,addtime',
            (switch_run_id, pair_id, event_id, origin_host_id, self._safeText(payload.get('report_host_id'), 128), self._safeText(payload.get('collect_method'), 32), seq, phase, step, status, log_text, now)
        )
        is_aux_after_done = phase not in ('prepare_online', 'offline', 'online') and run.get('status') in ('success', 'prepare_success')
        if not is_aux_after_done:
            line = '[{0}] [{1}] [{2}] [{3}] {4}'.format(now, origin_host_id or 'unknown', phase or 'event', status or 'info', log_text or step)
            self._appendLog(run.get('log_path'), line)
        db_status = self._advanceSwitchRun(run, phase, status, step or log_text)
        saved_event = jh.M('ha_switch_event').where('event_id=?', (event_id,)).field('id,switch_run_id,pair_id,event_id,origin_host_id,report_host_id,collect_method,seq,phase,step,status,log_text,addtime').find()
        if isinstance(saved_event, dict) and saved_event.get('id'):
            self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_switch_event', event_id, {'event': saved_event})
        updated_run = self._getRun(switch_run_id)
        if updated_run:
            self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_switch_run', switch_run_id, {'run': self._normalizeRun(updated_run)})
        return jh.returnJson(True, '事件已上报')

    def publicReportAlertEvent(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        pair_id = self._safeText(payload.get('pair_id'), 128)
        if not self._getPair(pair_id):
            return jh.returnJson(False, 'unknown pair_id')
        event_id = self._safeText(payload.get('event_id'), 128)
        if not event_id:
            event_id = '{0}:{1}:{2}:{3}'.format(pair_id, self._safeText(payload.get('host_id'), 64), self._safeText(payload.get('event_type'), 64), int(time.time() * 1000))
        exists = jh.M('ha_alert_event').where('event_id=?', (event_id,)).field('id').find()
        if isinstance(exists, dict) and exists.get('id'):
            return jh.returnJson(True, '重复事件已忽略', {'duplicate': True})
        alerts = payload.get('alerts') if isinstance(payload.get('alerts'), list) else []
        now = self._now()
        jh.M('ha_alert_event').add(
            'pair_id,event_id,event_type,alert_key,alert_type,alert_level,status,title,message,sent_by_host_id,report_host_id,notifier_mode,alerts_json,addtime',
            (
                pair_id,
                event_id,
                self._safeText(payload.get('event_type'), 64),
                self._safeText(payload.get('alert_key'), 255),
                self._safeText(payload.get('alert_type'), 64),
                self._safeText(payload.get('alert_level'), 32),
                self._safeText(payload.get('status'), 32),
                self._safeText(payload.get('title'), 255),
                self._safeText(payload.get('message'), 4000),
                self._safeText(payload.get('sent_by_host_id') or payload.get('host_id'), 128),
                self._safeText(payload.get('report_host_id') or payload.get('host_id'), 128),
                self._safeText(payload.get('notifier_mode'), 64),
                json.dumps(alerts, ensure_ascii=False),
                now
            )
        )
        latest_title = self._safeText(payload.get('title'), 255)
        if latest_title:
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('update_time', (now,))
        saved_alert = jh.M('ha_alert_event').where('event_id=?', (event_id,)).field(self.alert_event_fields).find()
        if isinstance(saved_alert, dict) and saved_alert.get('id'):
            self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_alert_event', event_id, {'alert': self._normalizeAlertEvent(saved_alert)})
        return jh.returnJson(True, '通知事件已上报')

    def publicAckSwitchPhase(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        switch_run_id = payload.get('switch_run_id')
        run = self._getRun(switch_run_id)
        if not run:
            return jh.returnJson(False, 'unknown switch_run_id')
        phase = self._safeText(payload.get('phase'), 64)
        phase_status = self._safeText(payload.get('phase_status') or payload.get('status'), 64)
        step = self._safeText(payload.get('current_step') or payload.get('step'), 255)
        now = self._now()
        status = self._advanceSwitchRun(run, phase, phase_status, step or payload.get('last_error') or '')
        self._appendLog(run.get('log_path'), '[{0}] [{1}] [{2}] {3}'.format(now, phase or 'phase', phase_status or status, step or '阶段确认'))
        updated_run = self._getRun(switch_run_id)
        if updated_run:
            self._writeSyncEvent(self.DEFAULT_SYNC_TYPE, 'ha_switch_run', switch_run_id, {'run': self._normalizeRun(updated_run)})
        return jh.returnJson(True, '阶段已确认')

    def _executeCallbacks(self, pair_id, switch_run_id):
        pair = self._getPair(pair_id)
        run = self._getRun(switch_run_id)
        callback_url = (pair.get('callback_url') or '').strip()
        if not callback_url or self._safeInt(pair.get('callback_enabled'), 0) != 1:
            return
        payload = {
            'pair_id': pair_id,
            'switch_run_id': switch_run_id,
            'old_master': run.get('old_master_host_id') or '',
            'new_master': run.get('new_master_host_id') or '',
            'actual_master': run.get('new_master_host_id') or pair.get('actual_master_host_id') or '',
            'status': 'success',
            'finish_time': run.get('finish_time') or self._now()
        }
        body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        now = self._now()
        status = 'success'
        error_msg = ''
        response_body = ''
        try:
            req = urllib.request.Request(callback_url, data=body, headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=10) as resp:
                response_body = resp.read().decode('utf-8', errors='replace')[:4000]
                if resp.status < 200 or resp.status >= 300:
                    status = 'failed'
                    error_msg = 'HTTP {0}'.format(resp.status)
        except Exception as e:
            status = 'failed'
            error_msg = str(e)
        jh.M('ha_callback_record').add(
            'pair_id,switch_run_id,callback_url,status,error_msg,request_body,response_body,addtime,update_time',
            (pair_id, switch_run_id, callback_url, status, error_msg, json.dumps(payload, ensure_ascii=False), response_body, now, now)
        )
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('callback_status,update_time', (status, now))
        jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save('callback_status,callback_error,update_time', (status, error_msg, now))
        log_path = run.get('log_path') or self._monthLogPath(switch_run_id)
        if status == 'success':
            self._appendLog(log_path, '[{0}] [callback] [success] 外部回调执行成功 {1}'.format(now, callback_url))
        else:
            self._appendLog(log_path, '[{0}] [callback] [failed] 外部回调失败 {1}: {2}'.format(now, callback_url, error_msg))
