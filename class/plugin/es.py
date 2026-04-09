import json
import os
import traceback

from elasticsearch import Elasticsearch


DEFAULT_ES_CONFIG_PATH = os.path.join(os.getcwd(), 'data', 'es.json')
DEFAULT_ES_HOSTS = [{'host': '127.0.0.1', 'port': 9200, 'scheme': 'http'}]


class ES:
    def __init__(self, es_hosts=None, username=None, password=None, config_path=DEFAULT_ES_CONFIG_PATH):
        self._config_path = config_path
        self._es_hosts = list(DEFAULT_ES_HOSTS)
        self._username = ''
        self._password = ''
        self._conn = None
        self._err = None

        self._load_config()
        if es_hosts is not None:
            self._es_hosts = es_hosts
        if username is not None:
            self._username = username
        if password is not None:
            self._password = password

        self._connect()

    def _load_config(self):
        if not os.path.exists(self._config_path):
            return
        try:
            with open(self._config_path, 'r') as fp:
                config = json.load(fp)
            hosts = config.get('hosts', [])
            if isinstance(hosts, list) and len(hosts) > 0:
                self._es_hosts = hosts
            self._username = str(config.get('username', '') or '')
            self._password = str(config.get('password', '') or '')
        except Exception as ex:
            self._err = ex

    def _build_conn_kwargs(self):
        kwargs = {
            'hosts': self._es_hosts,
            'request_timeout': 10,
            'verify_certs': False,
        }
        if self._username != '':
            kwargs['basic_auth'] = (self._username, self._password)
        return kwargs

    def _connect(self):
        try:
            kwargs = self._build_conn_kwargs()
            try:
                self._conn = Elasticsearch(**kwargs)
            except TypeError:
                if 'basic_auth' in kwargs:
                    kwargs['http_auth'] = kwargs.pop('basic_auth')
                self._conn = Elasticsearch(**kwargs)
            return True
        except Exception as ex:
            traceback.print_exc()
            self._err = ex
            return False

    def getConn(self):
        if self._conn is None:
            self._connect()
        return self._conn

    def getClient(self):
        return self.getConn()

    def getError(self):
        return self._err

    def setEsHosts(self, es_hosts):
        if es_hosts is None:
            return
        self._es_hosts = es_hosts
        self._connect()

    def normalizeResponse(self, response):
        if hasattr(response, 'body'):
            return response.body
        if hasattr(response, 'to_dict'):
            return response.to_dict()
        return response or {}

    def search(self, index, body, scroll=None):
        try:
            kwargs = {'index': index, 'body': body}
            if scroll:
                kwargs['scroll'] = scroll
            return self.normalizeResponse(self.getConn().search(**kwargs))
        except Exception as ex:
            self._err = ex
            return None

    def get(self, index, doc_id):
        try:
            return self.normalizeResponse(self.getConn().get(index=index, id=doc_id))
        except Exception as ex:
            self._err = ex
            return None

    def index(self, index, doc_id, document=None, body=None, refresh=None):
        try:
            kwargs = {'index': index, 'id': doc_id}
            if document is not None:
                kwargs['document'] = document
            elif body is not None:
                kwargs['body'] = body
            else:
                kwargs['body'] = {}
            if refresh is not None:
                kwargs['refresh'] = refresh
            try:
                return self.getConn().index(**kwargs)
            except TypeError:
                if 'document' in kwargs:
                    kwargs['body'] = kwargs.pop('document')
                return self.getConn().index(**kwargs)
        except Exception as ex:
            self._err = ex
            return None

    def scroll(self, scroll_id, scroll='1m'):
        try:
            return self.normalizeResponse(self.getConn().scroll(scroll_id=scroll_id, scroll=scroll))
        except Exception as ex:
            self._err = ex
            return None

    def clearScroll(self, scroll_id):
        try:
            return self.getConn().clear_scroll(scroll_id=scroll_id)
        except Exception as ex:
            self._err = ex
            return None

    def indexExists(self, index):
        try:
            return bool(self.getConn().indices.exists(index=index))
        except Exception as ex:
            self._err = ex
            return False

    def createIndex(self, index, body):
        try:
            return self.getConn().indices.create(index=index, body=body)
        except Exception as ex:
            self._err = ex
            return None

    def putMapping(self, index, body):
        try:
            return self.getConn().indices.put_mapping(index=index, body=body)
        except Exception as ex:
            self._err = ex
            return None

    def indexTemplateExists(self, name):
        try:
            return bool(self.getConn().indices.exists_index_template(name=name))
        except Exception as ex:
            self._err = ex
            return False

    def putIndexTemplate(self, name, body):
        try:
            return self.getConn().indices.put_index_template(name=name, body=body)
        except Exception as ex:
            self._err = ex
            return None

    def searchAll(self, index, body, source_fields=None, page_size=500, scroll='1m'):
        results = []
        scroll_id = None
        try:
            query_body = dict(body or {})
            query_body['size'] = page_size
            if source_fields:
                query_body['_source'] = source_fields

            response = self.search(index=index, body=query_body, scroll=scroll)
            if not response:
                return []
            scroll_id = response.get('_scroll_id')

            while True:
                hits = response.get('hits', {}).get('hits', [])
                if len(hits) == 0:
                    break
                for hit in hits:
                    source = hit.get('_source', {})
                    if isinstance(source, dict):
                        results.append(source)
                if not scroll_id:
                    break
                response = self.scroll(scroll_id=scroll_id, scroll=scroll)
                if not response:
                    break
                scroll_id = response.get('_scroll_id', scroll_id)
        finally:
            if scroll_id:
                self.clearScroll(scroll_id)
        return results

    def test(self):
        try:
            es = self.getConn()
            query = {}
            indices_response = es.cat.indices()
            search_response = es.search(index='filebeat-*', body=query)

            print('========= Test ES Start =========')
            print('== indices_response:', indices_response)
            print('== search_response:', search_response)
            print('========= Test ES End =========')
        except Exception as ex:
            traceback.print_exc()
            self._err = ex
            return False
        return True


if __name__ == '__main__':
    es = ES()
    es.test()
