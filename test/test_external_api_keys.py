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
        self.assertTrue(is_external_route('/ha/api/local/relationships'))
        for path in ['/ha/api/local/list', '/config/get_api_keys', '/api/config_api/get']:
            self.assertFalse(is_external_route(path))

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


if __name__ == '__main__':
    unittest.main()
