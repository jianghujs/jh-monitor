# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖面板
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-panel) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 防火墙操作
# ---------------------------------------------------------------------------------


import psutil
import time
import os
import sys
import jh
import re
import json
import pwd

from flask import request


class firewall_api:

    __isFirewalld = False
    __isUfw = False
    __isMac = False

    def __init__(self):
        if os.path.exists('/usr/sbin/firewalld'):
            self.__isFirewalld = True
        if os.path.exists('/usr/sbin/ufw'):
            self.__isUfw = True
        if jh.isAppleSystem():
            self.__isMac = True

    ##### ----- start ----- ###
    # 添加屏蔽IP
    def addDropAddressApi(self):
        import re
        port = request.form.get('port', '').strip()
        ps = request.form.get('ps', '').strip()

        rep = "^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(\/\d{1,2})?$"
        if not re.search(rep, port):
            return jh.returnJson(False, '您输入的IP地址不合法!')
        address = port
        if jh.M('firewall').where("port=?", (address,)).count() > 0:
            return jh.returnJson(False, '您要放屏蔽的IP已存在屏蔽列表，无需重复处理!')
        if self.__isUfw:
            jh.execShell('ufw deny from ' + address + ' to any')
        else:
            if self.__isFirewalld:
                cmd = 'firewall-cmd --permanent --add-rich-rule=\'rule family=ipv4 source address="' + \
                    address + '" drop\''
                jh.execShell(cmd)
            else:
                cmd = 'iptables -I INPUT -s ' + address + ' -j DROP'
                jh.execShell(cmd)

        msg = jh.getInfo('屏蔽IP[{1}]成功!', (address,))
        jh.writeLog("防火墙管理", msg)
        addtime = time.strftime('%Y-%m-%d %X', time.localtime())
        jh.M('firewall').add('port,ps,addtime', (address, ps, addtime))
        self.firewallReload()
        return jh.returnJson(True, '添加成功!')

    # 添加放行端口
    def addAcceptPortApi(self):
        if not self.getFwStatus():
            return jh.returnJson(False, '防火墙启动时,才能添加规则!')

        port = request.form.get('port', '').strip()
        protocol = request.form.get('protocol', '').strip()
        ps = request.form.get('ps', '').strip()
        stype = request.form.get('type', '').strip()
        data = self.addAcceptPortArgs(port, protocol, ps, stype)
        return jh.getJson(data)

    # 添加放行端口
    def addAcceptPortArgs(self, port, protocol, ps, stype):
        import re
        import time

        if not self.getFwStatus():
            self.setFw(0)

        rep = "^\d{1,5}(:\d{1,5})?$"
        if not re.search(rep, port):
            return jh.returnData(False, '端口范围不正确!')

        if jh.M('firewall').where("port=?", (port,)).count() > 0:
            return jh.returnData(False, '您要放行的端口已存在，无需重复放行!')

        msg = jh.getInfo('放行端口[{1}]成功', (port,))
        jh.writeLog("防火墙管理", msg)
        addtime = time.strftime('%Y-%m-%d %X', time.localtime())
        
        jh.M('firewall').add('port,protocol,ps,addtime', (port, protocol, ps, addtime))

        self.addAcceptPort(port, protocol)
        self.firewallReload()
        return jh.returnData(True, '添加放行(' + port + ')端口成功!')

    # 删除IP屏蔽
    def delDropAddressApi(self):
        if not self.getFwStatus():
            return jh.returnJson(False, '防火墙启动时,才能删除规则!')

        port = request.form.get('port', '').strip()
        ps = request.form.get('ps', '').strip()
        sid = request.form.get('id', '').strip()
        address = port
        if self.__isUfw:
            jh.execShell('ufw delete deny from ' + address + ' to any')
        else:
            if self.__isFirewalld:
                jh.execShell(
                    'firewall-cmd --permanent --remove-rich-rule=\'rule family=ipv4 source address="' + address + '" drop\'')
            elif self.__isMac:
                pass
            else:
                cmd = 'iptables -D INPUT -s ' + address + ' -j DROP'
                jh.execShell(cmd)

        msg = jh.getInfo('解除IP[{1}]的屏蔽!', (address,))
        jh.writeLog("防火墙管理", msg)
        jh.M('firewall').where("id=?", (sid,)).delete()

        self.firewallReload()
        return jh.returnJson(True, '删除成功!')

    # 删除放行端口
    def delAcceptPortApi(self):
        port = request.form.get('port', '').strip()
        protocol = request.form.get('protocol', '').strip()
        
        sid = request.form.get('id', '').strip()
        jh_port = jh.readFile('data/port.pl')

        protocol_list = protocol.split('/')
        try:
            if(port == jh_port):
                return jh.returnJson(False, '失败，不能删除当前面板端口!')
            for protocol in protocol_list:
                if self.__isUfw:
                    jh.execShell('ufw delete allow ' + port + '/' + protocol)
                else:
                    if self.__isFirewalld:
                        jh.execShell(
                            'firewall-cmd --permanent --zone=public --remove-port=' + port + '/' + protocol)
                    else:
                        jh.execShell(
                            'iptables -D INPUT -p ' + protocol + ' -m state --state NEW -m ' + protocol + ' --dport ' + port + ' -j ACCEPT')
            msg = jh.getInfo('删除防火墙放行端口[{1}]成功!', (port,))
            jh.writeLog("防火墙管理", msg)
            jh.M('firewall').where("id=?", (sid,)).delete()

            self.firewallReload()
            return jh.returnJson(True, '删除成功!')
        except Exception as e:
            return jh.returnJson(False, '删除失败!:' + str(e))

    def getWwwPathApi(self):
        path = jh.getLogsDir()
        return jh.getJson({'path': path})

    def getListApi(self):

        # TODO 兼容旧版本，检查并添加protocol字段
        firewall_db = jh.M('firewall')
        firewall_columns = firewall_db.originExecute("PRAGMA table_info(firewall)").fetchall()
        protocol_exists = any(column[1] == 'protocol' for column in firewall_columns)
        if not protocol_exists:
            firewall_db.originExecute("ALTER TABLE firewall ADD COLUMN protocol varchar(50) DEFAULT 'tcp'")

        p = request.form.get('p', '1').strip()
        limit = request.form.get('limit', '10').strip()
        return self.getList(int(p), int(limit))

    def getLogListApi(self):
        p = request.form.get('p', '1').strip()
        limit = request.form.get('limit', '10').strip()
        search = request.form.get('search', '').strip()
        return self.getLogList(int(p), int(limit), search)

    def getSshInfoApi(self):
        data = {}

        file = '/etc/ssh/sshd_config'
        conf = jh.readFile(file)
        rep = "#*Port\s+([0-9]+)\s*\n"
        port = re.search(rep, conf).groups(0)[0]

        isPing = True
        try:
            if jh.isAppleSystem():
                isPing = True
            else:
                file = '/etc/sysctl.conf'
                sys_conf = jh.readFile(file)
                rep = "#*net\.ipv4\.icmp_echo_ignore_all\s*=\s*([0-9]+)"
                tmp = re.search(rep, sys_conf).groups(0)[0]
                if tmp == '1':
                    isPing = False
        except:
            isPing = True

        # sshd 检测
        status = True
        cmd = "service sshd status | grep -P '(dead|stop)'|grep -v grep"
        ssh_status = jh.execShell(cmd)
        if ssh_status[0] != '':
            status = False

        cmd = "systemctl status sshd.service | grep 'dead'|grep -v grep"
        ssh_status = jh.execShell(cmd)
        if ssh_status[0] != '':
            status = False

        data['pass_prohibit_status'] = False
        # 密码登陆配置检查
        pass_rep = "#PasswordAuthentication\s+(\w*)\s*\n"
        pass_status = re.search(pass_rep, conf)
        if pass_status:
            data['pass_prohibit_status'] = True

        if not data['pass_prohibit_status']:
            pass_rep = "PasswordAuthentication\s+(\w*)\s*\n"
            pass_status = re.search(pass_rep, conf)
            if pass_status and pass_status.groups(0)[0].strip() == 'no':
                data['pass_prohibit_status'] = True

        data['port'] = port
        data['status'] = status
        data['ping'] = isPing
        if jh.isAppleSystem():
            data['firewall_status'] = False
        else:
            data['firewall_status'] = self.getFwStatus()
        return jh.getJson(data)

    def setSshPortApi(self):
        port = request.form.get('port', '1').strip()
        if int(port) < 22 or int(port) > 65535:
            return jh.returnJson(False, '端口范围必需在22-65535之间!')

        ports = ['21', '25', '80', '443', '888']
        if port in ports:
            return jh.returnJson(False, '(' + port + ')' + '特殊端口不可设置!')

        file = '/etc/ssh/sshd_config'
        conf = jh.readFile(file)

        rep = "#*Port\s+([0-9]+)\s*\n"
        conf = re.sub(rep, "Port " + port + "\n", conf)
        jh.writeFile(file, conf)

        if self.__isFirewalld:
            jh.execShell('setenforce 0')
            jh.execShell(
                'sed -i "s#SELINUX=enforcing#SELINUX=disabled#" /etc/selinux/config')
            jh.execShell("systemctl restart sshd.service")
        elif self.__isUfw:
            jh.execShell('ufw allow ' + port + '/tcp')
            jh.execShell("service ssh restart")
        else:
            jh.execShell(
                'iptables -I INPUT -p tcp -m state --state NEW -m tcp --dport ' + port + ' -j ACCEPT')
            jh.execShell("/etc/init.d/sshd restart")

        self.firewallReload()
        # jh.M('firewall').where(
        #     "ps=?", ('SSH远程管理服务',)).setField('port', port)
        msg = "改SSH端口为[{}]成功!".format(port)
        jh.writeLog("防火墙管理", msg)
        return jh.returnJson(True, '修改成功!')

    def setSshStatusApi(self):
        if jh.isAppleSystem():
            return jh.returnJson(True, '开发机不能操作!')

        status = request.form.get('status', '1').strip()
        msg = 'SSH服务已启用'
        act = 'start'
        if status == "1":
            msg = 'SSH服务已停用'
            act = 'stop'

        ssh_service = jh.systemdCfgDir() + '/sshd.service'
        if os.path.exists(ssh_service):
            jh.execShell("systemctl " + act + " sshd.service")
        else:
            jh.execShell('service sshd ' + act)

        if os.path.exists('/etc/init.d/sshd'):
            jh.execShell('/etc/init.d/sshd ' + act)

        jh.writeLog("防火墙管理", msg)
        return jh.returnJson(True, '操作成功!')

    def setSshPassStatusApi(self):
        if jh.isAppleSystem():
            return jh.returnJson(True, '开发机不能操作!')

        status = request.form.get('status', '1').strip()
        msg = '禁止密码登陆成功'
        if status == "1":
            msg = '开启密码登陆成功'

        file = '/etc/ssh/sshd_config'
        if not os.path.exists(file):
            return jh.returnJson(False, '无法设置!')

        conf = jh.readFile(file)

        if status == '1':
            rep = "(#)?PasswordAuthentication\s+(\w*)\s*\n"
            conf = re.sub(rep, "PasswordAuthentication yes\n", conf)
        else:
            rep = "(#)?PasswordAuthentication\s+(\w*)\s*\n"
            conf = re.sub(rep, "PasswordAuthentication no\n", conf)
        jh.writeFile(file, conf)
        jh.execShell("systemctl restart sshd.service")
        jh.writeLog("SSH管理", msg)
        return jh.returnJson(True, msg)

    def setPingApi(self):
        if jh.isAppleSystem():
            return jh.returnJson(True, '开发机不能操作!')

        status = request.form.get('status')
        filename = '/etc/sysctl.conf'
        conf = jh.readFile(filename)
        if conf.find('net.ipv4.icmp_echo') != -1:
            rep = u"net\.ipv4\.icmp_echo.*"
            conf = re.sub(rep, 'net.ipv4.icmp_echo_ignore_all=' + status, conf)
        else:
            conf += "\nnet.ipv4.icmp_echo_ignore_all=" + status

        jh.writeFile(filename, conf)
        jh.execShell('sysctl -p')
        return jh.returnJson(True, '设置成功!')

    def setFwApi(self):
        if jh.isAppleSystem():
            return jh.returnJson(True, '开发机不能设置!')

        status = request.form.get('status', '1')
        return jh.getJson(self.setFw(status))

    def setFw(self, status):
        if status == '1':
            if self.__isUfw:
                jh.execShell('/usr/sbin/ufw disable')
            if self.__isFirewalld:
                jh.execShell('systemctl stop firewalld.service')
                jh.execShell('systemctl disable firewalld.service')
            elif self.__isMac:
                pass
            else:
                jh.execShell('/etc/init.d/iptables save')
                jh.execShell('/etc/init.d/iptables stop')
        else:
            if self.__isUfw:
                jh.execShell("echo 'y'| ufw enable")
            if self.__isFirewalld:
                jh.execShell('systemctl start firewalld.service')
                jh.execShell('systemctl enable firewalld.service')
            elif self.__isMac:
                pass
            else:
                jh.execShell('/etc/init.d/iptables save')
                jh.execShell('/etc/init.d/iptables restart')

        return jh.returnData(True, '设置成功!')

    def delPanelLogsApi(self):
        jh.M('logs').where('id>?', (0,)).delete()
        jh.writeLog('面板设置', '面板操作日志已清空!')
        return jh.returnJson(True, '面板操作日志已清空!')

    ##### ----- start ----- ###

    def getList(self, page, limit):

        start = (page - 1) * limit

        _list = jh.M('firewall').field('id,port,protocol,ps,addtime').limit(
            str(start) + ',' + str(limit)).order('id desc').select()
        data = {}
        data['data'] = _list

        count = jh.M('firewall').count()
        _page = {}
        _page['count'] = count
        _page['tojs'] = 'showAccept'
        _page['p'] = page

        data['page'] = jh.getPage(_page)
        return jh.getJson(data)

    def getLogList(self, page, limit, search=''):
        find_search = ''
        if search != '':
            find_search = "type like '%" + search + "%' or log like '%" + \
                search + "%' or addtime like '%" + search + "%'"

        start = (page - 1) * limit

        _list = jh.M('logs').where(find_search, ()).field(
            'id,type,log,addtime').limit(str(start) + ',' + str(limit)).order('id desc').select()
        data = {}
        data['data'] = _list

        count = jh.M('logs').where(find_search, ()).count()
        _page = {}
        _page['count'] = count
        _page['tojs'] = 'getLogs'
        _page['p'] = page

        data['page'] = jh.getPage(_page)
        return jh.getJson(data)

    def addAcceptPort(self, port, protocol):
        protocol_list = protocol.split('/')
        
        for protocol in protocol_list:
            if self.__isUfw:
                jh.execShell('ufw allow ' + port + '/' + protocol)
            elif self.__isFirewalld:
                port = port.replace(':', '-')
                cmd = 'firewall-cmd --permanent --zone=public --add-port=' + port + '/' + protocol
                jh.execShell(cmd)
            elif self.__isMac:
                pass
            else:
                cmd = 'iptables -I INPUT -p ' + protocol + ' -m state --state NEW -m ' + protocol + ' --dport ' + port + ' -j ACCEPT'
                jh.execShell(cmd)

    def firewallReload(self):
        if self.__isUfw:
            jh.execShell('/usr/sbin/ufw reload')
            return
        if self.__isFirewalld:
            jh.execShell('firewall-cmd --reload')
        elif self.__isMac:
            pass
        else:
            jh.execShell('/etc/init.d/iptables save')
            jh.execShell('/etc/init.d/iptables restart')

    def getFwStatus(self):
        if self.__isUfw:
            cmd = "/usr/sbin/ufw status| grep Status | awk -F ':' '{print $2}'"
            data = jh.execShell(cmd)
            if data[0].strip() == 'inactive':
                return False
            return True
        if self.__isFirewalld:
            cmd = "ps -ef|grep firewalld |grep -v grep | awk '{print $2}'"
            data = jh.execShell(cmd)
            if data[0] == '':
                return False
            return True
        elif self.__isMac:
            return False
        else:
            cmd = "ps -ef|grep iptables |grep -v grep  | awk '{print $2}'"
            data = jh.execShell(cmd)
            if data[0] == '':
                return False
            return True
