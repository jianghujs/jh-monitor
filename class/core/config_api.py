# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 配置操作
# ---------------------------------------------------------------------------------

import psutil
import time
import os
import sys
import jh
import re
import json
import pwd

from flask import session
from flask import request


class config_api:

    __version = '1.0.6'
    __api_addr = 'data/api.json'

    def __init__(self):
        pass

    def getVersion(self):
        return self.__version

    ##### ----- start ----- ###

    # 取面板列表
    def getPanelListApi(self):
        data = jh.M('panel').field(
            'id,title,url,username,password,click,addtime').order('click desc').select()
        return jh.getJson(data)

    def addPanelInfoApi(self):
        title = request.form.get('title', '')
        url = request.form.get('url', '')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        # 校验是还是重复
        isAdd = jh.M('panel').where(
            'title=? OR url=?', (title, url)).count()
        if isAdd:
            return jh.returnJson(False, '备注或面板地址重复!')
        isRe = jh.M('panel').add('title,url,username,password,click,addtime',
                                 (title, url, username, password, 0, int(time.time())))
        if isRe:
            return jh.returnJson(True, '添加成功!')
        return jh.returnJson(False, '添加失败!')

    # 删除面板资料
    def delPanelInfoApi(self):
        mid = request.form.get('id', '')
        isExists = jh.M('panel').where('id=?', (mid,)).count()
        if not isExists:
            return jh.returnJson(False, '指定面板资料不存在!')
        jh.M('panel').where('id=?', (mid,)).delete()
        return jh.returnJson(True, '删除成功!')

     # 修改面板资料
    def setPanelInfoApi(self):
        title = request.form.get('title', '')
        url = request.form.get('url', '')
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        mid = request.form.get('id', '')
        # 校验是还是重复
        isSave = jh.M('panel').where(
            '(title=? OR url=?) AND id!=?', (title, url, mid)).count()
        if isSave:
            return jh.returnJson(False, '备注或面板地址重复!')

        # 更新到数据库
        isRe = jh.M('panel').where('id=?', (mid,)).save(
            'title,url,username,password', (title, url, username, password))
        if isRe:
            return jh.returnJson(True, '修改成功!')
        return jh.returnJson(False, '修改失败!')

    def syncDateApi(self):
        if jh.isAppleSystem():
            return jh.returnJson(True, '开发系统不必同步时间!')

        data = jh.execShell('ntpdate -s time.nist.gov')
        if data[0] == '':
            return jh.returnJson(True, '同步成功!')
        return jh.returnJson(False, '同步失败:' + data[0])

    def setPasswordApi(self):
        password1 = request.form.get('password1', '')
        password2 = request.form.get('password2', '')
        if password1 != password2:
            return jh.returnJson(False, '两次输入的密码不一致，请重新输入!')
        if len(password1) < 5:
            return jh.returnJson(False, '用户密码不能小于5位!')
        jh.M('users').where("username=?", (session['username'],)).setField(
            'password', jh.md5(password1.strip()))
        return jh.returnJson(True, '密码修改成功!')

    def setNameApi(self):
        name1 = request.form.get('name1', '')
        name2 = request.form.get('name2', '')
        if name1 != name2:
            return jh.returnJson(False, '两次输入的用户名不一致，请重新输入!')
        if len(name1) < 3:
            return jh.returnJson(False, '用户名长度不能少于3位')

        jh.M('users').where("username=?", (session['username'],)).setField(
            'username', name1.strip())

        session['username'] = name1
        return jh.returnJson(True, '用户修改成功!')

    def setWebnameApi(self):
        webname = request.form.get('webname', '')
        if webname != jh.getConfig('title'):
            jh.setConfig('title', webname)
        return jh.returnJson(True, '面板别名保存成功!')

    def setPortApi(self):
        port = request.form.get('port', '')
        if port != jh.getHostPort():
            import system_api
            import firewall_api

            sysCfgDir = jh.systemdCfgDir()
            if os.path.exists(sysCfgDir + "/firewalld.service"):
                if not firewall_api.firewall_api().getFwStatus():
                    return jh.returnJson(False, 'firewalld必须先启动!')

            jh.setHostPort(port)

            msg = jh.getInfo('放行端口[{1}]成功', (port,))
            jh.writeLog("防火墙管理", msg)
            addtime = time.strftime('%Y-%m-%d %X', time.localtime())
            jh.M('firewall').add('port,ps,addtime', (port, "配置修改", addtime))

            firewall_api.firewall_api().addAcceptPort(port)
            firewall_api.firewall_api().firewallReload()

            system_api.system_api().restartMw()

        return jh.returnJson(True, '端口保存成功!')

    def setIpApi(self):
        host_ip = request.form.get('host_ip', '')
        if host_ip != jh.getHostAddr():
            jh.setHostAddr(host_ip)
        return jh.returnJson(True, 'IP保存成功!')

    def setWwwDirApi(self):
        sites_path = request.form.get('sites_path', '')
        if sites_path != jh.getWwwDir():
            jh.setWwwDir(sites_path)
        return jh.returnJson(True, '修改默认建站目录成功!')

    def setBackupDirApi(self):
        backup_path = request.form.get('backup_path', '')
        if backup_path != jh.getBackupDir():
            jh.setBackupDir(backup_path)
        return jh.returnJson(True, '修改默认备份目录成功!')

    def setBasicAuthApi(self):
        basic_user = request.form.get('basic_user', '').strip()
        basic_pwd = request.form.get('basic_pwd', '').strip()
        basic_open = request.form.get('is_open', '').strip()

        salt = '_md_salt'
        path = 'data/basic_auth.json'
        is_open = True

        if basic_open == 'false':
            if os.path.exists(path):
                os.remove(path)
            return jh.returnJson(True, '删除BasicAuth成功!')

        if basic_user == '' or basic_pwd == '':
            return jh.returnJson(True, '用户和密码不能为空!')

        ba_conf = None
        if os.path.exists(path):
            try:
                ba_conf = json.loads(public.readFile(path))
            except:
                os.remove(path)

        if not ba_conf:
            ba_conf = {
                "basic_user": jh.md5(basic_user + salt),
                "basic_pwd": jh.md5(basic_pwd + salt),
                "open": is_open
            }
        else:
            ba_conf['basic_user'] = jh.md5(basic_user + salt)
            ba_conf['basic_pwd'] = jh.md5(basic_pwd + salt)
            ba_conf['open'] = is_open

        jh.writeFile(path, json.dumps(ba_conf))
        os.chmod(path, 384)
        jh.writeLog('面板设置', '设置BasicAuth状态为: %s' % is_open)

        jh.restartMw()
        return jh.returnJson(True, '设置成功!')

    def setApi(self):
        webname = request.form.get('webname', '')
        port = request.form.get('port', '')
        host_ip = request.form.get('host_ip', '')
        domain = request.form.get('domain', '')
        sites_path = request.form.get('sites_path', '')
        backup_path = request.form.get('backup_path', '')

        if domain != '':
            reg = "^([\w\-\*]{1,100}\.){1,4}(\w{1,10}|\w{1,10}\.\w{1,10})$"
            if not re.match(reg, domain):
                return jh.returnJson(False, '主域名格式不正确')

        if int(port) >= 65535 or int(port) < 100:
            return jh.returnJson(False, '端口范围不正确!')

        if webname != jh.getConfig('title'):
            jh.setConfig('title', webname)

        if sites_path != jh.getWwwDir():
            jh.setWwwDir(sites_path)

        if backup_path != jh.getWwwDir():
            jh.setBackupDir(backup_path)

        if port != jh.getHostPort():
            import system_api
            import firewall_api

            sysCfgDir = jh.systemdCfgDir()
            if os.path.exists(sysCfgDir + "/firewalld.service"):
                if not firewall_api.firewall_api().getFwStatus():
                    return jh.returnJson(False, 'firewalld必须先启动!')

            jh.setHostPort(port)

            msg = jh.getInfo('放行端口[{1}]成功', (port,))
            jh.writeLog("防火墙管理", msg)
            addtime = time.strftime('%Y-%m-%d %X', time.localtime())
            jh.M('firewall').add('port,ps,addtime', (port, "配置修改", addtime))

            firewall_api.firewall_api().addAcceptPort(port)
            firewall_api.firewall_api().firewallReload()

            system_api.system_api().restartMw()

        if host_ip != jh.getHostAddr():
            jh.setHostAddr(host_ip)

        mhost = jh.getHostAddr()
        info = {
            'uri': '/config',
            'host': mhost + ':' + port
        }
        return jh.returnJson(True, '保存成功!', info)

    def setAdminPathApi(self):
        admin_path = request.form.get('admin_path', '').strip()
        admin_path_checks = ['/', '/close', '/login',
                             '/do_login', '/site', '/sites',
                             '/download_file', '/control', '/crontab',
                             '/firewall', '/files', 'config',
                             '/soft', '/system', '/code',
                             '/ssl', '/plugins', '/hook']
        if admin_path == '':
            admin_path = '/'
        if admin_path != '/':
            if len(admin_path) < 6:
                return jh.returnJson(False, '安全入口地址长度不能小于6位!')
            if admin_path in admin_path_checks:
                return jh.returnJson(False, '该入口已被面板占用,请使用其它入口!')
            if not re.match("^/[\w\./-_]+$", admin_path):
                return jh.returnJson(False, '入口地址格式不正确,示例: /jh_rand')
        # else:
        #     domain = jh.readFile('data/bind_domain.pl')
        #     if not domain:
        #         domain = ''
        #     limitip = jh.readFile('data/bind_limitip.pl')
        #     if not limitip:
        #         limitip = ''
        #     if not domain.strip() and not limitip.strip():
        # return jh.returnJson(False,
        # '警告，关闭安全入口等于直接暴露你的后台地址在外网，十分危险，至少开启以下一种安全方式才能关闭：<a
        # style="color:red;"><br>1、绑定访问域名<br>2、绑定授权IP</a>')

        admin_path_file = 'data/admin_path.pl'
        admin_path_old = '/'
        if os.path.exists(admin_path_file):
            admin_path_old = jh.readFile(admin_path_file).strip()

        if admin_path_old != admin_path:
            jh.writeFile(admin_path_file, admin_path)
            jh.restartMw()
        return jh.returnJson(True, '修改成功!')

    def closePanelApi(self):
        filename = 'data/close.pl'
        if os.path.exists(filename):
            os.remove(filename)
            return jh.returnJson(True, '开启成功')
        jh.writeFile(filename, 'True')
        jh.execShell("chmod 600 " + filename)
        jh.execShell("chown root.root " + filename)
        return jh.returnJson(True, '面板已关闭!')

    def openDebugApi(self):
        filename = 'data/debug.pl'
        if os.path.exists(filename):
            os.remove(filename)
            return jh.returnJson(True, '开发模式关闭!')
        jh.writeFile(filename, 'True')
        return jh.returnJson(True, '开发模式开启!')

    def setIpv6StatusApi(self):
        ipv6_file = 'data/ipv6.pl'
        if os.path.exists('data/ipv6.pl'):
            os.remove(ipv6_file)
            jh.writeLog('面板设置', '关闭面板IPv6兼容!')
        else:
            jh.writeFile(ipv6_file, 'True')
            jh.writeLog('面板设置', '开启面板IPv6兼容!')
        jh.restartMw()
        return jh.returnJson(True, '设置成功!')

    def setEnvToCnApi(self):
        net_env_cn_file = 'data/net_env_cn.pl'
        if os.path.exists('data/net_env_cn.pl'):
            os.remove(net_env_cn_file)
            jh.writeLog('面板设置', '切换国际源成功!')
            jh.restartMw()
            return jh.returnJson(True, '切换国际源成功!')
        else:
            jh.writeFile(net_env_cn_file, 'True')
            jh.writeLog('面板设置', '切换中国源成功!')
            jh.restartMw()
            return jh.returnJson(True, '切换中国源成功!')

    # 获取面板证书
    def getPanelSslApi(self):
        cert = {}

        keyPath = 'ssl/private.pem'
        certPath = 'ssl/cert.pem'

        if not os.path.exists(certPath):
            jh.createSSL()

        cert['privateKey'] = jh.readFile(keyPath)
        cert['certPem'] = jh.readFile(certPath)
        cert['rep'] = os.path.exists('ssl/input.pl')
        cert['info'] = jh.getCertName(certPath)
        return jh.getJson(cert)

    # 保存面板证书
    def savePanelSslApi(self):
        keyPath = 'ssl/private.pem'
        certPath = 'ssl/cert.pem'
        checkCert = '/tmp/cert.pl'

        certPem = request.form.get('certPem', '').strip()
        privateKey = request.form.get('privateKey', '').strip()

        if(privateKey.find('KEY') == -1):
            return jh.returnJson(False, '秘钥错误，请检查!')
        if(certPem.find('CERTIFICATE') == -1):
            return jh.returnJson(False, '证书错误，请检查!')

        jh.writeFile(checkCert, certPem)
        if privateKey:
            jh.writeFile(keyPath, privateKey)
        if certPem:
            jh.writeFile(certPath, certPem)
        if not jh.checkCert(checkCert):
            return jh.returnJson(False, '证书错误,请检查!')
        jh.writeFile('ssl/input.pl', 'True')
        return jh.returnJson(True, '证书已保存!')

    def setPanelDomainApi(self):
        domain = request.form.get('domain', '')

        panel_tpl = jh.getRunDir() + "/data/tpl/nginx_panel.conf"
        dst_panel_path = jh.getServerDir() + "/web_conf/nginx/vhost/panel.conf"

        cfg_domain = 'data/bind_domain.pl'
        if domain == '':
            os.remove(cfg_domain)
            os.remove(dst_panel_path)
            jh.restartWeb()
            return jh.returnJson(True, '清空域名成功!')

        reg = r"^([\w\-\*]{1,100}\.){1,4}(\w{1,10}|\w{1,10}\.\w{1,10})$"
        if not re.match(reg, domain):
            return jh.returnJson(False, '主域名格式不正确')

        op_dir = jh.getServerDir() + "/openresty"
        if not os.path.exists(op_dir):
            return jh.returnJson(False, '依赖OpenResty,先安装启动它!')

        content = jh.readFile(panel_tpl)
        content = content.replace("{$PORT}", "80")
        content = content.replace("{$SERVER_NAME}", domain)
        content = content.replace("{$PANAL_PORT}", jh.readFile('data/port.pl'))
        content = content.replace("{$LOGPATH}", jh.getRunDir() + '/logs')
        content = content.replace("{$PANAL_ADDR}", jh.getRunDir())
        jh.writeFile(dst_panel_path, content)
        jh.restartWeb()

        jh.writeFile(cfg_domain, domain)
        return jh.returnJson(True, '设置域名成功!')

     # 设置面板SSL
    def setPanelSslApi(self):
        sslConf = jh.getRunDir() + '/data/ssl.pl'

        panel_tpl = jh.getRunDir() + "/data/tpl/nginx_panel.conf"
        dst_panel_path = jh.getServerDir() + "/web_conf/nginx/vhost/panel.conf"
        if os.path.exists(sslConf):
            os.system('rm -f ' + sslConf)

            conf = jh.readFile(dst_panel_path)
            if conf:
                rep = "\s+ssl_certificate\s+.+;\s+ssl_certificate_key\s+.+;"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_protocols\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_ciphers\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_prefer_server_ciphers\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_session_cache\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_session_timeout\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_ecdh_curve\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_session_tickets\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_stapling\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl_stapling_verify\s+.+;\n"
                conf = re.sub(rep, '', conf)
                rep = "\s+ssl\s+on;"
                conf = re.sub(rep, '', conf)
                rep = "\s+error_page\s497.+;"
                conf = re.sub(rep, '', conf)
                rep = "\s+if.+server_port.+\n.+\n\s+\s*}"
                conf = re.sub(rep, '', conf)
                rep = "\s+listen\s+443.*;"
                conf = re.sub(rep, '', conf)
                rep = "\s+listen\s+\[\:\:\]\:443.*;"
                conf = re.sub(rep, '', conf)
                jh.writeFile(dst_panel_path, conf)

            jh.writeLog('面板配置', '面板SSL关闭成功!')
            jh.restartMw(True)
            return jh.returnJson(True, 'SSL已关闭，即将跳转http协议访问面板!')
        else:
            try:
                if not os.path.exists('ssl/input.ssl'):
                    jh.createSSL()
                jh.writeFile(sslConf, 'True')

                keyPath = jh.getRunDir() + '/ssl/private.pem'
                certPath = jh.getRunDir() + '/ssl/cert.pem'

                conf = jh.readFile(dst_panel_path)
                if conf:
                    if conf.find('ssl_certificate') == -1:
                        sslStr = """#error_page 404/404.html;
    ssl_certificate    %s;
    ssl_certificate_key  %s;
    ssl_protocols TLSv1 TLSv1.1 TLSv1.2;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:HIGH:!aNULL:!MD5:!RC4:!DHE;
    ssl_prefer_server_ciphers on;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    error_page 497  https://$host$request_uri;""" % (certPath, keyPath)
                    if(conf.find('ssl_certificate') != -1):
                        return jh.returnJson(True, 'SSL开启成功!')

                    conf = conf.replace('#error_page 404/404.html;', sslStr)

                    rep = "listen\s+([0-9]+)\s*[default_server]*;"
                    tmp = re.findall(rep, conf)
                    if not jh.inArray(tmp, '443'):
                        listen = re.search(rep, conf).group()
                        http_ssl = "\n\tlisten 443 ssl http2;"
                        http_ssl = http_ssl + "\n\tlisten [::]:443 ssl http2;"
                        conf = conf.replace(listen, listen + http_ssl)

                    jh.backFile(dst_panel_path)
                    jh.writeFile(dst_panel_path, conf)
                    isError = jh.checkWebConfig()
                    if(isError != True):
                        jh.restoreFile(dst_panel_path)
                        return jh.returnJson(False, '证书错误: <br><a style="color:red;">' + isError.replace("\n", '<br>') + '</a>')
            except Exception as ex:
                return jh.returnJson(False, '开启失败:' + str(ex))
            jh.restartMw(True)
            return jh.returnJson(True, '开启SSL成功，即将跳转https协议访问面板!')

    # 更新面板SSL证书
    def updatePanelSslApi(self):
        jh.execShell('rm -f %s/ssl/input.pl' % jh.getRunDir())
        jh.createSSL()
        return jh.returnJson(True, '更新SSL证书成功!')

    def getApi(self):
        data = {}
        return jh.getJson(data)
    ##### ----- end ----- ###

    # 获取临时登录列表
    def getTempLoginApi(self):
        if 'tmp_login_expire' in session:
            return jh.returnJson(False, '没有权限')
        limit = request.form.get('limit', '10').strip()
        p = request.form.get('p', '1').strip()
        tojs = request.form.get('tojs', '').strip()

        tempLoginM = jh.M('temp_login')
        tempLoginM.where('state=? and expire<?',
                         (0, int(time.time()))).setField('state', -1)

        start = (int(p) - 1) * (int(limit))
        vlist = tempLoginM.limit(str(start) + ',' + str(limit)).order('id desc').field(
            'id,addtime,expire,login_time,login_addr,state').select()

        data = {}
        data['data'] = vlist

        count = tempLoginM.count()
        page_args = {}
        page_args['count'] = count
        page_args['tojs'] = 'get_temp_login'
        page_args['p'] = p
        page_args['row'] = limit

        data['page'] = jh.getPage(page_args)
        return jh.getJson(data)

    # 删除临时登录
    def removeTempLoginApi(self):
        if 'tmp_login_expire' in session:
            return jh.returnJson(False, '没有权限')
        sid = request.form.get('id', '10').strip()
        if jh.M('temp_login').where('id=?', (sid,)).delete():
            jh.writeLog('面板设置', '删除临时登录连接')
            return jh.returnJson(True, '删除成功')
        return jh.returnJson(False, '删除失败')

    def setTempLoginApi(self):
        if 'tmp_login_expire' in session:
            return jh.returnJson(False, '没有权限')
        s_time = int(time.time())
        jh.M('temp_login').where(
            'state=? and expire>?', (0, s_time)).delete()
        token = jh.getRandomString(48)
        salt = jh.getRandomString(12)

        pdata = {
            'token': jh.md5(token + salt),
            'salt': salt,
            'state': 0,
            'login_time': 0,
            'login_addr': '',
            'expire': s_time + 3600,
            'addtime': s_time
        }

        if not jh.M('temp_login').count():
            pdata['id'] = 101

        if jh.M('temp_login').insert(pdata):
            jh.writeLog('面板设置', '生成临时连接,过期时间:{}'.format(
                jh.formatDate(times=pdata['expire'])))
            return jh.getJson({'status': True, 'msg': "临时连接已生成", 'token': token, 'expire': pdata['expire']})
        return jh.returnJson(False, '连接生成失败')

    def getTempLoginLogsApi(self):
        if 'tmp_login_expire' in session:
            return jh.returnJson(False, '没有权限')

        logs_id = request.form.get('id', '').strip()
        logs_id = int(logs_id)
        data = jh.M('logs').where(
            'uid=?', (logs_id,)).order('id desc').field(
            'id,type,uid,log,addtime').select()
        return jh.returnJson(False, 'ok', data)

    def checkPanelToken(self):
        api_file = self.__api_addr
        if not os.path.exists(api_file):
            return False, ''

        tmp = jh.readFile(api_file)
        data = json.loads(tmp)
        if data['open']:
            return True, data
        else:
            return False, ''

    def getPanelTokenApi(self):
        api_file = self.__api_addr

        tmp = jh.readFile(api_file)
        if not os.path.exists(api_file):
            ready_data = {"open": False, "token": "", "limit_addr": []}
            jh.writeFile(api_file, json.dumps(ready_data))
            jh.execShell("chmod 600 " + api_file)
            tmp = jh.readFile(api_file)
        data = json.loads(tmp)

        if not 'key' in data:
            data['key'] = jh.getRandomString(16)
            jh.writeFile(api_file, json.dumps(data))

        if 'token_crypt' in data:
            data['token'] = jh.deCrypt(data['token'], data['token_crypt'])
        else:
            token = jh.getRandomString(32)
            data['token'] = jh.md5(token)
            data['token_crypt'] = jh.enCrypt(
                data['token'], token).decode('utf-8')
            jh.writeFile(api_file, json.dumps(data))
            data['token'] = "***********************************"

        data['limit_addr'] = '\n'.join(data['limit_addr'])

        del(data['key'])
        return jh.returnJson(True, 'ok', data)
    
    def getNotifyApi(self):
        # 获取
        data = jh.getNotifyData(True)
        return jh.returnData(True, 'ok', data)

    def setNotifyApi(self):
        tag = request.form.get('tag', '').strip()
        data = request.form.get('data', '').strip()

        cfg = jh.getNotifyData(False)

        crypt_data = jh.enDoubleCrypt(tag, data)
        if tag in cfg:
            cfg[tag]['cfg'] = crypt_data
        else:
            t = {'cfg': crypt_data}
            cfg[tag] = t

        jh.writeNotify(cfg)
        return jh.returnData(True, '设置成功')

    def setNotifyTestApi(self):
        # 异步通知验证
        tag = request.form.get('tag', '').strip()
        tag_data = request.form.get('data', '').strip()

        if tag == 'tgbot':
            t = json.loads(tag_data)
            test_bool = jh.tgbotNotifyTest(t['app_token'], t['chat_id'])
            if test_bool:
                return jh.returnData(True, '验证成功')
            return jh.returnData(False, '验证失败')

        if tag == 'email':
            t = json.loads(tag_data)
            test_bool = jh.emailNotifyTest(t)
            if test_bool:
                return jh.returnData(True, '验证成功')
            return jh.returnData(False, '验证失败')

        return jh.returnData(False, '暂时未支持该验证')

    def setNotifyEnableApi(self):
        # 异步通知验证
        tag = request.form.get('tag', '').strip()
        tag_enable = request.form.get('enable', '').strip()

        data = jh.getNotifyData(False)
        op_enable = True
        op_action = '开启'
        if tag_enable != 'true':
            op_enable = False
            op_action = '关闭'

        if tag in data:
            data[tag]['enable'] = op_enable

        jh.writeNotify(data)

        return jh.returnData(True, op_action + '成功')


    def setPanelTokenApi(self):
        op_type = request.form.get('op_type', '').strip()

        api_file = self.__api_addr
        tmp = jh.readFile(api_file)
        data = json.loads(tmp)

        if op_type == '1':
            token = jh.getRandomString(32)
            data['token'] = jh.md5(token)
            data['token_crypt'] = jh.enCrypt(
                data['token'], token).decode('utf-8')
            jh.writeLog('API配置', '重新生成API-Token')
            jh.writeFile(api_file, json.dumps(data))
            return jh.returnJson(True, 'ok', token)

        elif op_type == '2':
            data['open'] = not data['open']
            stats = {True: '开启', False: '关闭'}
            if not 'token_crypt' in data:
                token = jh.getRandomString(32)
                data['token'] = jh.md5(token)
                data['token_crypt'] = jh.enCrypt(
                    data['token'], token).decode('utf-8')

            token = stats[data['open']] + '成功!'
            jh.writeLog('API配置', '%sAPI接口' % stats[data['open']])
            jh.writeFile(api_file, json.dumps(data))
            return jh.returnJson(not not data['open'], token)

        elif op_type == '3':
            limit_addr = request.form.get('limit_addr', '').strip()
            data['limit_addr'] = limit_addr.split('\n')
            jh.writeLog('API配置', '变更IP限制为[%s]' % limit_addr)
            jh.writeFile(api_file, json.dumps(data))
            return jh.returnJson(True, '保存成功!')

    def get(self):

        data = {}
        data['title'] = jh.getConfig('title')
        data['site_path'] = jh.getWwwDir()
        data['backup_path'] = jh.getBackupDir()
        sformat = 'date +"%Y-%m-%d %H:%M:%S %Z %z"'
        data['systemdate'] = jh.execShell(sformat)[0].strip()

        data['port'] = jh.getHostPort()
        data['ip'] = jh.getHostAddr()

        admin_path_file = 'data/admin_path.pl'
        if not os.path.exists(admin_path_file):
            data['admin_path'] = '/'
        else:
            data['admin_path'] = jh.readFile(admin_path_file)

        ipv6_file = 'data/ipv6.pl'
        if os.path.exists(ipv6_file):
            data['ipv6'] = 'checked'
        else:
            data['ipv6'] = ''
        
        net_env_cn_file = 'data/net_env_cn.pl'
        if os.path.exists(net_env_cn_file):
            data['net_env_cn'] = 'checked'
        else:
            data['net_env_cn'] = ''

        debug_file = 'data/debug.pl'
        if os.path.exists(debug_file):
            data['debug'] = 'checked'
        else:
            data['debug'] = ''

        ssl_file = 'data/ssl.pl'
        if os.path.exists('data/ssl.pl'):
            data['ssl'] = 'checked'
        else:
            data['ssl'] = ''

        basic_auth = 'data/basic_auth.json'
        if os.path.exists(basic_auth):
            bac = jh.readFile(basic_auth)
            bac = json.loads(bac)
            if bac['open']:
                data['basic_auth'] = 'checked'
        else:
            data['basic_auth'] = ''

        cfg_domain = 'data/bind_domain.pl'
        if os.path.exists(cfg_domain):
            domain = jh.readFile(cfg_domain)
            data['bind_domain'] = domain.strip()
        else:
            data['bind_domain'] = ''

        api_token = self.__api_addr
        if os.path.exists(api_token):
            bac = jh.readFile(api_token)
            bac = json.loads(bac)
            if bac['open']:
                data['api_token'] = 'checked'
        else:
            data['api_token'] = ''

        data['site_count'] = jh.M('sites').count()

        data['username'] = jh.M('users').where(
            "id=?", (1,)).getField('username')

        data['hook_tag'] = request.args.get('tag', '')

        # databases hook
        database_hook_file = 'data/hook_database.json'
        if os.path.exists(database_hook_file):
            df = jh.readFile(database_hook_file)
            df = json.loads(df)
            data['hook_database'] = df
        else:
            data['hook_database'] = []

        # menu hook
        menu_hook_file = 'data/hook_menu.json'
        if os.path.exists(menu_hook_file):
            df = jh.readFile(menu_hook_file)
            df = json.loads(df)
            data['hook_menu'] = df
        else:
            data['hook_menu'] = []

        # global_static hook
        global_static_hook_file = 'data/hook_global_static.json'
        if os.path.exists(global_static_hook_file):
            df = jh.readFile(global_static_hook_file)
            df = json.loads(df)
            data['hook_global_static'] = df
        else:
            data['hook_global_static'] = []

        # notiy config
        notify_data = jh.getNotifyData(True)
        notify_tag_list = ['tgbot', 'email']
        for tag in notify_tag_list:
            new_tag = 'notify_' + tag + '_enable'
            data[new_tag] = ''
            if tag in notify_data and 'enable' in notify_data[tag]:
                if notify_data[tag]['enable']:
                    data[new_tag] = 'checked'

        return data
