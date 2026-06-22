# coding: utf-8
"""
log_tool: 统一的 Jianghu 运维风格日志工具

参考 /root/.codex/skills/jianghujs-logger 的风格：
- 一行一条记录，前缀 `[module]`，字段 `key=value`
- 顶层任务用 `========` 长分隔线，重复块用 `--------` 短分隔线
- 主流程入口/出口用 `☑️ 开始...` / `☑️ ...完成`（成功/进行中，绿色）
- 失败/异常用 `❌ ...失败`（红色）
- 子步骤用 `|- 开始...` 、`|--- ...完成` / `|--- ...失败` / `|--- ...跳过`
- 字段值规范化：None/'' 显示为 `-`，列表用 `|` 拼接，含空白的值加引号
- ANSI 颜色仅在 TTY 下生效，写到文件/管道时自动去色，避免污染日志文件

环境变量：
- NO_COLOR=1     强制不上色
- FORCE_COLOR=1  强制上色（即便 stream 不是 TTY）

用法：
    from log_tool import LogTool
    logger = LogTool('es-init')
    logger.separator(long=True)
    logger.start('开始初始化ES索引', mode='ensure', month='2026-06')
    logger.step('开始扫描资源')
    logger.detail('扫描完成', count=10)
    logger.error('索引创建失败', index='foo', error=str(ex))
    logger.done('ES索引初始化完成', useTime='1.23s')
    logger.separator(long=True)
"""

import os
import re
import sys


# ANSI color codes
ANSI_RESET = '\033[0m'
ANSI_GREEN = '\033[32m'
ANSI_RED = '\033[31m'
ANSI_YELLOW = '\033[33m'
ANSI_CYAN = '\033[36m'
ANSI_GRAY = '\033[90m'
ANSI_BOLD = '\033[1m'

# 图标常量
ICON_OK = '☑️'
ICON_FAIL = '❌'

# ANSI 转义序列，用于把彩色行剥成纯文本喂给回调
_ANSI_PATTERN = re.compile(r'\x1b\[[0-9;]*m')


def format_log_value(value):
    """把任意 Python 值规范成日志字段值"""
    if value is None or value == '':
        return '-'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (list, tuple, set)):
        items = [str(item) for item in value if item is not None and item != '']
        return '|'.join(items) if items else '-'
    if isinstance(value, dict):
        if not value:
            return '-'
        parts = []
        for sub_key, sub_value in value.items():
            parts.append('{0}:{1}'.format(sub_key, format_log_value(sub_value)))
        return '{' + ','.join(parts) + '}'
    text = str(value).strip()
    if text == '':
        return '-'
    if any(ch.isspace() for ch in text):
        return '"' + text.replace('"', "'") + '"'
    return text


def format_fields(fields):
    """把 fields dict 拼成 ` key=value key2=value2`，前导空格已内置"""
    if not fields:
        return ''
    parts = []
    for key, value in fields.items():
        if value is None:
            continue
        parts.append('{0}={1}'.format(key, format_log_value(value)))
    if not parts:
        return ''
    return ' ' + ' '.join(parts)


def _detect_color_enabled(stream):
    """根据环境与 stream 是否 TTY 决定是否上色"""
    if os.environ.get('NO_COLOR'):
        return False
    if os.environ.get('FORCE_COLOR'):
        return True
    try:
        return bool(stream.isatty())
    except Exception:
        return False


