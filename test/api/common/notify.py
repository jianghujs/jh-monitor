# coding: utf-8


class NotifyDryRun:
    def __init__(self, jh_module, extra_modules=None):
        self.jh_module = jh_module
        self.extra_modules = extra_modules or []
        self.messages = []
        self._originals = []

    def __enter__(self):
        self._replace_notify(self.jh_module)
        for module in self.extra_modules:
            self._replace_notify(module.jh if hasattr(module, 'jh') else module)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.restore()
        return False

    def _replace_notify(self, target):
        original_notify = target.notifyMessage
        self._originals.append((target, original_notify))
        target.notifyMessage = self._fake_notify

    def _fake_notify(self, msg, msgtype='text', title='江湖云监控通知', stype='common', trigger_time=300, is_write_log=True):
        self.messages.append({
            'title': title,
            'stype': stype,
            'msgtype': msgtype,
            'trigger_time': trigger_time,
            'is_write_log': is_write_log,
            'content_length': len(str(msg or '')),
        })
        return True

    def restore(self):
        while self._originals:
            target, original_notify = self._originals.pop()
            target.notifyMessage = original_notify

