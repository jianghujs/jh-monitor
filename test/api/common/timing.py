# coding: utf-8

import functools
import time


class StepLogger:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.start_ts = time.time()
        self.last_ts = self.start_ts

    def log(self, message, **kwargs):
        if not self.enabled:
            return
        now = time.time()
        parts = [
            '[api-test]',
            message,
            'elapsed={0:.3f}s'.format(now - self.start_ts),
            'delta={0:.3f}s'.format(now - self.last_ts),
        ]
        for key, value in kwargs.items():
            parts.append('{0}={1}'.format(key, value))
        print(' '.join(parts), flush=True)
        self.last_ts = now


class MethodTimer:
    def __init__(self, logger, patches):
        self.logger = logger
        self.patches = patches
        self.originals = []

    def __enter__(self):
        for target, method_name, label in self.patches:
            if not hasattr(target, method_name):
                self.logger.log('skip missing method', method=method_name)
                continue
            original = getattr(target, method_name)
            self.originals.append((target, method_name, original))
            setattr(target, method_name, self._wrap(original, label or method_name))
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.restore()
        return False

    def _wrap(self, original, label):
        @functools.wraps(original)
        def wrapper(*args, **kwargs):
            self.logger.log('start {0}'.format(label))
            start_ts = time.time()
            try:
                return original(*args, **kwargs)
            finally:
                self.logger.log('done {0}'.format(label), cost='{0:.3f}s'.format(time.time() - start_ts))
        return wrapper

    def restore(self):
        while self.originals:
            target, method_name, original = self.originals.pop()
            setattr(target, method_name, original)
