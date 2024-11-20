from elasticsearch import Elasticsearch
import traceback

class ES:
    __ES_HOSTS = [{'host': 'localhost', 'port': 9200, 'scheme': 'http'}]
    __ES_AUTH = ('elastic', 'changeme')
    __ES_CONN = None
    __ES_ERR = None

    def __init__(self, es_hosts=None):
        if es_hosts is not None:
            self.__ES_HOSTS = es_hosts
        self.__Conn()
        # self.__Test()

    def __Conn(self):
        try:
            self.__ES_CONN = Elasticsearch(self.__ES_HOSTS, http_auth=self.__ES_AUTH)
            return True
        except Exception as e:
            traceback.print_exc()
            self.__ES_ERR = e
            return False

    def getConn(self):
        if self.__ES_CONN is None:
            self.__Conn()
        return self.__ES_CONN

    def setEsHosts(self, es_hosts):
        if es_hosts is None:
            return
        self.__ES_HOSTS = es_hosts
        self.__Conn()

    def search(self, index, body):
        try:
            results = self.__ES_CONN.search(index=index, body=body)
            return results
        except Exception as e:
            self.__ES_ERR = e
            return None
  
    def test(self):
        try:
            # 从ES获取数据
            es = self.__ES_CONN
            query = {}
            # 执行搜索请求
            indices_response = self.__ES_CONN.cat.indices()
            search_response = self.__ES_CONN.search(index="filebeat-8.15.3", body=query)
            print("========= Test ES Start =========")
            print("== indices_response:", indices_response)
            print("== search_response:", search_response)
            print("========= Test ES End =========")
        except Exception as e:
            traceback.print_exc()
            self.__ES_ERR = e
            return False
        return True


if __name__ == '__main__':
    es = ES()
    print('es', es)
    es.test()