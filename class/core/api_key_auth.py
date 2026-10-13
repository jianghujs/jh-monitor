# coding: utf-8

# ---------------------------------------------------------------------------------
# 外部接口凭据解析
# ---------------------------------------------------------------------------------
# 面板总密钥（签名+IP白名单）与带权限的调用密钥共用这一处解析，避免出现两套鉴权。
# 本模块只做纯逻辑，不依赖面板内部模块，便于单测。

import hashlib
import io
import json

from api_permissions import can_access


class AuthError(Exception):
    # 凭据异常，status 直接对应返回的 HTTP 状态码。
    def __init__(self, message, status=401):
        super(AuthError, self).__init__(message)
        self.status = status


def md5(text):
    # 与面板 jh.md5 完全一致。
    return hashlib.md5(str(text).encode('utf-8')).hexdigest()


def read_api_config(api_config_path):
    # 只读取面板 API 配置，不外泄任何字段。
    try:
        with io.open(api_config_path, 'r', encoding='utf-8') as fp:
            data = json.loads(fp.read())
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def panel_api_open(api_config_path):
    # 设置页“API接口”总开关。
    return bool(read_api_config(api_config_path).get('open'))


def master_signature_valid(api_config_path, request_time, request_token, remote_addr):
    # 面板总密钥规则：md5(request_time + md5(token_crypt)) 且来源 IP 在白名单内。
    data = read_api_config(api_config_path)
    if not data.get('open'):
        raise AuthError('未开启API', 403)
    token_crypt = data.get('token_crypt')
    if not token_crypt or not request_time or not request_token:
        raise AuthError('密钥错误')
    if md5(str(request_time) + md5(token_crypt)) != request_token:
        raise AuthError('密钥错误')
    if remote_addr not in (data.get('limit_addr') or []):
        raise AuthError('非法请求', 403)
    return {'mode': 'master'}


def resolve_credentials(headers, form, remote_addr, store, api_config_path):
    # 调用密钥优先；否则按面板总密钥校验，两者都失败时返回 401。
    authorization = (headers or {}).get('Authorization')
    if authorization:
        if not panel_api_open(api_config_path):
            raise AuthError('面板API未开启', 403)
        record = store.authenticate(authorization)
        return {'mode': 'key', 'key_id': record['key_id'], 'key_type': record['key_type'],
                'scopes': json.loads(record['scopes'])}

    request_time = (form or {}).get('request_time', '')
    request_token = (form or {}).get('request_token', '')
    if request_time or request_token:
        return master_signature_valid(api_config_path, request_time, request_token, remote_addr)
    raise AuthError('缺少调用凭据')


def authorize_request(headers, form, remote_addr, store, api_config_path, method, path):
    # 解析凭据后再校验接口权限：管理员密钥放行全部，普通密钥按登记权限判断。
    credential = resolve_credentials(headers, form, remote_addr, store, api_config_path)
    if credential['mode'] == 'key' and not can_access(credential['key_type'], credential['scopes'], method, path):
        raise AuthError('该密钥没有访问此接口的权限', 403)
    return credential
