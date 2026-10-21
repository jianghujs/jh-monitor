# coding: utf-8

import concurrent.futures
import datetime
import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'class/core'))

from flask import Flask, session
from api_key_auth import AuthError, authorize_request, panel_api_open, resolve_credentials
from api_key_routes import is_external_route, register_api_key_routes
from api_key_store import ApiKeyStore, ApiKeyError
from api_permissions import route_scope


class CredentialTests(unittest.TestCase):
    """凭据解析：总密钥签名与带权限的调用密钥共用一处。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ApiKeyStore(self.temp.name + '/test.db', self.temp.name + '/master.key')
        self.store.migrate()
        self.api_config = self.temp.name + '/api.json'
        self.token_crypt = 'xcrypt-token'
        self.write_config(open_api=True, limit_addr=['10.0.0.9'])

    def tearDown(self):
        self.temp.cleanup()

    def write_config(self, open_api, limit_addr):
        with io.open(self.api_config, 'w', encoding='utf-8') as f:
            json.dump({'open': open_api, 'token': 'secret-hash', 'token_crypt': self.token_crypt,
                       'limit_addr': limit_addr, 'key': 'panel-key'}, f)

    def signature(self, request_time='1700000000'):
        inner = hashlib.md5(self.token_crypt.encode()).hexdigest()
        return hashlib.md5((str(request_time) + inner).encode()).hexdigest()

    def resolve(self, headers=None, form=None, remote_addr='10.0.0.9'):
        return resolve_credentials(headers or {}, form or {}, remote_addr, self.store, self.api_config)

    def test_permission_registry_maps_route_to_scope(self):
        self.assertEqual(route_scope('GET', '/host/api/list'), 'host:read')
        self.assertIsNone(route_scope('POST', '/host/api/list'))
        self.assertEqual(route_scope('GET', '/ha/api/local/relationships'), 'ha:read')
        self.assertIsNone(route_scope('POST', '/ha/api/local/relationships'))
        self.assertIsNone(route_scope('GET', '/api/config_api/get'))

    def test_missing_or_closed_panel_api_is_rejected(self):
        self.write_config(open_api=False, limit_addr=['10.0.0.9'])
        self.assertFalse(panel_api_open(self.api_config))
        with self.assertRaises(AuthError) as raised:
            self.resolve(headers={'Authorization': 'Bearer x'})
        self.assertEqual(raised.exception.status, 403)
        self.write_config(open_api=True, limit_addr=['10.0.0.9'])
        with self.assertRaises(AuthError) as raised:
            self.resolve()
        self.assertEqual(raised.exception.status, 401)

    def test_master_key_requires_signature_and_ip_whitelist(self):
        good = {'request_time': '1700000000', 'request_token': self.signature()}
        self.assertEqual(self.resolve(form=good)['mode'], 'master')
        with self.assertRaises(AuthError) as raised:
            self.resolve(form={'request_time': '1700000000', 'request_token': 'bad'})
        self.assertEqual(raised.exception.status, 401)
        with self.assertRaises(AuthError) as raised:
            self.resolve(form=good, remote_addr='10.0.0.10')
        self.assertEqual(raised.exception.status, 403)

    def test_key_mode_reports_scopes_and_blocks_disabled_or_expired(self):
        created = self.store.create({'name': '外部系统', 'scopes': ['ha:read']})
        credential = self.resolve(headers={'Authorization': 'Bearer ' + created['key']})
        self.assertEqual(credential['mode'], 'key')
        self.assertEqual(credential['scopes'], ['ha:read'])
        self.store.update(created['key_id'], {'name': '外部系统', 'scopes': ['ha:read'], 'is_enabled': False})
        with self.assertRaises(ApiKeyError) as raised:
            self.resolve(headers={'Authorization': 'Bearer ' + created['key']})
        self.assertEqual(raised.exception.status, 401)
        self.store.update(created['key_id'], {'name': '外部系统', 'scopes': ['ha:read'], 'is_enabled': True,
                                              'expires_at': '2000-01-01T00:00:00+00:00'})
        with self.assertRaises(ApiKeyError):
            self.resolve(headers={'Authorization': 'Bearer ' + created['key']})

    def test_admin_key_ignores_scopes_while_normal_key_needs_permission(self):
        admin = self.store.create({'name': '管理密钥', 'key_type': 'admin', 'scopes': ['ha:read']})
        credential = authorize_request({'Authorization': 'Bearer ' + admin['key']}, {}, '10.0.0.9',
                                       self.store, self.api_config, 'GET', '/api/config_api/get')
        self.assertEqual(credential['key_type'], 'admin')
        normal = self.store.create({'name': '普通密钥', 'key_type': 'normal', 'scopes': []})
        with self.assertRaises(AuthError) as raised:
            authorize_request({'Authorization': 'Bearer ' + normal['key']}, {}, '10.0.0.9',
                              self.store, self.api_config, 'GET', '/ha/api/local/relationships')
        self.assertEqual(raised.exception.status, 403)

    def test_key_type_must_be_admin_or_normal(self):
        with self.assertRaises(ApiKeyError):
            self.store.create({'name': '类型错误', 'key_type': 'super'})


class ReadRouteTests(unittest.TestCase):
    """只读关系接口与设置页管理接口的实际行为。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ApiKeyStore(self.temp.name + '/test.db', self.temp.name + '/master.key')
        self.store.migrate()
        self.api_config = self.temp.name + '/api.json'
        self.token_crypt = 'xcrypt-token'
        self.write_config(open_api=True, limit_addr=['127.0.0.1'])
        with self.store.connect() as db:
            db.executescript('''CREATE TABLE ha_pair(id INTEGER PRIMARY KEY,pair_id TEXT,pair_name TEXT,status TEXT,status_text TEXT,local_type TEXT);
            CREATE TABLE ha_host_state(id INTEGER PRIMARY KEY,pair_id TEXT,host_id TEXT,host_name TEXT,role TEXT,online_status TEXT,health_status TEXT,collect_status TEXT,last_report_at TEXT,update_time TEXT,switch_task_id TEXT);
            CREATE TABLE ha_switch_task(switch_task_id TEXT,pair_id TEXT,status TEXT);
            INSERT INTO ha_pair VALUES(1,'p','Dev02','normal','ok','local'),(2,'empty','Empty','normal','ok','local'),(3,'legacy','Dev02','normal','ok',NULL);
            INSERT INTO ha_host_state VALUES(1,'p','h','Dev02@Polaris','standby','online','normal','success','2020-01-01 00:00:00','2020-01-01 00:00:01','t');
            INSERT INTO ha_switch_task VALUES('t','p','running');''')
        self.app = Flask(__name__)
        self.app.secret_key = 'test-only'
        register_api_key_routes(self.app, self.store, lambda: session.get('admin', False), self.api_config)
        self.client = self.app.test_client()

    def tearDown(self):
        self.temp.cleanup()

    def write_config(self, open_api, limit_addr):
        with io.open(self.api_config, 'w', encoding='utf-8') as f:
            json.dump({'open': open_api, 'token': 'secret-hash', 'token_crypt': self.token_crypt,
                       'limit_addr': limit_addr, 'key': 'panel-key'}, f)

    def signature_headers(self, request_time='1700000000'):
        inner = hashlib.md5(self.token_crypt.encode()).hexdigest()
        return {'request_time': str(request_time),
                'request_token': hashlib.md5((str(request_time) + inner).encode()).hexdigest()}

    def admin_csrf(self):
        with self.client.session_transaction() as s:
            s['admin'] = True
        response = self.client.post('/config/get_api_keys', environ_base={'REMOTE_ADDR': '127.0.0.1'})
        return response.json['data']['csrf_token']

    def post(self, url, data, csrf=None):
        payload = dict(data)
        if csrf:
            payload['csrf_token'] = csrf
        return self.client.post(url, data=payload,
                                headers={'Origin': 'http://localhost'},
                                environ_base={'REMOTE_ADDR': '127.0.0.1'})

    def get_relationships(self, headers=None):
        return self.client.get('/ha/api/local/relationships', headers=headers or {},
                               environ_base={'REMOTE_ADDR': '127.0.0.1'})

    def test_external_route_is_separate_from_page_routes(self):
        self.assertTrue(is_external_route('/host/api/list'))
        self.assertTrue(is_external_route('/ha/api/local/relationships'))
        for path in ['/ha/api/local/list', '/config/get_api_keys', '/api/config_api/get']:
            self.assertFalse(is_external_route(path))

    def prepare_inventory(self):
        with self.store.connect() as db:
            db.executescript('''
                CREATE TABLE host(id INTEGER PRIMARY KEY,host_id TEXT,host_name TEXT,
                    host_group_id TEXT,ip TEXT,os TEXT,is_jhpanel BOOLEAN,is_pve BOOLEAN,
                    is_master BOOLEAN,backup_host_id TEXT,ssh_pkey TEXT,remark TEXT);
                CREATE TABLE host_group(host_group_id TEXT,host_group_name TEXT);
                INSERT INTO host_group VALUES('g','Room A');
                INSERT INTO host VALUES(1,'h1','Server A','g','10.0.0.1','Debian',1,0,1,'h2','SECRET','PRIVATE');
                INSERT INTO host VALUES(2,'h2','Server B','missing','10.0.0.2','Linux',0,1,NULL,NULL,'SECRET','PRIVATE');
            ''')

    def test_host_scope_ui_and_public_snapshot(self):
        self.prepare_inventory()
        self.admin_csrf()
        self.assertEqual(self.client.get('/config/get_api_keys').json['data']['scopes']['host:read'],
                         '读取云监控主机列表')
        created = self.store.create({'name': 'Holmes', 'scopes': ['host:read']})
        auth = {'Authorization': 'Bearer ' + created['key']}
        with self.store.connect() as db:
            before = list(db.iterdump())
        result = self.client.get('/host/api/list', headers=auth)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.headers['Cache-Control'], 'no-store')
        data = result.json['data']
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['schema_version'], 1)
        self.assertIsNotNone(datetime.datetime.fromisoformat(data['snapshot_at']).tzinfo)
        self.assertEqual(set(data['list'][0]), {'host_id', 'host_name', 'host_group_id',
                         'host_group_name', 'group_resolved', 'ip', 'os', 'is_jhpanel',
                         'is_pve', 'is_master', 'backup_host_id'})
        self.assertEqual(data['list'][0]['host_group_name'], 'Room A')
        self.assertTrue(data['list'][0]['group_resolved'])
        self.assertIs(data['list'][0]['is_pve'], False)
        self.assertFalse(data['list'][1]['group_resolved'])
        self.assertIsNone(data['list'][1]['host_group_name'])
        self.assertNotIn('SECRET', result.get_data(as_text=True))
        self.assertNotIn('PRIVATE', result.get_data(as_text=True))
        with self.store.connect() as db:
            # Authentication may update only API key usage; inventory must be unchanged.
            after = list(db.iterdump())
        self.assertEqual([s for s in before if 'INSERT INTO "host' in s],
                         [s for s in after if 'INSERT INTO "host' in s])
        self.assertEqual(self.get_relationships(auth).status_code, 403)

    def test_host_route_auth_and_empty_inventory(self):
        self.prepare_inventory()
        self.assertEqual(self.client.get('/host/api/list').status_code, 401)
        self.assertEqual(self.client.get('/host/api/list', headers={'Authorization': 'Bearer invalid'}).status_code, 401)
        ha = self.store.create({'name': 'HA only', 'scopes': ['ha:read']})
        self.assertEqual(self.client.get('/host/api/list', headers={'Authorization': 'Bearer ' + ha['key']}).status_code, 403)
        key = self.store.create({'name': 'Inventory', 'scopes': ['host:read']})
        auth = {'Authorization': 'Bearer ' + key['key']}
        with self.store.connect() as db:
            db.execute('DELETE FROM host')
        self.assertEqual(self.client.get('/host/api/list', headers=auth).json['data']['list'], [])
        admin = self.store.create({'name': 'Admin', 'key_type': 'admin'})
        self.assertEqual(self.client.get('/host/api/list', headers={'Authorization': 'Bearer ' + admin['key']}).status_code, 200)
        self.assertEqual(self.client.get('/host/api/list', query_string=self.signature_headers(),
                                        environ_base={'REMOTE_ADDR': '127.0.0.1'}).status_code, 200)
        self.store.update(key['key_id'], {'name': 'Inventory', 'scopes': ['host:read'], 'is_enabled': False})
        self.assertEqual(self.client.get('/host/api/list', headers=auth).status_code, 401)
        self.write_config(open_api=False, limit_addr=[])
        self.assertEqual(self.client.get('/host/api/list', headers=auth).status_code, 403)

    def test_scoped_key_returns_snapshot_and_master_signature_also_works(self):
        created = self.store.create({'name': '数据同步', 'scopes': ['ha:read']})
        response = self.get_relationships({'Authorization': 'Bearer ' + created['key']})
        self.assertEqual(response.status_code, 200)
        payload = response.json
        self.assertTrue(payload['status'])
        self.assertEqual(payload['data']['schema_version'], 1)
        self.assertEqual(len(payload['data']['list']), 2)
        host = payload['data']['list'][0]['hosts'][0]
        self.assertEqual(host['role'], 'standby')
        self.assertTrue(host['received_at'].startswith('2020-'))
        self.assertEqual(payload['data']['list'][1]['hosts'], [])
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        master = self.client.get('/ha/api/local/relationships', query_string=self.signature_headers(),
                                 environ_base={'REMOTE_ADDR': '127.0.0.1'})
        self.assertEqual(master.status_code, 200)
        self.assertEqual(master.json['data']['schema_version'], 1)

    def test_admin_key_reads_relationships_without_registered_scope(self):
        created = self.store.create({'name': '管理密钥', 'key_type': 'admin'})
        response = self.get_relationships({'Authorization': 'Bearer ' + created['key']})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json['status'])

    def test_historical_running_task_does_not_override_current_success(self):
        created = self.store.create({'name': 'snapshot', 'scopes': ['ha:read']})
        with self.store.connect() as db:
            db.execute("INSERT INTO ha_switch_task VALUES('new','p','success')")
            db.execute("UPDATE ha_host_state SET switch_task_id='new' WHERE pair_id='p'")
        payload = self.get_relationships({'Authorization': 'Bearer ' + created['key']}).json
        pair = payload['data']['list'][0]
        self.assertEqual(pair['status'], 'normal')
        self.assertEqual(pair['hosts'][0]['switch_task_status'], 'success')
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT status FROM ha_switch_task WHERE switch_task_id='t'").fetchone()[0], 'running')

    def test_current_pending_or_running_task_still_blocks(self):
        created = self.store.create({'name': 'snapshot', 'scopes': ['ha:read']})
        for status in ('pending', 'running'):
            with self.store.connect() as db:
                db.execute("UPDATE ha_switch_task SET status=? WHERE switch_task_id='t'", (status,))
            pair = self.get_relationships({'Authorization': 'Bearer ' + created['key']}).json['data']['list'][0]
            self.assertEqual(pair['status'], 'switching')
            self.assertEqual(pair['hosts'][0]['switch_task_status'], status)

    def test_auth_failures_are_json_with_status_codes(self):
        created = self.store.create({'name': '无权限', 'scopes': []})
        response = self.get_relationships({'Authorization': 'Bearer ' + created['key']})
        self.assertEqual(response.status_code, 403)
        self.assertFalse(response.json['status'])
        self.assertEqual(self.get_relationships().status_code, 401)
        self.assertEqual(self.get_relationships({'Authorization': 'Bearer jhm_bad'}).status_code, 401)
        wrong_ip = self.client.get('/ha/api/local/relationships', query_string=self.signature_headers(),
                                   environ_base={'REMOTE_ADDR': '10.1.1.1'})
        self.assertEqual(wrong_ip.status_code, 403)
        self.assertNotIn('text/html', response.headers.get('Content-Type', ''))

    def test_key_is_unavailable_when_panel_api_switch_is_off(self):
        created = self.store.create({'name': '数据同步', 'scopes': ['ha:read']})
        self.write_config(open_api=False, limit_addr=[])
        response = self.get_relationships({'Authorization': 'Bearer ' + created['key']})
        self.assertEqual(response.status_code, 403)
        self.assertIn('未开启', response.json['msg'])

    def test_management_requires_admin_csrf_and_same_origin(self):
        self.assertEqual(self.client.post('/config/get_api_keys').status_code, 403)
        csrf = self.admin_csrf()
        self.assertEqual(self.post('/config/set_api_key', {'action': 'create', 'name': 'A'}).status_code, 403)
        self.assertEqual(self.client.post('/config/set_api_key', data={'action': 'create', 'name': 'A', 'csrf_token': csrf},
                                          headers={'Origin': 'http://evil.example'}).status_code, 403)
        created = self.post('/config/set_api_key', {'action': 'create', 'name': 'A', 'scopes': '["ha:read"]'}, csrf).json['data']
        listing = self.client.post('/config/get_api_keys').get_data(as_text=True)
        self.assertNotIn(created['key'], listing)
        csrf = self.admin_csrf()
        revealed = self.post('/config/set_api_key', {'action': 'reveal', 'key_id': created['key_id']}, csrf)
        self.assertEqual(revealed.json['data']['key'], created['key'])
        self.assertEqual(revealed.headers['Cache-Control'], 'no-store')
        with self.client.session_transaction() as s:
            s['tmp_login'] = True
        self.assertEqual(self.client.post('/config/get_api_keys').status_code, 403)

    def test_lifecycle_disable_and_delete_take_effect_immediately(self):
        csrf = self.admin_csrf()
        created = self.post('/config/set_api_key', {'action': 'create', 'name': 'B', 'scopes': '["ha:read"]'}, csrf).json['data']
        auth = {'Authorization': 'Bearer ' + created['key']}
        self.assertEqual(self.get_relationships(auth).status_code, 200)
        csrf = self.admin_csrf()
        self.post('/config/set_api_key', {'action': 'update', 'key_id': created['key_id'], 'name': 'B',
                                           'scopes': '["ha:read"]', 'is_enabled': '0'}, csrf)
        self.assertEqual(self.get_relationships(auth).status_code, 401)
        csrf = self.admin_csrf()
        self.post('/config/set_api_key', {'action': 'delete', 'key_id': created['key_id']}, csrf)
        self.assertEqual(self.get_relationships(auth).status_code, 401)

    def test_custom_key_route_rejects_duplicate_and_update_without_leaking_plaintext(self):
        csrf = self.admin_csrf()
        raw_key = 'Route_Custom_Key_' + ('A' * 32)
        with self.assertLogs(self.app.logger.name, level='INFO') as logs:
            created = self.post('/config/set_api_key', {
                'action': 'create', 'name': '自定义密钥', 'key': raw_key, 'scopes': '["ha:read"]'
            }, csrf)
        self.assertEqual(created.status_code, 200)
        self.assertEqual(created.json['data']['key'], raw_key)
        self.assertNotIn(raw_key, '\n'.join(logs.output))
        listing = self.client.post('/config/get_api_keys').get_data(as_text=True)
        self.assertNotIn(raw_key, listing)

        csrf = self.admin_csrf()
        duplicate = self.post('/config/set_api_key', {
            'action': 'create', 'name': '重复密钥', 'key': raw_key, 'scopes': '["ha:read"]'
        }, csrf)
        self.assertEqual(duplicate.status_code, 409)
        self.assertNotIn(raw_key, duplicate.get_data(as_text=True))

        key_id = created.json['data']['key_id']
        csrf = self.admin_csrf()
        changed_key = 'Route_Changed_Key_' + ('B' * 32)
        update = self.post('/config/set_api_key', {
            'action': 'update', 'key_id': key_id, 'name': '不能修改', 'key': changed_key,
            'scopes': '["ha:read"]'
        }, csrf)
        self.assertEqual(update.status_code, 400)
        self.assertNotIn(changed_key, update.get_data(as_text=True))
        self.assertEqual(self.store.reveal(key_id)['key'], raw_key)
        self.assertEqual(self.store.list()[0]['name'], '自定义密钥')


