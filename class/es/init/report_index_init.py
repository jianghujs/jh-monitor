#!/usr/bin/env python3
import json
import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ES_DIR = os.path.dirname(CURRENT_DIR)
ROOT_DIR = os.path.dirname(os.path.dirname(ES_DIR))
ES_MODEL_DIR = os.path.join(ES_DIR, 'model')
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)
if ES_DIR not in sys.path:
    sys.path.insert(0, ES_DIR)
if ES_MODEL_DIR not in sys.path:
    sys.path.insert(0, ES_MODEL_DIR)

from index_manager import IndexManager
from report_schema import REPORT_INDEXES, REPORT_INDEX_TEMPLATES


def main():
    manager = IndexManager()
    results = {
        'indices': manager.ensure_indices(REPORT_INDEXES),
        'templates': manager.ensure_index_templates(REPORT_INDEX_TEMPLATES),
    }
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
