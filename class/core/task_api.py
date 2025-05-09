# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 任务页操作
# ---------------------------------------------------------------------------------


import psutil
import time
import os
import sys
import jh
import re
import json
import pwd
from urllib.parse import unquote


from flask import request


class task_api:

    def __init__(self):
        pass

    def countApi(self):
        c = jh.M('tasks').where("status!=?", ('1',)).count()
        return str(c)

    def listApi(self):

        p = request.form.get('p', '1')
        limit = request.form.get('limit', '10').strip()
        search = request.form.get('search', '').strip()

        start = (int(p) - 1) * int(limit)
        limit_str = str(start) + ',' + str(limit)

        _list = jh.M('tasks').where('', ()).field(
            'id,name,type,status,addtime,start,end').limit(limit_str).order('id desc').select()
        _ret = {}
        _ret['data'] = _list

        count = jh.M('tasks').where('', ()).count()
        _page = {}
        _page['count'] = count
        _page['tojs'] = 'remind'
        _page['p'] = p

        # return data
        _ret['count'] = count
        _ret['page'] = jh.getPage(_page)
        return jh.getJson(_ret)

    def getExecLogApi(self):
        file = os.getcwd() + "/tmp/panelExec.log"
        v = jh.getLastLine(file, 100)
        return v

    def getTaskSpeedApi(self):
        tempFile = jh.getRunDir() + '/tmp/panelExec.log'
        freshFile = jh.getRunDir() + '/tmp/panelFresh'

        find = jh.M('tasks').where('status=? OR status=?',
                                   ('-1', '0')).field('id,type,name,execstr').find()
        if not len(find):
            return jh.returnJson(False, '当前没有任务队列在执行-2!')

        jh.triggerTask()

        data = {}
        data['name'] = find['name']
        data['execstr'] = find['execstr']
        if find['type'] == 'download':
            readLine = ""
            for i in range(3):
                try:
                    readLine = jh.readFile(tempFile)
                    if len(readLine) > 10:
                        data['msg'] = json.loads(readLine)
                        data['isDownload'] = True
                        break
                except Exception as e:
                    if i == 2:
                        jh.M('tasks').where("id=?", (find['id'],)).save(
                            'status', ('0',))
                        return jh.returnJson(False, '当前没有任务队列在执行-4:' + str(e))
                time.sleep(0.5)
        else:
            data['msg'] = jh.getLastLine(tempFile, 10)
            data['isDownload'] = False

        data['task'] = jh.M('tasks').where("status!=?", ('1',)).field(
            'id,status,name,type').order("id asc").select()
        return jh.getJson(data)

    def generateScriptFileAndAddTaskApi(self):
        name = request.form.get('name', '').strip()
        content = unquote(str(request.form.get('content', '')), 'utf-8').replace("\\n", "\n")

        # 写入临时文件用于执行
        tempFilePath = jh.getRunDir() + '/tmp/' +  str(time.time()) + '.sh'
        jh.writeFile(tempFilePath, '%(content)s\nrm -f %(tempFilePath)s' % {'content': content, 'tempFilePath': tempFilePath})
        jh.execShell('chmod 750 ' + tempFilePath)
        
        jh.addAndTriggerTask(
            name,
            execstr = 'sh %(tempFilePath)s' % {'tempFilePath': tempFilePath }
        )
        return jh.returnJson(False, 'ok', {
            'name': name,
            'content': content,
            'tempFilePath': tempFilePath
        })

    def speedLogsFileApi(self):
        p = request.form.get('path', '').strip()
        # 生成临时文件
        if p == '':
            p = '/tmp/' +  str(time.time()) + '.sh'
        log_file = jh.getRunDir() + p
        if not os.path.exists(log_file):
            jh.execShell('touch ' + log_file)
        return jh.returnJson(True, 'OK', log_file)

    def generateScriptFileAndExcuteApi(self): 
        log_path = request.form.get('logPath', '').strip()
        script_content = unquote(str(request.form.get('scriptContent', '')), 'utf-8').replace("\\n", "\n")
        
        cmd = """
        %(script_content)s
        """ % {'script_content': script_content, 'log_path': log_path}

        # 写入临时文件用于执行
        tempFilePath = jh.getRunDir() + '/tmp/' +  str(time.time()) + '.sh'
        tempFileContent = """
        set -e\n
        %(cmd)s
        if [ $? -eq 0 ]; then
            true
        else
            false
        fi  
        """ % {'cmd': cmd, 'tempFilePath': tempFilePath}
        jh.writeFile(tempFilePath, tempFileContent)
        jh.execShell('chmod 750 ' + tempFilePath)
        # 使用os.system执行命令，不会返回结果
        data = jh.execShell('source /root/.bashrc && ' + tempFilePath + ' > ' + log_path + ' 2>&1')
        # 删除临时文件
        os.remove( tempFilePath)
        if data[2] != 0:
            return jh.returnJson(False, '执行失败' )
        return jh.returnJson(True, 'ok')

        
