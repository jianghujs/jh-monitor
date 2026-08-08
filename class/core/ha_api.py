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
        'collect_method,report_host_id,health_detail,switch_run_id,switch_phase,switch_status,'
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
                'health_detail': 'TEXT', 'switch_run_id': 'TEXT', 'switch_phase': 'TEXT', 'switch_status': 'TEXT',
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

    def _normalizeHost(self, row):
        detail = self._jsonLoads(row.get('health_detail'), {})
        role = row.get('role') or 'unknown'
        return {
            'host_id': row.get('host_id') or '',
            'name': row.get('host_name') or row.get('host_id') or '',
            'host_name': row.get('host_name') or row.get('host_id') or '',
            'ip': row.get('host_ip') or '',
            'host_ip': row.get('host_ip') or '',
            'role': role,
            'online': row.get('online_status') or 'unknown',
            'online_status': row.get('online_status') or 'unknown',
            'health_status': row.get('health_status') or 'unknown',
            'collect_status': row.get('collect_status') or 'unknown',
            'collect_method': row.get('collect_method') or '',
            'report_host_id': row.get('report_host_id') or '',
            'health_detail': detail,
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
        running = jh.M('ha_switch_run').where(
            'pair_id=? AND status IN (?,?,?)', (pair.get('pair_id'), 'pending', 'running', 'waiting_retry')
        ).field(self.run_fields).find()
        if isinstance(running, dict) and running.get('switch_run_id'):
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
                    if int(time.time() - ts) > self.REPORT_LOST_SECONDS and item.get('role') == 'master':
                        danger.append('{0} 插件失联'.format(item.get('host_name') or item.get('host_id')))
                except Exception:
                    pass
            if item.get('role') == 'master' and item.get('online_status') == 'offline':
                danger.append('{0} 主机离线'.format(item.get('host_name') or item.get('host_id')))
            if item.get('collect_status') in ('failed', 'partial'):
                warnings.append('{0} SSH采集异常'.format(item.get('host_name') or item.get('host_id')))
            if item.get('health_status') in ('warning', 'danger', 'failed'):
                detail = self._jsonLoads(item.get('health_detail'), {})
                warnings.append(detail.get('summary') or '{0} 自检提醒'.format(item.get('host_name') or item.get('host_id')))
        desired = pair.get('desired_master_host_id') or ''
        actual = masters[0].get('host_id') if len(masters) == 1 else ''
        if desired and actual and desired != actual:
            danger.append('期望主机和实际主机不一致')
        if danger:
            return 'danger', '；'.join(danger[:3])
        if warnings:
            return 'warning', '；'.join(warnings[:3])
        if any([v == 'offline' for v in online.values()]):
            return 'warning', '备用机或对端离线'
        return 'normal', '状态正常'

    def _normalizePair(self, pair):
        states = self._getStates(pair.get('pair_id'))
        status, status_text = self.deriveStatus(pair, states)
        hosts = [self._normalizeHost(x) for x in states]
        actual_master = ''
        for host in hosts:
            if host.get('role') == 'master':
                actual_master = host.get('host_id')
                break
        data = dict(pair)
        data['status'] = status
        data['status_text'] = status_text
        data['hosts'] = hosts
        data['actual_master_host_id'] = actual_master or pair.get('actual_master_host_id') or ''
        data['desired_master_host_id'] = pair.get('desired_master_host_id') or data['actual_master_host_id']
        data['switch_run_id'] = pair.get('current_switch_run_id') or ''
        data['log_path'] = ''
        if data['switch_run_id']:
            run = self._getRun(data['switch_run_id'])
            data['log_path'] = run.get('log_path') or ''
        data['health'] = self._summaryHealth(hosts)
        data['warnings'] = [] if status == 'normal' else status_text.split('；')
        data['log'] = self._readLogText(data.get('log_path')) if data.get('log_path') else ''
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
        return jh.returnJson(True, 'ok', {'list': [self._normalizePair(row) for row in rows]})

    def getDetailApi(self):
        pair_id = request.form.get('pair_id', '').strip()
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        return jh.returnJson(True, 'ok', self._normalizePair(pair))

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

    def requestSwitchApi(self):
        self.ensureHaSchema()
        pair_id = request.form.get('pair_id', '').strip()
        target_host_id = request.form.get('target_host_id', '').strip() or request.form.get('desired_master_host_id', '').strip()
        pair = self._getPair(pair_id)
        if not pair:
            return jh.returnJson(False, '主备关系不存在')
        if not target_host_id:
            return jh.returnJson(False, '目标主机不能为空')
        switch_run_id = self._runId()
        old_master = pair.get('actual_master_host_id') or ''
        states = self._getStates(pair_id)
        for state in states:
            if state.get('role') == 'master':
                old_master = state.get('host_id')
                break
        options = self._bodyJson()
        options.pop('pair_id', None)
        options.pop('target_host_id', None)
        log_path = self._monthLogPath(switch_run_id)
        now = self._now()
        jh.M('ha_switch_run').add(
            'switch_run_id,pair_id,old_master_host_id,new_master_host_id,desired_master_host_id,options_json,status,current_phase,current_step,next_step,log_path,callback_status,addtime,update_time',
            (switch_run_id, pair_id, old_master, target_host_id, target_host_id, json.dumps(options, ensure_ascii=False), 'pending', 'offline', '等待旧主机领取下线阶段', '目标主机上线阶段', log_path, 'pending', now, now)
        )
        jh.M('ha_pair').where('pair_id=?', (pair_id,)).save(
            'desired_master_host_id,current_switch_run_id,status,status_text,update_time',
            (target_host_id, switch_run_id, 'switching', '等待插件执行切换', now)
        )
        self._appendLog(log_path, '[{0}] [system] [pending] 创建切换任务 {1}，目标主机 {2}'.format(now, switch_run_id, target_host_id))
        return jh.returnJson(True, '切换任务已创建', {'switch_run_id': switch_run_id, 'log_path': log_path})

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
        return jh.returnJson(True, 'ok', {'log_path': log_path, 'offset': offset, 'next_offset': next_offset, 'content': text})

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
            jh.M('ha_pair').where('pair_id=?', (pair_id,)).save('pair_name,desired_master_host_id,api_secret,update_time', (pair_name, master_id, api_secret, now))
        else:
            jh.M('ha_pair').add('pair_id,pair_name,desired_master_host_id,api_secret,status,status_text,addtime,update_time', (pair_id, pair_name, master_id, api_secret, 'unknown', '等待插件上报', now, now))
        for host in (local, peer):
            if isinstance(host, dict) and host.get('host_id'):
                self._upsertState(pair_id, host, host.get('role') or ('master' if host.get('host_id') == master_id else 'standby'), now)
        return jh.returnJson(True, '注册成功', {'pair_id': pair_id, 'api_secret': api_secret})

    def _upsertState(self, pair_id, host, role, now):
        host_id = self._safeText(host.get('host_id'), 128)
        exists = jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).field('id').find()
        values = (
            self._safeText(host.get('host_name') or host.get('name') or host_id, 128),
            self._safeText(host.get('host_ip') or host.get('ip'), 64),
            self._safeText(role, 32),
            self._safeText(host.get('online_status') or host.get('online') or 'unknown', 32),
            self._safeText(host.get('health_status') or 'unknown', 32),
            self._safeText(host.get('collect_status') or 'unknown', 32),
            self._safeText(host.get('collect_method') or '', 32),
            self._safeText(host.get('report_host_id') or '', 128),
            json.dumps(host.get('health_detail') or {}, ensure_ascii=False),
            now,
            now
        )
        if isinstance(exists, dict) and exists.get('id'):
            jh.M('ha_host_state').where('pair_id=? AND host_id=?', (pair_id, host_id)).save(
                'host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,health_detail,last_report_at,update_time', values
            )
        else:
            jh.M('ha_host_state').add(
                'pair_id,host_id,host_name,host_ip,role,online_status,health_status,collect_status,collect_method,report_host_id,health_detail,last_report_at,addtime,update_time',
                (pair_id, host_id) + values + (now,)
            )

    def publicPullDesiredState(self):
        ok, payload, msg = self._publicPayload(True)
        if not ok:
            return jh.returnJson(False, msg)
        pair = self._getPair(payload.get('pair_id'))
        if not pair:
            return jh.returnJson(False, 'unknown pair_id')
        run = {}
        if pair.get('current_switch_run_id'):
            run = self._getRun(pair.get('current_switch_run_id'))
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
        states = self._getStates(pair_id)
        pair = self._getPair(pair_id)
        status, status_text = self.deriveStatus(pair, states)
        actual = ''
        for state in states:
            if state.get('role') == 'master':
                actual = state.get('host_id')
                break
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
        db_status = 'running'
        if status in ('failed', 'error'):
            db_status = 'waiting_retry'
        elif status in ('success', 'done') and phase in ('online', 'callback'):
            db_status = 'success'
        jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save('status,current_phase,current_step,last_error,update_time,finish_time', (db_status, phase, step or log_text, log_text if db_status == 'waiting_retry' else '', now, now if db_status == 'success' else ''))
        if db_status == 'success':
            self._executeCallbacks(pair_id, switch_run_id)
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
        status = 'running'
        if phase_status in ('failed', 'error'):
            status = 'waiting_retry'
        elif phase_status in ('done', 'success') and phase == 'online':
            status = 'success'
        jh.M('ha_switch_run').where('switch_run_id=?', (switch_run_id,)).save('status,current_phase,current_step,last_error,update_time,finish_time', (status, phase, step, payload.get('last_error') or '', now, now if status == 'success' else ''))
        self._appendLog(run.get('log_path'), '[{0}] [{1}] [{2}] {3}'.format(now, phase or 'phase', phase_status or status, step or '阶段确认'))
        if status == 'success':
            self._executeCallbacks(run.get('pair_id'), switch_run_id)
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