class StoreTests(unittest.TestCase):
    """主密钥与密文的完整性。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = ApiKeyStore(self.temp.name + '/test.db', self.temp.name + '/master.key')
        self.store.migrate()
        self.store.migrate()

    def tearDown(self):
        self.temp.cleanup()

    def test_concurrent_creation_and_master_key_integrity(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            keys = list(pool.map(lambda i: self.store.create({'name': str(i)}), range(6)))
        for key in keys:
            self.assertEqual(self.store.reveal(key['key_id'])['key'], key['key'])
        self.assertNotIn(keys[0]['key'], json.dumps(self.store.list()))
        original = Path(self.store.master_path).read_bytes()
        os.unlink(self.store.master_path)
        with self.assertRaises(ApiKeyError):
            self.store.create({'name': 'fail'})
        self.assertFalse(os.path.exists(self.store.master_path))
        with open(self.store.master_path, 'wb') as f:
            f.write(os.urandom(32))
        os.chmod(self.store.master_path, 0o600)
        with self.assertRaises(ApiKeyError):
            self.store.reveal(keys[0]['key_id'])
        with self.assertRaises(ApiKeyError):
            self.store.create({'name': 'wrong master'})
        with open(self.store.master_path, 'wb') as f:
            f.write(original)
        with self.store.connect() as db:
            db.execute('UPDATE api_key SET key_ciphertext=? WHERE key_id=?', (b'broken', keys[0]['key_id']))
        with self.assertRaises(ApiKeyError):
            self.store.reveal(keys[0]['key_id'])

    def test_unregistered_scope_is_rejected(self):
        with self.assertRaises(ApiKeyError):
            self.store.create({'name': 'bad scope', 'scopes': ['panel:admin']})

    def test_admin_key_stores_empty_scopes(self):
        created = self.store.create({'name': 'admin', 'key_type': 'admin', 'scopes': ['ha:read']})
        records = [item for item in self.store.list() if item['key_id'] == created['key_id']]
        self.assertEqual(records[0]['key_type'], 'admin')
        self.assertEqual(records[0]['scopes'], [])

    def test_auto_generated_and_custom_key_boundaries_authenticate_and_reveal(self):
        generated = [
            self.store.create({'name': '缺省'}),
            self.store.create({'name': '空字符串', 'key': ''}),
        ]
        for item in generated:
            self.assertTrue(item['key'].startswith('jhm_'))
            self.assertEqual(len(item['key']), 68)
            self.assertEqual(self.store.reveal(item['key_id'])['key'], item['key'])
            self.assertEqual(self.store.authenticate('Bearer ' + item['key'])['key_id'], item['key_id'])

        for length in (32, 68, 128):
            raw_key = 'A' + ('b' * (length - 2)) + 'Z'
            created = self.store.create({'name': '边界-%s' % length, 'key': raw_key, 'scopes': ['ha:read']})
            self.assertEqual(created['key'], raw_key)
            self.assertEqual(self.store.reveal(created['key_id'])['key'], raw_key)
            self.assertEqual(self.store.authenticate('bearer ' + raw_key)['key_id'], created['key_id'])
            with self.assertRaises(ApiKeyError) as raised:
                self.store.authenticate('Bearer ' + raw_key.swapcase())
            self.assertEqual(raised.exception.status, 401)

    def test_invalid_custom_keys_are_rejected_without_records(self):
        invalid = [
            None, False, 123, [], 'a' * 31, 'a' * 129, ' ' * 32,
            ('a' * 31) + ' ', ('a' * 31) + '\n', ('a' * 31) + '中',
            ('a' * 31) + '.', ('a' * 31) + '/',
        ]
        for index, raw_key in enumerate(invalid):
            with self.subTest(raw_key=repr(raw_key)):
                with self.assertRaises(ApiKeyError) as raised:
                    self.store.create({'name': '非法-%s' % index, 'key': raw_key})
                self.assertIn('32～128', str(raised.exception))
        self.assertEqual(self.store.list(), [])

    def test_duplicate_keys_include_disabled_expired_and_concurrent_records(self):
        disabled_key = 'Disabled_Key_' + ('D' * 32)
        disabled = self.store.create({'name': '停用记录', 'key': disabled_key, 'scopes': ['ha:read']})
        self.store.update(disabled['key_id'], {
            'name': '停用记录', 'key_type': 'normal', 'scopes': ['ha:read'], 'is_enabled': False
        })
        expired_key = 'Expired_Key_' + ('E' * 32)
        expired = self.store.create({'name': '过期记录', 'key': expired_key, 'scopes': ['ha:read']})
        self.store.update(expired['key_id'], {
            'name': '过期记录', 'key_type': 'normal', 'scopes': ['ha:read'], 'is_enabled': True,
            'expires_at': '2000-01-01T00:00:00+00:00'
        })
        for raw_key in (disabled_key, expired_key):
            with self.assertRaises(ApiKeyError) as raised:
                self.store.create({'name': '覆盖尝试', 'key': raw_key, 'key_type': 'admin'})
            self.assertEqual(raised.exception.status, 409)
        records = {item['key_id']: item for item in self.store.list()}
        self.assertEqual(records[disabled['key_id']]['name'], '停用记录')
        self.assertFalse(records[disabled['key_id']]['is_enabled'])
        self.assertEqual(records[expired['key_id']]['name'], '过期记录')
        self.assertEqual(records[expired['key_id']]['key_type'], 'normal')

        concurrent_key = 'Concurrent_Key_' + ('C' * 32)
        def create_same(index):
            try:
                return self.store.create({'name': '并发-%s' % index, 'key': concurrent_key})
            except ApiKeyError as error:
                return error
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(create_same, range(2)))
        self.assertEqual(len([item for item in results if isinstance(item, dict)]), 1)
        conflicts = [item for item in results if isinstance(item, ApiKeyError)]
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].status, 409)
        digest = hashlib.sha256(concurrent_key.encode()).hexdigest()
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM api_key WHERE key_hash=?', (digest,)).fetchone()[0], 1)

    def test_update_rejects_nonempty_key_and_preserves_metadata(self):
        raw_key = 'Original_Update_Key_' + ('O' * 32)
        created = self.store.create({'name': '原名称', 'key': raw_key, 'scopes': ['ha:read']})
        with self.assertRaises(ApiKeyError):
            self.store.update(created['key_id'], {
                'name': '新名称', 'key': 'Changed_Update_Key_' + ('N' * 32), 'scopes': []
            })
        record = self.store.list()[0]
        self.assertEqual(record['name'], '原名称')
        self.assertEqual(record['scopes'], ['ha:read'])
        self.assertEqual(self.store.reveal(created['key_id'])['key'], raw_key)


class IndependentDeploymentTests(unittest.TestCase):
    """两套云监控可保存相同原文，权限、状态与加密材料各自独立。"""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.deployments = [self.make_deployment('A'), self.make_deployment('B')]
        self.raw_key = 'Shared_Two_Site_Key_' + ('S' * 32)
        self.created = []
        for deployment in self.deployments:
            self.created.append(deployment['store'].create({
                'name': '双机房调用', 'key': self.raw_key, 'scopes': ['ha:read']
            }))

    def tearDown(self):
        self.temp.cleanup()

    def make_deployment(self, site):
        root = Path(self.temp.name) / site
        root.mkdir()
        store = ApiKeyStore(str(root / 'monitor.db'), str(root / 'api_key_master.key'))
        store.migrate()
        with store.connect() as db:
            db.executescript('''CREATE TABLE ha_pair(id INTEGER PRIMARY KEY,pair_id TEXT,pair_name TEXT,status TEXT,status_text TEXT,local_type TEXT);
            CREATE TABLE ha_host_state(id INTEGER PRIMARY KEY,pair_id TEXT,host_id TEXT,host_name TEXT,role TEXT,online_status TEXT,health_status TEXT,collect_status TEXT,last_report_at TEXT,update_time TEXT,switch_task_id TEXT);
            CREATE TABLE ha_switch_task(switch_task_id TEXT,pair_id TEXT,status TEXT);''')
            db.execute("INSERT INTO ha_pair VALUES(1,'pair',?,'normal','ok','local')", ('机房-' + site,))
        config = str(root / 'api.json')
        self.write_config(config, True)
        app = Flask('deployment_' + site)
        app.secret_key = 'test-' + site
        register_api_key_routes(app, store, lambda: False, config)
        return {'store': store, 'config': config, 'client': app.test_client()}

    @staticmethod
    def write_config(path, is_open):
        with io.open(path, 'w', encoding='utf-8') as target:
            json.dump({'open': is_open, 'token': 'hash', 'token_crypt': 'crypt',
                       'limit_addr': ['127.0.0.1'], 'key': 'panel'}, target)

    def request(self, index):
        return self.deployments[index]['client'].get(
            '/ha/api/local/relationships', headers={'Authorization': 'Bearer ' + self.raw_key},
            environ_base={'REMOTE_ADDR': '127.0.0.1'})

    def update_first(self, **changes):
        data = {'name': '双机房调用', 'key_type': 'normal', 'scopes': ['ha:read'], 'is_enabled': True}
        data.update(changes)
        self.deployments[0]['store'].update(self.created[0]['key_id'], data)

    def test_same_plaintext_uses_independent_ids_nonces_ciphertext_and_relationships(self):
        self.assertNotEqual(self.created[0]['key_id'], self.created[1]['key_id'])
        rows = []
        for deployment, created in zip(self.deployments, self.created):
            self.assertEqual(deployment['store'].reveal(created['key_id'])['key'], self.raw_key)
            with deployment['store'].connect() as db:
                rows.append(db.execute('SELECT key_nonce,key_ciphertext FROM api_key WHERE key_id=?',
                                       (created['key_id'],)).fetchone())
        self.assertNotEqual(bytes(rows[0]['key_nonce']), bytes(rows[1]['key_nonce']))
        self.assertNotEqual(bytes(rows[0]['key_ciphertext']), bytes(rows[1]['key_ciphertext']))
        self.assertNotEqual(Path(self.deployments[0]['store'].master_path).read_bytes(),
                            Path(self.deployments[1]['store'].master_path).read_bytes())
        responses = [self.request(0), self.request(1)]
        self.assertEqual([response.status_code for response in responses], [200, 200])
        self.assertEqual([response.json['data']['list'][0]['pair_name'] for response in responses], ['机房-A', '机房-B'])

    def test_one_site_switch_permission_status_and_expiry_do_not_affect_other_site(self):
        scenarios = [
            ('api_closed', None),
            ('disabled', {'is_enabled': False}),
            ('expired', {'expires_at': '2000-01-01T00:00:00+00:00'}),
            ('scope_removed', {'scopes': []}),
        ]
        for name, update in scenarios:
            with self.subTest(name=name):
                self.write_config(self.deployments[0]['config'], True)
                self.update_first()
                if name == 'api_closed':
                    self.write_config(self.deployments[0]['config'], False)
                else:
                    self.update_first(**update)
                self.assertIn(self.request(0).status_code, (401, 403))
                self.assertEqual(self.request(1).status_code, 200)


if __name__ == '__main__':
    unittest.main()
