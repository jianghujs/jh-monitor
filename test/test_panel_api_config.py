"""Exercise legacy panel-token handlers without starting panel services."""
import ast
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from flask import Flask, request

SOURCE = Path(__file__).resolve().parents[1] / 'class/core/config_api.py'
tree = ast.parse(SOURCE.read_text())
original = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'config_api')
methods = {'_readPanelApiConfig', '_writeJsonConfig', 'checkPanelToken', 'getPanelTokenApi', 'setPanelTokenApi'}
original.body = [node for node in original.body if isinstance(node, ast.FunctionDef) and node.name in methods]
module = ast.Module(body=[original], type_ignores=[])
jh = SimpleNamespace(getRandomString=lambda n: 'x' * n,
                     md5=lambda s: hashlib.md5(s.encode()).hexdigest(),
                     enCrypt=lambda digest, token: b'test-ciphertext',
                     deCrypt=lambda digest, token: 'test-plaintext',
                     writeLog=Mock(),
                     returnJson=lambda status, msg, data=None: {'status': status, 'msg': msg, 'data': data})
namespace = {'os': os, 'json': json, 'tempfile': tempfile, 'jh': jh, 'request': request}
exec(compile(ast.fix_missing_locations(module), str(SOURCE), 'exec'), namespace)


class PanelApiConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'data/api.json'
        self.service = namespace['config_api']()
        self.service._config_api__api_addr = str(self.path)
        self.app = Flask(__name__)

    def tearDown(self):
        self.temp.cleanup()

    def toggle(self):
        with self.app.test_request_context('/config/set_panel_token', method='POST', data={'op_type': '2'}):
            return self.service.setPanelTokenApi()

    def write(self, value):
        self.path.parent.mkdir(exist_ok=True)
        self.path.write_text(json.dumps(value))

    def test_first_enable_without_opening_settings_initializes_config(self):
        self.assertTrue(self.toggle()['status'])
        data = json.loads(self.path.read_text())
        self.assertTrue(data['open'])
        self.assertEqual(data['limit_addr'], [])
        self.assertIn('token_crypt', data)
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.toggle()['status'])
        self.assertFalse(json.loads(self.path.read_text())['open'])

    def test_boolean_switch_and_existing_credentials_are_preserved(self):
        data = {'open': False, 'token': 'original', 'token_crypt': 'cipher', 'key': 'key', 'limit_addr': ['10.0.0.1']}
        self.write(data)
        self.toggle()
        self.assertEqual(json.loads(self.path.read_text()), dict(data, open=True))

    def test_invalid_config_is_not_overwritten(self):
        for data in [False, [], {'open': 'false'}, {'open': False, 'limit_addr': False}]:
            self.write(data)
            before = self.path.read_bytes()
            with self.assertRaises(ValueError):
                self.toggle()
            self.assertEqual(self.path.read_bytes(), before)
        self.path.write_text('{broken')
        with self.assertRaisesRegex(ValueError, '格式无效'):
            self.toggle()
        self.assertEqual(self.path.read_text(), '{broken')

    def test_unreadable_config_reports_path_and_does_not_write(self):
        with patch('builtins.open', side_effect=PermissionError()), patch.object(self.service, '_writeJsonConfig') as write:
            with self.assertRaisesRegex(ValueError, '路径和权限'):
                self.toggle()
            write.assert_not_called()

    def test_write_failure_cannot_report_success(self):
        with patch.object(self.service, '_writeJsonConfig', side_effect=PermissionError()):
            with self.assertRaises(PermissionError):
                self.toggle()

    def test_read_missing_config_is_disabled_and_settings_can_initialize(self):
        self.assertEqual(self.service.checkPanelToken(), (False, ''))
        self.assertFalse(self.path.exists())
        result = self.service.getPanelTokenApi()
        self.assertTrue(result['status'])
        self.assertFalse(result['data']['open'])
        self.assertTrue(self.path.exists())


if __name__ == '__main__':
    unittest.main()
