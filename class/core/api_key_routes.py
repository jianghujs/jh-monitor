# coding: utf-8

# ---------------------------------------------------------------------------------
# 面板 API 接口的调用密钥
# ---------------------------------------------------------------------------------
# “设置 -> API接口配置”里的调用密钥管理与只读关系接口共用同一处凭据解析，
# 不再单独提供另一套 API 管理入口。

import hmac
import json
import secrets
from urllib.parse import urlsplit

from flask import jsonify, request, session

from api_key_auth import AuthError, authorize_request
from api_key_store import ApiKeyError
from api_permissions import scope_labels
from ha_read_snapshot import relationships_snapshot
from host_read_snapshot import hosts_snapshot
from monitor_task_read_snapshot import monitor_tasks_snapshot


def is_external_route(path):
    # 外部接口使用自己的凭据，不叠加面板 BasicAuth 与登录态。
    return path in ('/ha/api/local/relationships', '/host/api/list',
                    '/ha/api/local/inspection', '/monitor-task/api/list')


def register_api_key_routes(app, store, is_logged_in, api_config_path):
    def response(data=None, message=None, status=200):
        result = jsonify(status=status < 400, data=data, msg=message)
        result.status_code = status
        result.headers['Cache-Control'] = 'no-store'
        return result

    def admin_ready():
        # 只有完整管理员登录态可以管理调用密钥。
        if not is_logged_in() or session.get('tmp_login') or session.get('tmp_login_id') or session.get('tmp_login_expire'):
            return response(message='完整管理员登录后才可管理调用密钥', status=403)
        if request.headers.get('Authorization'):
            return response(message='调用密钥不能用于管理调用密钥', status=403)
        return None

    def csrf_ready():
        expected = session.get('api_key_csrf', '')
        parsed = urlsplit(request.headers.get('Origin') or request.headers.get('Referer') or '')
        if parsed.scheme != request.scheme or parsed.netloc != request.host:
            return response(message='请求来源校验失败，请从面板页面操作', status=403)
        if not expected or not hmac.compare_digest(expected, request.form.get('csrf_token', '')):
            return response(message='页面验证已失效，请刷新后重试', status=403)
        return None

    def form_boolean(value):
        return str(value).lower() in ('1', 'true', 'yes', 'on')

    def scopes_from_form(value):
        if value is None or value == '':
            return []
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except ValueError:
            pass
        return [item.strip() for item in str(value).split(',') if item.strip()]

    @app.route('/config/get_api_keys', methods=['GET', 'POST'])
    def get_api_keys():
        blocked = admin_ready()
        if blocked:
            return blocked
        if not session.get('api_key_csrf'):
            session['api_key_csrf'] = secrets.token_urlsafe(32)
        return response({
            'list': store.list(),
            'scopes': scope_labels(),
            'csrf_token': session['api_key_csrf'],
            'panel_api_open': bool(_panel_api_open(api_config_path)),
        })

    @app.route('/config/set_api_key', methods=['POST'])
    def set_api_key():
        blocked = admin_ready() or csrf_ready()
        if blocked:
            return blocked
        action = request.form.get('action', '')
        try:
            if action in ('create', 'update'):
                payload = {
                    'name': request.form.get('name'),
                    'key_type': request.form.get('key_type') or 'normal',
                    'remark': request.form.get('remark'),
                    'scopes': scopes_from_form(request.form.get('scopes')),
                    'is_enabled': form_boolean(request.form.get('is_enabled', '1')),
                    'expires_at': request.form.get('expires_at') or None,
                }
                if action == 'create':
                    payload['key'] = request.form.get('key', '')
                    data = store.create(payload)
                else:
                    if request.form.get('key', '') != '':
                        raise ApiKeyError('编辑调用密钥时不能修改密钥串')
                    data = store.update(request.form.get('key_id'), payload)
            elif action == 'delete':
                data = store.delete(request.form.get('key_id'))
            elif action == 'reveal':
                data = store.reveal(request.form.get('key_id'))
            else:
                raise ApiKeyError('未知操作', 400)
            app.logger.info('api_key action=%s key_id=%s user=%s', action, data.get('key_id'), session.get('username'))
            return response(data)
        except ApiKeyError as error:
            return response(message=str(error), status=error.status)
        except Exception:
            return response(message='调用密钥存储暂不可用', status=503)

    @app.route('/host/api/list', methods=['GET'])
    def read_hosts():
        try:
            authorize_request(request.headers, request.values, request.remote_addr, store, api_config_path,
                              request.method, request.path)
            return response(hosts_snapshot(store.db_path))
        except (AuthError, ApiKeyError) as error:
            return response(message=str(error), status=error.status)
        except Exception:
            return response(message='主机列表暂不可用', status=503)

    @app.route('/monitor-task/api/list', methods=['GET'])
    def read_monitor_tasks():
        try:
            authorize_request(request.headers, request.values, request.remote_addr, store, api_config_path,
                              request.method, request.path)
            return response(monitor_tasks_snapshot(store.db_path))
        except (AuthError, ApiKeyError) as error:
            return response(message=str(error), status=error.status)
        except Exception:
            return response(message='监控任务快照暂不可用', status=503)

    @app.route('/ha/api/local/inspection', methods=['GET'])
    def read_ha_inspection():
        try:
            authorize_request(request.headers, request.values, request.remote_addr, store, api_config_path,
                              request.method, request.path)
            return response(relationships_snapshot(store.db_path, include_checks=True))
        except (AuthError, ApiKeyError) as error:
            return response(message=str(error), status=error.status)
        except Exception:
            return response(message='主备巡检快照暂不可用', status=503)

    @app.route('/ha/api/local/relationships', methods=['GET'])
    def read_relationships():
        try:
            authorize_request(request.headers, request.values, request.remote_addr, store, api_config_path,
                              request.method, request.path)
            return response(relationships_snapshot(store.db_path))
        except (AuthError, ApiKeyError) as error:
            return response(message=str(error), status=error.status)
        except Exception:
            return response(message='主备关系快照暂不可用', status=503)


def _panel_api_open(api_config_path):
    from api_key_auth import panel_api_open

    return panel_api_open(api_config_path)
