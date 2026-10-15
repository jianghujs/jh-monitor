"""Recoverable API credentials. No dependency on panel request globals."""
import datetime
import fcntl
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from api_permissions import SCOPES
PUBLIC_FIELDS = ('key_id', 'name', 'key_type', 'key_prefix', 'scopes', 'is_enabled', 'expires_at',
                 'remark', 'created_at', 'updated_at', 'last_used_at')
KEY_TYPES = ('admin', 'normal')
API_KEY_PATTERN = re.compile(r'[A-Za-z0-9_-]{32,128}')
API_KEY_RULE_MESSAGE = '密钥串必须为 32～128 位字母、数字、下划线或短横线'


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def parse_time(value):
    parsed = datetime.datetime.fromisoformat(value.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Expiry must include timezone')
    return parsed


class ApiKeyError(ValueError):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


class ApiKeyStore:
    def __init__(self, db_path, master_path):
        self.db_path = db_path
        self.master_path = master_path

    def connect(self):
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def migrate(self):
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS api_key (
                key_id TEXT PRIMARY KEY, name TEXT NOT NULL, key_prefix TEXT NOT NULL,
                key_hash TEXT NOT NULL, key_ciphertext BLOB NOT NULL, key_nonce BLOB NOT NULL,
                encryption_version INTEGER NOT NULL DEFAULT 1, scopes TEXT NOT NULL,
                is_enabled INTEGER NOT NULL DEFAULT 1, expires_at TEXT, remark TEXT,
                key_type TEXT NOT NULL DEFAULT 'normal',
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_used_at TEXT)''')
            columns = [row[1] for row in db.execute('PRAGMA table_info(api_key)').fetchall()]
            if 'key_type' not in columns:
                db.execute("ALTER TABLE api_key ADD COLUMN key_type TEXT NOT NULL DEFAULT 'normal'")
            db.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_api_key_hash ON api_key(key_hash)')

    def master_key(self):
        # Lock creation and checking together: other workers never read a partial key.
        fd = os.open(self.master_path + '.lock', os.O_CREAT | os.O_RDWR, 0o600)
        with os.fdopen(fd, 'rb') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not os.path.exists(self.master_path):
                with self.connect() as db:
                    if db.execute('SELECT 1 FROM api_key LIMIT 1').fetchone():
                        raise ApiKeyError('缺少调用密钥主密钥，请恢复原备份', 503)
                key = secrets.token_bytes(32)
                fd = os.open(self.master_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, 'wb') as target:
                    target.write(key)
                    target.flush()
                    os.fsync(target.fileno())
            if os.stat(self.master_path).st_mode & 0o077:
                raise ApiKeyError('调用密钥主密钥权限必须为 0600', 503)
            with open(self.master_path, 'rb') as source:
                key = source.read()
            if len(key) != 32:
                raise ApiKeyError('调用密钥主密钥无效，请恢复备份', 503)
            return key

    @staticmethod
    def metadata(data):
        name = str(data.get('name') or '').strip()
        key_type = str(data.get('key_type') or 'normal').strip()
        if key_type not in KEY_TYPES:
            raise ApiKeyError('密钥类型无效')
        scopes = [] if key_type == 'admin' else data.get('scopes', ['ha:read'])
        enabled = data.get('is_enabled', True)
        expiry = data.get('expires_at') or None
        if not name or len(name) > 128:
            raise ApiKeyError('Name is required (maximum 128 characters)')
        if not isinstance(scopes, list) or any(not isinstance(s, str) or s not in SCOPES for s in scopes):
            raise ApiKeyError('Unknown API permission')
        if type(enabled) not in (bool, int) or enabled not in (True, False, 0, 1):
            raise ApiKeyError('启用状态无效')
        if expiry:
            try:
                expiry = parse_time(expiry).isoformat()
            except (ValueError, TypeError, AttributeError):
                raise ApiKeyError('有效期格式无效')
        return (name, json.dumps(sorted(set(scopes))), int(enabled), expiry,
                str(data.get('remark') or '')[:1000], key_type)

    @staticmethod
    def key_is_valid(raw_key):
        return isinstance(raw_key, str) and API_KEY_PATTERN.fullmatch(raw_key) is not None

    @classmethod
    def key_for_create(cls, data):
        if 'key' not in data or data.get('key') == '':
            return 'jhm_' + secrets.token_hex(32)
        raw_key = data.get('key')
        if not cls.key_is_valid(raw_key):
            raise ApiKeyError(API_KEY_RULE_MESSAGE)
        return raw_key

    def list(self):
        with self.connect() as db:
            rows = db.execute('SELECT ' + ','.join(PUBLIC_FIELDS) + ' FROM api_key ORDER BY created_at DESC').fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item['scopes'] = json.loads(item['scopes'])
            item['key_prefix'] += '…'
            result.append(item)
        return result

    def create(self, data):
        metadata = self.metadata(data)
        key_id = uuid.uuid4().hex
        raw_key = self.key_for_create(data)
        key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
        nonce = secrets.token_bytes(12)
        master = self.master_key()
        with self.connect() as db:
            existing = db.execute('SELECT key_id FROM api_key LIMIT 1').fetchone()
        if existing:
            self.reveal(existing['key_id'])  # Do not create new ciphertext under a replaced/wrong key.
        ciphertext = AESGCM(master).encrypt(nonce, raw_key.encode(), (key_id + ':1').encode())
        try:
            with self.connect() as db:
                db.execute('''INSERT INTO api_key
                    (key_id,key_prefix,key_hash,key_ciphertext,key_nonce,encryption_version,
                     name,scopes,is_enabled,expires_at,remark,key_type,created_at,updated_at)
                    VALUES (?,?,?,?,?,1,?,?,?,?,?,?,?,?)''',
                    (key_id, raw_key[:12], key_hash, ciphertext, nonce) + metadata + (now_iso(), now_iso()))
        except sqlite3.IntegrityError:
            with self.connect() as db:
                duplicate = db.execute('SELECT key_id FROM api_key WHERE key_hash=?', (key_hash,)).fetchone()
            if duplicate:
                raise ApiKeyError('该密钥已存在，请使用已有记录或填写其他密钥', 409)
            raise
        return {'key_id': key_id, 'key': raw_key}

    def update(self, key_id, data):
        if 'key' in data and data.get('key') not in ('', None):
            raise ApiKeyError('编辑调用密钥时不能修改密钥串')
        with self.connect() as db:
            changed = db.execute('''UPDATE api_key SET name=?,scopes=?,is_enabled=?,expires_at=?,remark=?,key_type=?,updated_at=?
                WHERE key_id=?''', self.metadata(data) + (now_iso(), key_id)).rowcount
            if not changed:
                raise ApiKeyError('调用密钥不存在', 404)
        return {'key_id': key_id}

    def delete(self, key_id):
        with self.connect() as db:
            db.execute('DELETE FROM api_key WHERE key_id=?', (key_id,))
        return {'key_id': key_id}

    def reveal(self, key_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM api_key WHERE key_id=?', (key_id,)).fetchone()
        if not row:
            raise ApiKeyError('调用密钥不存在', 404)
        try:
            raw = AESGCM(self.master_key()).decrypt(row['key_nonce'], row['key_ciphertext'],
                  (key_id + ':' + str(row['encryption_version'])).encode()).decode()
        except ApiKeyError:
            raise
        except Exception:
            raise ApiKeyError('调用密钥无法解密，请检查主密钥与备份', 503)
        return {'key_id': key_id, 'key': raw}

    def authenticate(self, authorization, scope=None):
        # 校验启用/有效期后返回密钥记录；scope 为空表示只验凭据，由调用方再查权限。
        if scope is not None and scope not in SCOPES:
            raise ApiKeyError('未登记的权限', 403)
        parts = (authorization or '').split()
        if len(parts) != 2 or parts[0].lower() != 'bearer' or not self.key_is_valid(parts[1]):
            raise ApiKeyError('调用密钥无效或已停用', 401)
        digest = hashlib.sha256(parts[1].encode()).hexdigest()
        with self.connect() as db:
            row = db.execute('SELECT * FROM api_key WHERE key_hash=?', (digest,)).fetchone()
            if not row or not hmac.compare_digest(row['key_hash'], digest) or not row['is_enabled']:
                raise ApiKeyError('调用密钥无效或已停用', 401)
            if row['expires_at'] and parse_time(row['expires_at']) <= datetime.datetime.now(datetime.timezone.utc):
                raise ApiKeyError('调用密钥已过期', 401)
            if scope is not None and scope not in json.loads(row['scopes']):
                raise ApiKeyError('调用密钥缺少该接口的权限', 403)
            if not row['last_used_at'] or (datetime.datetime.now(datetime.timezone.utc) - parse_time(row['last_used_at'])).total_seconds() >= 60:
                db.execute('UPDATE api_key SET last_used_at=? WHERE key_id=?', (now_iso(), row['key_id']))
        return row
