# coding: utf-8

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))
PLUGIN_DIR = os.path.join(ROOT_DIR, 'class', 'plugin')
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from es import ES

ES_CONFIG_PATH = 'data/es.json'


class IndexManager(object):
    def __init__(self, config_path=ES_CONFIG_PATH, es_client=None):
        self.config_path = config_path
        self.es = es_client or ES(config_path=self.config_path)

    def ensure_indices(self, index_definitions):
        results = []
        for index_name, index_body in index_definitions.items():
            exists = self.es.indexExists(index_name)
            if exists:
                self.es.putMapping(index_name, index_body.get('mappings', {}))
                results.append({'index': index_name, 'action': 'updated'})
            else:
                self.es.createIndex(index_name, index_body)
                results.append({'index': index_name, 'action': 'created'})
        return results

    def ensure_index_templates(self, template_definitions):
        results = []
        for template_name, template_body in template_definitions.items():
            exists = self.es.indexTemplateExists(template_name)
            self.es.putIndexTemplate(template_name, template_body)
            results.append({'template': template_name, 'action': 'updated' if exists else 'created'})
        return results


__all__ = [
    'IndexManager',
]
