# coding:utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 入口文件
# ---------------------------------------------------------------------------------


# pip install profiler_online
# 性能测试
# from profiler_online import run_profiler
# run_profiler()
import sys
import io
import os
from route import app, socketio


from gevent.pywsgi import WSGIServer
from geventwebsocket.handler import WebSocketHandler

from gevent import monkey
monkey.patch_all()

try:
    if __name__ == "__main__":

        PORT = 7200
        if os.path.exists('data/port.pl'):
            f = open('data/port.pl')
            PORT = int(f.read())
            f.close()

        HOST = '0.0.0.0'
        http_server = WSGIServer(
            (HOST, PORT), app, handler_class=WebSocketHandler)

        http_server.serve_forever()

        socketio.run(app, host=HOST, port=PORT)
except Exception as ex:
    print(ex)
