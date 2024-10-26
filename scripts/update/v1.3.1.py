# coding: utf-8
#-----------------------------
# 更新脚本
#-----------------------------

import sys
import os
import json
import datetime

if sys.platform != 'darwin':
    os.chdir('/www/server/jh-monitor')


chdir = os.getcwd()
sys.path.append(chdir + '/class/core')

# reload(sys)
# sys.setdefaultencoding('utf-8')


import jh
import db
import time
def updateDatabase():
    # 监控相关
    sql = db.Sql().dbfile('system')
    csql = jh.readFile('data/sql/system.sql')
        csql_list = csql.split(';')
        for index in range(len(csql_list)):
            sql.execute(csql_list[index], ())


if __name__ == "__main__":
    updateDatabase()
