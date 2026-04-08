import time



def parseTime(value, default=0, formats=None):
    try:
        value = str(value or '').strip()
        if value == '':
            return default

        if formats is None:
            formats = ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y/%m/%d %H:%M:%S')

        for fmt in formats:
            try:
                return int(time.mktime(time.strptime(value, fmt)))
            except Exception:
                pass

        return int(float(value))
    except Exception:
        return default


def safeInt(value, default=0):
    try:
        if value is None or value == '':
            return default
        return int(float(value))
    except Exception:
        return default


def safeFloat(value, default=0.0):
    try:
        if value is None or value == '':
            return default
        return float(value)
    except Exception:
        return default


def escapeHtml(value):
    text = str(value or '')
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def getNested(data, path, default=None):
    current = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    if current is None:
        return default
    return current
