# coding: utf-8

import os
import sys


def get_root_dir(current_file):
    current_dir = os.path.dirname(os.path.abspath(current_file))
    while current_dir and current_dir != os.path.dirname(current_dir):
        marker = os.path.join(current_dir, 'class', 'core', 'jh.py')
        if os.path.exists(marker):
            return current_dir
        current_dir = os.path.dirname(current_dir)
    raise RuntimeError('无法定位 jh-monitor 项目根目录')


def setup_test_env(current_file):
    root_dir = get_root_dir(current_file)
    path_list = [
        root_dir,
        os.path.join(root_dir, 'class', 'core'),
        os.path.join(root_dir, 'class', 'plugin'),
        os.path.join(root_dir, 'class', 'es', 'model'),
        os.path.join(root_dir, 'scripts', 'client'),
        os.path.join(root_dir, 'scripts'),
    ]
    for path in path_list:
        if path not in sys.path:
            sys.path.insert(0, path)
    os.chdir(root_dir)
    return root_dir
