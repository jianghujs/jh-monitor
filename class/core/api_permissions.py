# coding: utf-8

# ---------------------------------------------------------------------------------
# 外部接口权限清单
# ---------------------------------------------------------------------------------
# 调用密钥的权限必须来自本清单；新增外部接口时在这里登记接口与权限的对应关系。

SCOPES = {
    'ha:read': '读取云监控主备关系',
    'host:read': '读取云监控主机列表',
    'monitor_task:read': '读取云监控监控任务',
}

# 权限 -> 可访问的 (方法, 路径) 列表。
SCOPE_ROUTES = {
    'host:read': [
        ('GET', '/host/api/list'),
    ],
    'ha:read': [
        ('GET', '/ha/api/local/relationships'),
        ('GET', '/ha/api/local/inspection'),
    ],
    'monitor_task:read': [
        ('GET', '/monitor-task/api/list'),
    ],
}


def known_scopes():
    # 按名称返回全部已登记权限。
    return sorted(SCOPES)


def scope_labels():
    # 供设置页面展示权限名称。
    return {scope: SCOPES[scope] for scope in known_scopes()}


def can_access(key_type, scopes, method, path):
    # 管理员密钥可访问全部接口；普通密钥只能访问登记了对应权限的接口。
    if key_type == 'admin':
        return True
    required = route_scope(method, path)
    return bool(required) and required in (scopes or [])


def route_scope(method, path):
    # 反查某次请求需要的权限；未登记的接口返回 None。
    for scope, routes in SCOPE_ROUTES.items():
        for rule_method, rule_path in routes:
            if rule_path == path and rule_method.upper() == str(method).upper():
                return scope
    return None
