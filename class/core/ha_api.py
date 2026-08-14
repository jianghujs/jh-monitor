# coding: utf-8

import hashlib
import hmac
import json
import os
import time
import urllib.request

from flask import request

import jh


class ha_api:

    LOG_ROOT = '/www/server/jh-monitor/logs/ha_switch'
    NONCE_TTL_SECONDS = 600
    REPORT_LOST_SECONDS = 300
    DEFAULT_SECRET = 'jh-monitor-ha-bootstrap-secret'

    pair_fields = (
        'id,pair_id,pair_name,desired_master_host_id,actual_master_host_id,status,status_text,'
        'last_report_at,current_switch_run_id,callback_url,callback_enabled,callback_status,'
        'api_secret,addtime,update_time'
    )

    state_fields = (
        'id,pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,'
        'collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,'
        'current_step,next_step,last_error,log_path,last_report_at,addtime,update_time'
    )

    run_fields = (
        'id,switch_run_id,pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,'
        'options_json,status,current_phase,current_step,next_step,last_error,step_summary,log_path,'
        'callback_status,callback_error,addtime,update_time,finish_time'
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
        for key in ('sync_files', 'run_checksum', 'allow_checksum_diff', 'checksum_confirmed', 'restore_site_setting', 'restore_plugin_setting', 'run_xtrabackup_inc_restore'):
            if key in options:
                options[key] = self._boolValue(options.get(key))
        options['promote_mysql'] = True
        return options

    def _masterHostId(self, pair_id, fallback=''):
        for state in self._displayStates(self._getStates(pair_id)):
            if state.get('role') == 'master':
                return state.get('host_id') or fallback
        return fallback

    def _createSwitchRun(self, pair, target_host_id, phase, current_step, next_step, status, options, action_text, old_master_host_id=''):
        pair_id = pair.get('pair_id')
        switch_run_id = self._runId()
        old_master = old_master_host_id or self._masterHostId(pair_id, pair.get('actual_master_host_id') or '')
        log_path = self._monthLogPath(switch_run_id)
        now = self._now()
        jh.M('ha_switch_run').add(
            'switch_run_id,pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,options_json,status,current_phase,current_step,next_step,log_path,callback_status,addtime,update_time',
            (switch_run_id, pair_id, old_master, target_host_id, target_host_id, json.dumps(options, ensure_ascii=False), status, phase, current_step, next_step, log_path, 'pending', now, now)
        )
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).save(
            'desired_master_host_id,current_switch_run_id,status,status_text,update_time',
            (target_host_id, switch_run_id, 'switching', current_step, now)
        )
        self._appendLog(log_path, '[{0}] [system] [pending] 创建切换任务 {1}，动作 {2}，目标主机 {3}'.format(now, switch_run_id, action_text, target_host_id))
        self._appendLog(log_path, '[{0}] [system] [pending] {1}'.format(now, self._switchOptionsSummary(options)))
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
                'addtime': 'TEXT', 'update_time': 'TEXT'
            },
            'ha_host_state': {
                'pair_id': 'TEXT', 'host_id': 'TEXT', 'host_name': 'TEXT', 'host_ip': 'TEXT',
                'role': 'TEXT', 'online_status': "TEXT DEFAULT 'unknown'", 'health_status': "TEXT DEFAULT 'unknown'",
                'collect_status': "TEXT DEFAULT 'unknown'", 'collect_method': 'TEXT', 'report_host_id': 'TEXT',
                'site_scope': 'TEXT', 'health_detail': 'TEXT', 'switch_run_id': 'TEXT', 'switch_phase': 'TEXT', 'switch_status': 'TEXT',
                'current_step': 'TEXT', 'next_step': 'TEXT', 'last_error': 'TEXT', 'log_path': 'TEXT',
                'last_report_at': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT'
            },
            'ha_switch_run': {
                'switch_run_id': 'TEXT', 'pair_id': 'TEXT', 'old_master_host_id': 'TEXT',
                'new_master_host_id': 'TEXT', 'desired_master_host_id': 'TEXT', 'options_json': 'TEXT',
                'status': "TEXT DEFAULT 'pending'", 'current_phase': 'TEXT', 'current_step': 'TEXT',
                'next_step': 'TEXT', 'last_error': 'TEXT', 'step_summary': 'TEXT', 'log_path': 'TEXT',
                'callback_status': 'TEXT', 'callback_error': 'TEXT', 'addtime': 'TEXT', 'update_time': 'TEXT',
                'finish_time': 'TEXT'
            },
            'ha_switch_event': {
                'switch_run_id': 'TEXT', 'pair_id': 'TEXT', 'event_id': 'TEXT', 'origin_host_id': 'TEXT',
                'report_host_id': 'TEXT', 'collect_method': 'TEXT', 'seq': 'INTEGER DEFAULT 0', 'phase': 'TEXT',
                'step': 'TEXT', 'status': 'TEXT', 'log_text': 'TEXT', 'addtime': 'TEXT'
            },
            'ha_callback_record': {
                'pair_id': 'TEXT', 'switch_run_id': 'TEXT', 'callback_url': 'TEXT', 'status': 'TEXT',
                'error_msg': 'TEXT', 'request_body': 'TEXT', 'response_body': 'TEXT', 'addtime': 'TEXT',
                'update_time': 'TEXT'
            },
            'ha_api_nonce': {'nonce': 'TEXT', 'pair_id': 'TEXT', 'addtime': 'INTEGER'}
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
            'CREATE UNIQUE INDEX IF NOT EXISTS idx_ha_api_nonce_nonce ON ha_api_nonce(nonce)'
        ]
        for sql in indexes:
            try:
                db.originExecute(sql)
            except Exception:
                pass
        return True

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
            'addtime': run.get('addtime') or '',
            'update_time': run.get('update_time') or '',
            'finish_time': run.get('finish_time') or ''
        }

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

    def _displayStates(self, states):
        grouped = {}
        for row in states:
            key = row.get('host_ip') or row.get('host_id') or str(row.get('id'))
            grouped.setdefault(key, []).append(row)
        result = []
        for rows in grouped.values():
            selected = rows[0]
            for row in rows[1:]:
                if self._hostStateScore(row) > self._hostStateScore(selected):
                    selected = row
            local_rows = [row for row in rows if row.get('collect_method') == 'local']
            if local_rows:
                selected = local_rows[0]
                for row in local_rows[1:]:
                    if self._hostStateScore(row) > self._hostStateScore(selected):
                        selected = row
            item = dict(selected)
            alias_ids = []
            alias_names = []
            alias_roles = []
            alias_collect_methods = []
            for row in rows:
                if row.get('host_id') and row.get('host_id') not in alias_ids:
                    alias_ids.append(row.get('host_id'))
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
        role = row.get('role') or 'unknown'
        script_checks = self._normalizeScriptChecks(detail)
        display_name = self._displayHostName(row, pair)
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
            'script_checks': script_checks,
            'switch_run_id': row.get('switch_run_id') or '',
            'switch_phase': row.get('switch_phase') or '',
            'switch_status': row.get('switch_status') or '',
            'current_step': row.get('current_step') or '',
            'next_step': row.get('next_step') or '',
            'last_error': row.get('last_error') or '',
            'log_path': row.get('log_path') or '',
            'last_report_at': row.get('last_report_at') or ''
        }

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
        masters = [x for x in states if x.get('role') == 'master']
        online = dict([(x.get('host_id'), x.get('online_status')) for x in states])
        warnings = []
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
            if item.get('health_status') in ('warning', 'danger', 'failed'):
                detail = self._jsonLoads(item.get('health_detail'), {})
                warnings.append(detail.get('summary') or '{0} 自检提醒'.format(self._displayHostName(item, pair)))
        desired = pair.get('desired_master_host_id') or ''
        actual_aliases = masters[0].get('_alias_host_ids') or [masters[0].get('host_id')] if len(masters) == 1 else []
        if desired and actual_aliases and desired not in actual_aliases:
            danger.append('期望主机和实际主机不一致')
        if danger:
            return 'danger', '；'.join(danger[:3])
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
            if host.get('role') == 'master' or 'master' in (host.get('host_alias_roles') or []):
                actual_master = host.get('host_id')
                break
        desired_master = pair.get('desired_master_host_id') or actual_master
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
        data['switch_events'] = []
        if data['switch_run_id']:
            run = self._getRun(data['switch_run_id'])
            data['switch_run'] = self._normalizeRun(run)
            data['log_path'] = run.get('log_path') or ''
            if include_events:
                data['switch_events'] = [self._normalizeEvent(x) for x in self._getEvents(data['switch_run_id'])]
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
        rows = jh.M('ha_pair').field(self.pair_fields).order('id desc').select()
        if not isinstance(rows, list):
            rows = []
        return jh.returnJson(True, 'ok', {'list': [self._normalizePair(row, include_log=False, include_events=False) for row in rows]})

    def getDetailApi(self):
        pair_id = request.form.get('pair_id', '').strip()
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        return jh.returnJson(True, 'ok', self._normalizePair(pair, include_log=True, include_events=True))

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
        if phase_status in ('failed', 'error'):
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,last_error,update_time', ('waiting_retry', phase, step, step, now))
            return 'waiting_retry'
        if phase_status not in ('done', 'success'):
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,update_time', ('running', phase, step, now))
            return 'running'
        if phase == 'prepare_online':
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,next_step,update_time,finish_time', ('prepare_success', phase, step or '预上线完成', '等待操作员执行正式上线', now, now))
            jh.M('ha_pair').where('pair_id=?', (run.get('pair_id'),)).save('status,status_text,last_report_at,update_time', ('normal', '预上线完成，等待正式上线', now, now))
            return 'prepare_success'
        if phase == 'offline':
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,next_step,update_time', ('pending_online', 'online', '等待目标主机领取上线阶段', '目标主机正式上线', now))
            return 'pending_online'
        if phase == 'online':
            jh.M('ha_switch_run').where('switch_run_id=?', (run.get('switch_run_id'),)).save('status,current_phase,current_step,last_error,update_time,finish_time', ('success', phase, step or '正式上线完成', '', now, now))
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
        if action == 'prepare':
            data = self._createSwitchRun(pair, target_host_id, 'prepare_online', '等待目标主机领取预上线阶段', '预上线完成后执行正式上线', 'pending_prepare', options, '预上线')
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
        data = self._createSwitchRun(pair, finalize_target_host_id, 'offline', '等待旧主机领取下线阶段', '目标主机上线阶段', 'pending_finalize', options, '正式上线', old_master_host_id)
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
            jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (pair_id, pair_name, master_id, api_secret, 'unknown', '等待插件上报', now, now))
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
            json.dumps(host.get('health_detail') or {}, ensure_ascii=False),
            self._safeText(host.get('switch_run_id') or '', 128),
            self._safeText(host.get('switch_phase') or '', 64),
            self._safeText(host.get('switch_status') or '', 64),
            self._safeText(host.get('current_step') or '', 255),
            self._safeText(host.get('next_step') or '', 255),
            self._safeText(host.get('last_error') or '', 512),
            self._safeText(host.get('log_path') or '', 512),
            now,
            now
        )
        if isinstance(exists, dict) and exists.get('id'):
            jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).save(
                'host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,current_step,next_step,last_error,log_path,last_report_at,update_time', values
            )
        else:
            jh.M('ha_host_state').add(
                'pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,site_scope,health_detail,switch_run_id,switch_phase,switch_status,current_step,next_step,last_error,log_path,last_report_at,addtime,update_time',
                (pair_id, host_id) + values + (now,)
            )

    def publicPullDesiredState(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        host_id = self._safeText(payload.get('host_id'), 128)
        pair = self._getPair(payload.get('pair_id'))
        if not pair:
            return jh.returnJson(False, 'unknown pair_id')
        run = {}
        if pair.get('current_switch_run_id'):
            run = self._getRun(pair.get('current_switch_run_id'))
            if run:
                phase = run.get('current_phase') or ''
                if phase == 'prepare_online':
                    run['execute_phase'] = 'prepare_online' if host_id == run.get('new_master_host_id') else ''
                    run['execute_role'] = 'master'
                elif phase == 'offline':
                    run['execute_phase'] = 'offline' if host_id == run.get('old_master_host_id') else ''
                    run['execute_role'] = 'standby'
                elif phase == 'online':
                    run['execute_phase'] = 'online' if host_id == run.get('new_master_host_id') else ''
                    run['execute_role'] = 'master'
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
        for host in hosts:
            self._upsertState(pair_id, host, host.get('role') or host.get('actual_role') or 'unknown', now)
        states = self._displayStates(self._getStates(pair_id))
        pair = self._getPair(pair_id)
        status, status_text = self.deriveStatus(pair, states)
        actual = ''
        for state in states:
            if state.get('role') == 'master':
                actual = state.get('host_id')
                break
        desired = self._safeText(payload.get('desired_master_host_id') or '', 128)
        current_run = self._getRun(pair.get('current_switch_run_id') or '') if pair.get('current_switch_run_id') else {}
        if current_run.get('status') == 'prepare_success':
            desired = ''
        if desired:
            pair['desired_master_host_id'] = desired
            status, status_text = self.deriveStatus(pair, states)
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('desired_master_host_id,actual_master_host_id,status,status_text,last_report_at,update_time', (desired, actual, status, status_text, now, now))
        else:
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('actual_master_host_id,status,status_text,last_report_at,update_time', (actual, status, status_text, now, now))
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
        line = '[{0}] [{1}] [{2}] [{3}] {4}'.format(now, origin_host_id or 'unknown', phase or 'event', status or 'info', log_text or step)
        self._appendLog(run.get('log_path'), line)
        db_status = self._advanceSwitchRun(run, phase, status, step or log_text)
        return jh.returnJson(True, '事件已上报')

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