class LogTool(object):
    """统一日志工具

    Args:
        prefix: 模块前缀，比如 'es-init'、'monitor-task'
        stream: 输出流，默认 stderr，便于 stdout 留给 JSON 等机读输出
        enabled: 是否启用，默认 True
        color: True/False/None，None 表示自动按 TTY 与 NO_COLOR/FORCE_COLOR 判断
    """

    SEP_LONG = '=' * 40
    SEP_SHORT = '-' * 40

    def __init__(self, prefix='log', stream=None, enabled=True, color=None, callback=None):
        """

        Args:
            prefix: 模块前缀，比如 'es-init'。
            stream: 输出流，默认 stderr。
            enabled: 是否启用。
            color: True/False/None；None 表示按 TTY + NO_COLOR/FORCE_COLOR 自动决定。
            callback: 可选回调，签名 ``callback(plain_text_line)``。
                每条日志写完 stream 后，会把同一行剥掉 ANSI 颜色，再喂给回调。
                适合用于把进度同步到面板 UI、消息队列、外部记录器等位置。
        """
        self.prefix = '[{0}]'.format(str(prefix or 'log').strip().strip('[]'))
        self.stream = stream if stream is not None else sys.stderr
        self.enabled = bool(enabled)
        self.callback = callback
        if color is None:
            self.color = _detect_color_enabled(self.stream)
        else:
            self.color = bool(color)

    def _paint(self, text, color_code):
        if not self.color or not color_code:
            return text
        return '{0}{1}{2}'.format(color_code, text, ANSI_RESET)

    def _dispatch_callback(self, body):
        """把已经渲染好的整行（未带换行符的 body）剥色后丢给 callback。"""
        if not self.callback:
            return
        try:
            plain = _ANSI_PATTERN.sub('', body)
            if plain == '':
                return
            self.callback(plain)
        except Exception:
            # 回调异常不影响日志主流程
            pass

    def _emit(self, message, fields=None, color_code=None):
        if not self.enabled:
            return
        body = '{0} {1}{2}'.format(self.prefix, message, format_fields(fields))
        line = self._paint(body, color_code) + '\n'
        try:
            self.stream.write(line)
            self.stream.flush()
        except Exception:
            # 日志输出不应影响主流程
            pass
        self._dispatch_callback(body)

    # 基础输出
    def info(self, message, **fields):
        self._emit(message, fields)

    def warn(self, message, **fields):
        self._emit(message, fields, ANSI_YELLOW)

    def error(self, message, **fields):
        """普通错误（不带 ❌ 前缀），整行红色"""
        self._emit(message, fields, ANSI_RED)

    def debug(self, message, **fields):
        self._emit(message, fields, ANSI_GRAY)

    # 结构化便捷方法（Jianghu 操作日志风格）
    def separator(self, long=False):
        if not self.enabled:
            return
        sep = self.SEP_LONG if long else self.SEP_SHORT
        body = '{0} {1}'.format(self.prefix, sep)
        try:
            self.stream.write(self._paint(body, ANSI_GRAY) + '\n')
            self.stream.flush()
        except Exception:
            pass
        self._dispatch_callback(body)

    def start(self, message, **fields):
        """顶层入口：☑️ 开始...（绿色）"""
        self._emit('{0} {1}'.format(ICON_OK, message), fields, ANSI_GREEN)

    def done(self, message, **fields):
        """顶层完成：☑️ ...完成（绿色）"""
        self._emit('{0} {1}'.format(ICON_OK, message), fields, ANSI_GREEN)

    def fail(self, message, **fields):
        """顶层失败：❌ ...失败（红色）"""
        self._emit('{0} {1}'.format(ICON_FAIL, message), fields, ANSI_RED)

    def step(self, message, **fields):
        """主要子步骤：|- 开始..."""
        if not message.startswith('|-'):
            message = '|- {0}'.format(message)
        self._emit(message, fields)

    def detail(self, message, **fields):
        """子步骤明细：|--- ...完成（默认无色，调用方可用 detail_ok/detail_fail 区分语义）"""
        if not message.startswith('|--'):
            message = '|--- {0}'.format(message)
        self._emit(message, fields)

    def detail_ok(self, message, **fields):
        """子步骤成功：|--- ☑️ ...完成（绿色）"""
        if not message.startswith('|--'):
            message = '|--- {0}'.format(message)
        self._emit(message.replace('|---', '|--- {0}'.format(ICON_OK), 1) if '|---' in message
                   else '{0} {1}'.format(ICON_OK, message),
                   fields, ANSI_GREEN)

    def detail_fail(self, message, **fields):
        """子步骤失败：|--- ❌ ...失败（红色）"""
        if not message.startswith('|--'):
            message = '|--- {0}'.format(message)
        self._emit(message.replace('|---', '|--- {0}'.format(ICON_FAIL), 1) if '|---' in message
                   else '{0} {1}'.format(ICON_FAIL, message),
                   fields, ANSI_RED)

    # 上下文管理：自动包裹一段任务，进入打 start，离开打 done/fail
    def task(self, message, **fields):
        return _TaskScope(self, message, fields)


class _TaskScope(object):
    def __init__(self, logger, message, fields):
        self.logger = logger
        self.message = message
        self.fields = fields or {}
        self._start_ts = None

    def __enter__(self):
        import time as _time
        self._start_ts = _time.time()
        self.logger.separator(long=True)
        self.logger.start(self.message, **self.fields)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time as _time
        use_time = '{0:.2f}s'.format(_time.time() - (self._start_ts or _time.time()))
        base = self.message.replace('开始', '').strip() or '任务'
        if exc_type is None:
            self.logger.done('{0}完成'.format(base), useTime=use_time)
        else:
            self.logger.fail('{0}失败'.format(base), error=str(exc_val), useTime=use_time)
        self.logger.separator(long=True)
        return False  # 不吞异常


# 模块级默认实例 & 便捷函数
_default_logger = LogTool('log')


def get_default_logger():
    return _default_logger


def info(message, **fields):
    _default_logger.info(message, **fields)


def warn(message, **fields):
    _default_logger.warn(message, **fields)


def error(message, **fields):
    _default_logger.error(message, **fields)


def debug(message, **fields):
    _default_logger.debug(message, **fields)


def separator(long=False):
    _default_logger.separator(long=long)


__all__ = [
    'LogTool',
    'ICON_OK',
    'ICON_FAIL',
    'format_log_value',
    'format_fields',
    'get_default_logger',
    'info',
    'warn',
    'error',
    'debug',
    'separator',
]
