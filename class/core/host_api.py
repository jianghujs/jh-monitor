# coding: utf-8

# ---------------------------------------------------------------------------------
# 江湖云监控
# ---------------------------------------------------------------------------------
# copyright (c) 2018-∞(https://github.com/jianghujs/jh-monitor) All rights reserved.
# ---------------------------------------------------------------------------------
# Author: midoks <midoks@163.com>
# ---------------------------------------------------------------------------------

# ---------------------------------------------------------------------------------
# 主机管理
# ---------------------------------------------------------------------------------

import os
import sys
import time

import jh
sys.path.append(os.getcwd() + "/class/plugin")
sys.path.append(os.getcwd() + "/class/es/mapper")
sys.path.append(os.getcwd() + "/class/es/query")
sys.path.append(os.getcwd() + "/class/es/service")
import value_tool as value_utils
import host_status_mapper as host_status_mapper_utils
import host_query as host_query_utils
import host_status_service as host_status_service_utils
import json
import traceback
from jinja2 import Environment, FileSystemLoader

from flask import Flask, request

app = Flask(__name__)

class host_api:
    
    host_meta_field = 'id,host_id,host_name,host_group_id,host_group_name,ip,os,remark,ssh_port,ssh_user,ssh_pkey,is_jhpanel,is_pve,is_master,backup_host_id,backup_host_name,backup_ip,addtime'
    host_field = 'id,host_id,host_name,host_group_id,host_group_name,ip,os,remark,ssh_port,ssh_user,ssh_pkey,is_jhpanel,is_pve,is_master,backup_host_id,backup_host_name,backup_ip,addtime,host_status,host_info,cpu_info,mem_info,disk_info,net_info,load_avg,firewall_info,port_info,backup_info,temperature_info,ssh_user_list,detail_addtime'
    host_detail_field = 'id,host_id,host_name,host_status,uptime,host_info,cpu_info,mem_info,disk_info,net_info,load_avg,firewall_info,port_info,backup_info,temperature_info,ssh_user_list,last_update,addtime'
    host_alarm_field = "id,host_id,host_name,alarm_type,alarm_level,alarm_content,addtime"
    host_status_indexes = host_query_utils.HOST_STATUS_INDEXES

    def normalizeHostReportData(self, report_raw):
        if report_raw is None:
            return None
        if isinstance(report_raw, dict):
            return report_raw
        if isinstance(report_raw, str):
            try:
                return json.loads(report_raw)
            except Exception:
                return report_raw
        return report_raw

    def _buildHostReportEmptyHtml(self, host_row):
        host_name = host_row.get('host_name', '')
        host_ip = host_row.get('ip', '')
        title = "主机报告通知 - {0}({1})".format(host_name, host_ip)
        return (
            '<div class="panel_report bgw p-5">'
            '<div class="title c6 f16 plr15">'
            '<h3 class="c6 f16 pull-left">{0}</h3>'
            '</div>'
            '<div class="mx-auto leading-10 plr15">'
            '<div class="text-center mt-5">暂无报告内容</div>'
            '</div>'
            '</div>'
        ).format(title)

    def renderHostReportHtml(self, host_row, report_data):
        if not isinstance(report_data, dict):
            return self._buildHostReportEmptyHtml(host_row)
        if not report_data.get('title'):
            return self._buildHostReportEmptyHtml(host_row)

        if not hasattr(self, '_host_report_env'):
            template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'route', 'templates', 'report'))
            self._host_report_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=False
            )
        env = self._host_report_env
        template_name = 'host_panel_report.html'
        template_data = {
            'title': report_data.get('title', ''),
            'ip': report_data.get('ip', ''),
            'report_time': report_data.get('report_time_text', report_data.get('report_time', '')),
            'start_date': report_data.get('start_date', ''),
            'end_date': report_data.get('end_date', ''),
            'start_time': report_data.get('start_time_text', report_data.get('start_time', '')),
            'end_time': report_data.get('end_time_text', report_data.get('end_time', '')),
            'summary_tips': report_data.get('summary_tips') or [],
            'sysinfo_tips': report_data.get('sysinfo_tips') or [],
            'backup_tips': report_data.get('backup_tips') or [],
            'siteinfo_tips': report_data.get('siteinfo_tips') or [],
            'jianghujsinfo_tips': report_data.get('jianghujsinfo_tips') or [],
            'dockerinfo_tips': report_data.get('dockerinfo_tips') or [],
            'mysqlinfo_tips': report_data.get('mysqlinfo_tips') or []
        }

        try:
            template = env.get_template(template_name)
            html = template.render(**template_data)
        except Exception:
            html = ''
        if not html:
            return self._buildHostReportEmptyHtml(host_row)
        return html

    def renderPVEReportHtml(self, host_row, report_data):
        if not isinstance(report_data, dict):
            return self._buildHostReportEmptyHtml(host_row)
        if not report_data.get('title'):
            return self._buildHostReportEmptyHtml(host_row)

        if not hasattr(self, '_host_report_env'):
            template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'route', 'templates', 'report'))
            self._host_report_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=False
            )
        env = self._host_report_env
        template_name = 'host_pve_report.html'
        template_data = {
            'title': report_data.get('title', ''),
            'ip': report_data.get('ip', ''),
            'report_time': report_data.get('report_time_text', report_data.get('report_time', '')),
            'start_date': report_data.get('start_date', ''),
            'end_date': report_data.get('end_date', ''),
            'start_time': report_data.get('start_time_text', report_data.get('start_time', '')),
            'end_time': report_data.get('end_time_text', report_data.get('end_time', '')),
            'summary_tips': report_data.get('summary_tips') or [],
            'error_tips': report_data.get('error_tips') or [],
            'sysinfo_tips': report_data.get('sysinfo_tips') or [],
            'network_tips': report_data.get('network_tips') or [],
            'smart_tips': report_data.get('smart_tips') or [],
            'io_tips': report_data.get('io_tips') or [],
            'sensor_tips': report_data.get('sensor_tips') or [],
            'power_tips': report_data.get('power_tips') or []
        }

        try:
            template = env.get_template(template_name)
            html = template.render(**template_data)
        except Exception:
            html = ''
        if not html:
            return self._buildHostReportEmptyHtml(host_row)
        return html

    def buildHostReportMessage(self, host_row, report_data):
        is_pve = value_utils.safeBool(host_row.get('is_pve'))
        if is_pve:
            return self.renderPVEReportHtml(host_row, report_data)
        return self.renderHostReportHtml(host_row, report_data)

    def getHostMetaRows(self, host_group_id=''):
        hostM = jh.M('host')
        if host_group_id != '' and host_group_id != '-1':
            hostM.where('host_group_id=?', (host_group_id,))
        data = hostM.field(self.host_meta_field).order('id desc').select()
        if isinstance(data, str) or data is None:
            return []
        return data

    def mergeHostRowWithDetail(self, host_row, host_detail):
        detail = host_detail or host_status_mapper_utils.buildHostDetailFromStatusDoc(host_row, None)
        row = dict(host_row)
        row.update({
            'host_status': detail.get('host_status', 'Stopped'),
            'host_info': detail.get('host_info', '{}'),
            'cpu_info': detail.get('cpu_info', '{}'),
            'mem_info': detail.get('mem_info', '{}'),
            'disk_info': detail.get('disk_info', '[]'),
            'net_info': detail.get('net_info', '{}'),
            'load_avg': detail.get('load_avg', '{}'),
            'firewall_info': detail.get('firewall_info', '{}'),
            'port_info': detail.get('port_info', '{}'),
            'backup_info': detail.get('backup_info', '{}'),
            'temperature_info': detail.get('temperature_info', '{}'),
            'ssh_user_list': detail.get('ssh_user_list', '[]'),
            'detail_addtime': detail.get('addtime', 0),
            'detail_last_update': detail.get('last_update', '')
        })
        return row

    def _formatHistoryRows(self, rows, fields):
        data = []
        for row in rows:
            item = {}
            for field in fields:
                item[field] = row.get(field)
            item['addtime'] = time.strftime('%m/%d %H:%M', time.localtime(float(row.get('addtime', 0) or 0)))
            data.append(item)
        return data

    def listApi(self):
        limit = request.form.get('limit', '100')
        p = request.form.get('p', '1')
        host_group_id = request.form.get('host_group_id', '')
        start = (int(p) - 1) * (int(limit))
        try:
            host_rows = self.getHostMetaRows(host_group_id)
            count = len(host_rows)
            _list = host_rows[start:start + int(limit)]
            host_detail_map = host_status_service_utils.getLatestHostDetailMap(
                _list,
                host_status_indexes=self.host_status_indexes
            )

            host_report_map = host_status_service_utils.getLatestHostReportMap(_list)

            from config_api import config_api
            dispatch_config = config_api().getReportDispatchConfigData()
            report_enabled = bool(dispatch_config.get('enabled'))
            report_host_ids = dispatch_config.get('report_host_ids', []) or []
            report_host_id_set = set(report_host_ids)
            default_report_cron = dispatch_config.get('cron', config_api().getDefaultReportCronData())

            # 循环转换详情数据
            for i in range(len(_list)):
                _list[i] = self.mergeHostRowWithDetail(
                    _list[i], host_detail_map.get(_list[i].get('host_id', ''))
                )
                host_id = _list[i].get('host_id')
                _list[i]['host_report'] = '{}'
                if host_report_map:
                    _list[i]['host_report'] = host_report_map.get(host_id, '{}')
                host_report_enabled = bool(host_id and report_enabled and host_id in report_host_id_set)
                _list[i]['report_notify'] = host_report_enabled
                _list[i]['report_cron'] = dict(default_report_cron)

                _list[i] = self.parseDetailJSONValue(_list[i])

            _ret = {}
            _ret['data'] = _list

            _page = {}
            _page['count'] = count
            _page['tojs'] = 'getWeb'
            _page['p'] = p
            _page['row'] = limit

            _ret['page'] = jh.getPage(_page)
            return jh.getJson(_ret)
        except Exception as e:
            traceback.print_exc()
            return jh.returnJson(False, '获取失败!' + str(e))

    
    def getHostGroupListApi(self):
        data = jh.M("host_group").field("id,host_group_id,host_group_name").order("id asc").select()
        data.insert(0, {"id": 0, "host_group_id": "default", "host_group_name": "默认分组"})
        return jh.getJson(data)

    
    def addHostGroupApi(self):
        host_group_name = request.form.get('host_group_name', '').strip()
        if not host_group_name:
            return jh.returnJson(False, "分组名称不能为空")
        if len(host_group_name) > 18:
            return jh.returnJson(False, "分组名称长度不能超过6个汉字或18位字母")
        if jh.M('host_group').where('host_group_name=?', (host_group_name,)).count() > 0:
            return jh.returnJson(False, "指定分组名称已存在!")
        host_group_id = 'HG' + '_' + jh.getRandomString(4)
        jh.M('host_group').add("host_group_id,host_group_name", (host_group_id,host_group_name,))
        return jh.returnJson(True, '添加成功!')

    def removeHostGroupApi(self):
        id = request.form.get('id', '')
        if jh.M('host_group').where('id=?', (id,)).count() == 0:
            return jh.returnJson(False, "指定分组不存在!")
        # 查询host_group_id
        host_group_id = jh.M('host_group').where('id=?', (id,)).getField('host_group_id')
        jh.M('host_group').where('id=?', (id,)).delete()
        jh.M("host").where("host_group_id=?", (host_group_id,)).save("host_group_id", ('default',))
        return jh.returnJson(True, "分组已删除!")

    def modifyHostGroupNameApi(self):
        # 修改主机分组名称
        host_group_name = request.form.get('host_group_name', '').strip()
        mid = request.form.get('id', '')
        if not host_group_name:
            return jh.returnJson(False, "分组名称不能为空")
        if len(host_group_name) > 18:
            return jh.returnJson(False, "分组名称长度不能超过6个汉字或18位字母")
        if jh.M('host_group').where('id=?', (mid,)).count() == 0:
            return jh.returnJson(False, "指定分组不存在!")
        jh.M('host_group').where('id=?', (mid,)).setField('host_group_name', host_group_name)
        return jh.returnJson(True, "修改成功!")

    def addApi(self):
        host_name = request.form.get('host_name', '10')
        ip = request.form.get('ip', '')
        with open('/etc/ansible/hosts', 'a') as f:
            f.write(f"{ip}\n")

        jh.M('host').add("host_name,ip,addtime", (host_name, ip, time.strftime('%Y-%m-%d %H:%M:%S')))
        try:
            host_id = jh.M('host').where('ip=?', (ip,)).order('id desc').getField('host_id')
            if host_id:
                from config_api import config_api
                config_api().applyReportScheduleForNewHost(host_id)
        except Exception:
            pass
        return jh.returnJson(True, '主机添加成功!')

    def updateHostNameApi(self):
        host_id = request.form.get('host_id', '')
        host_name = request.form.get('host_name', '')
        
        jh.M('host').where('host_id=?', (host_id,)).setField('host_name', host_name)
        return jh.returnJson(True, '主机名称修改成功!')

    def changeHostGroupApi(self):
        host_id = request.form.get('host_id', '')
        host_group_id = request.form.get('host_group_id', '')

        if host_group_id == 'default':
            host_group_name = ''
        else:
            host_group_name = jh.M('host_group').where('host_group_id=?', (host_group_id,)).getField('host_group_name')
            if not host_group_name:
                return jh.returnJson(False, '指定分组不存在!')
        
        jh.M('host').where('host_id=?', (host_id,)).setField('host_group_id', host_group_id)
        jh.M('host').where('host_id=?', (host_id,)).setField('host_group_name', host_group_name)
        return jh.returnJson(True, '主机分组修改成功!')

    def deleteApi(self):
        host_id = request.form.get('host_id', '')
        jh.M('host').where('host_id=?', (host_id,)).delete()
        return jh.returnJson(True, '主机删除成功!')

    def detailApi(self):
        host_id = request.form.get('host_id', '')
        host_rows = jh.M('host').where('host_id=?', (host_id,)).field(self.host_meta_field).select()
        if host_rows:
            host_detail_map = host_status_service_utils.getLatestHostDetailMap(
                host_rows,
                host_status_indexes=self.host_status_indexes
            )
            host_detail = self.mergeHostRowWithDetail(host_rows[0], host_detail_map.get(host_id))
            host_report_map = host_status_service_utils.getLatestHostReportMap(host_rows)
            host_detail['host_report'] = '{}'
            if host_report_map:
                host_detail['host_report'] = host_report_map.get(host_id, '{}')
            host_detail = self.parseDetailJSONValue(host_detail)
            from config_api import config_api
            dispatch_config = config_api().getReportDispatchConfigData()
            report_enabled = bool(dispatch_config.get('enabled'))
            report_host_ids = dispatch_config.get('report_host_ids', []) or []
            default_report_cron = dispatch_config.get('cron', config_api().getDefaultReportCronData())
            host_detail['report_notify'] = bool(host_id and report_enabled and host_id in report_host_ids)
            host_detail['report_cron'] = dict(default_report_cron)
            return jh.returnJson(True, 'ok',  host_detail)
        return jh.returnJson(False, '获取为空', {})

    def getHostReportTemplateApi(self):
        report_type = request.form.get('report_type', '').strip().lower()
        if not report_type:
            report_type = request.args.get('report_type', '').strip().lower()
        if report_type not in ('panel', 'pve'):
            report_type = 'panel'
        if not hasattr(self, '_host_report_env'):
            template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'route', 'templates', 'report'))
            self._host_report_env = Environment(
                loader=FileSystemLoader(template_dir),
                autoescape=False
            )
        env = self._host_report_env
        template_name = 'host_pve_report.html' if report_type == 'pve' else 'host_panel_report.html'
        try:
            template_source = env.loader.get_source(env, template_name)[0]
        except Exception:
            return jh.returnJson(False, '模板不存在', {'template': ''})
        return jh.returnJson(True, 'ok', {'template': template_source})
    
    def getLogPathListApi(self):
        host_ip = request.form.get('host_ip', '')
        path_list = self.getLogPathListFromES(host_ip)
        return jh.getJson(path_list)

    def getLogDetailApi(self):
        host_ip = request.form.get('host_ip', '')
        log_path = request.form.get('log_path', '')
        log_detail = self.getLogDetailFromES(host_ip, log_path)
        return jh.getJson(log_detail)

    def getClientInstallShellLanApi(self):
        client_install_shell = f"curl -sSO https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/client/install.sh && bash install.sh install http://{jh.getHostAddr()}:10844"
        server_ip = jh.getHostAddr()
        github_script_url = "https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/client/install.sh"
        gitee_script_url = "https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/client/install.sh"
        command_template = "wget -O /tmp/install.sh %s && bash /tmp/install.sh install http://%s:10844"
        command_template_cn = "wget -O /tmp/install.sh %s && bash /tmp/install.sh install http://%s:10844 cn"
        return jh.returnJson(True, 'ok', {
            'github': command_template % (github_script_url, server_ip),
            'gitee': command_template_cn % (gitee_script_url, server_ip)
        })

    def alarmApi(self):
        host_id = request.form.get('host_id', '')
        host_alarm = jh.M('host_alarm').where('host_id=?', (host_id,)).field(self.host_alarm_field).select()
        if host_alarm:
            return jh.returnJson(True, 'ok',  host_alarm)
        return jh.returnJson(False, '获取为空', {})

    def parseDetailJSONValue(self, host_detail):
        try:
            # 转成json
            host_detail['host_info'] = json.loads(host_detail['host_info']) if host_detail.get('host_info') is not None else {}
            host_detail['cpu_info'] = json.loads(host_detail['cpu_info']) if host_detail.get('cpu_info') is not None else {}
            host_detail['mem_info'] = json.loads(host_detail['mem_info']) if host_detail.get('mem_info') is not None else {}
            host_detail['disk_info'] = json.loads(host_detail['disk_info']) if host_detail.get('disk_info') is not None else []
            host_detail['net_info'] = json.loads(host_detail['net_info']) if host_detail.get('net_info') is not None else {}
            host_detail['load_avg'] = json.loads(host_detail['load_avg']) if host_detail.get('load_avg') is not None else {}
            host_detail['firewall_info'] = json.loads(host_detail['firewall_info']) if host_detail.get('firewall_info') is not None else {}
            host_detail['port_info'] = json.loads(host_detail['port_info']) if host_detail.get('port_info') is not None else {}
            host_detail['backup_info'] = json.loads(host_detail['backup_info']) if host_detail.get('backup_info') is not None else {}
            host_detail['temperature_info'] = json.loads(host_detail['temperature_info']) if host_detail.get('temperature_info') is not None else {}    
            host_detail['host_report'] = self.normalizeHostReportData(host_detail.get('host_report')) or {}
        except Exception as e:
            traceback.print_exc()
        return host_detail

    def getAllHostChartApi(self):
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        print(start, end)
        data = self.getAllHostChartData(start, end)
        
        return jh.getJson(data)

    def getHostLoadAverageApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostLoadAverageData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostCpuIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostCpuIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostMemIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostMemIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostDiskIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostDiskIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))

    def getHostNetworkIoApi(self):
        host_id = request.form.get('host_id', '')
        start = request.form.get('start', '')
        end = request.form.get('end', '')
        data = self.getHostNetWorkIoData(host_id, start, end)
        return jh.getJson(self.lessenData(data))
    
    def getAllHostChartData(self, start, end):
        # 取所有主机的数据
        data = host_status_service_utils.getHostStatusHistory(
            '',
            start,
            end,
            host_status_indexes=self.host_status_indexes
        )
        data = self._formatHistoryRows(data, ['id', 'host_id', 'host_name', 'cpu_info', 'mem_info', 'disk_info', 'net_info', 'load_avg'])
        
        # 按host_id分组
        host_data = {}
        for value in data:
            if value['host_id'] not in host_data:
                host_data[value['host_id']] = []
            host_data[value['host_id']].append(value)
        # 防止线过于密集，每个host_id最多只取平均分布的100条
        for key in host_data:
            host_data[key] = self.lessenData(host_data[key])
        
        return host_data


    def getHostNetWorkIoData(self, host_id, start, end):
        # 取指定时间段的网络Io
        data = host_status_service_utils.getHostStatusHistory(
            host_id,
            start,
            end,
            host_status_indexes=self.host_status_indexes
        )
        return self._formatHistoryRows(data, ['id', 'net_info'])

    def getHostDiskIoData(self, host_id, start, end):
        # 取指定时间段的磁盘Io
        data = host_status_service_utils.getHostStatusHistory(
            host_id,
            start,
            end,
            host_status_indexes=self.host_status_indexes
        )
        return self._formatHistoryRows(data, ['id', 'disk_info'])

    def getHostCpuIoData(self, host_id, start, end):
        # 取指定时间段的CpuIo
        data = host_status_service_utils.getHostStatusHistory(
            host_id,
            start,
            end,
            host_status_indexes=self.host_status_indexes
        )
        return self._formatHistoryRows(data, ['id', 'cpu_info', 'mem_info'])

    def getHostMemIoData(self, host_id, start, end):
        # 取指定时间段的内存Io
        data = host_status_service_utils.getHostStatusHistory(
            host_id,
            start,
            end,
            host_status_indexes=self.host_status_indexes
        )
        return self._formatHistoryRows(data, ['id', 'mem_info'])

    def getHostLoadAverageData(self, host_id, start, end):
        data = host_status_service_utils.getHostStatusHistory(
            host_id,
            start,
            end,
            host_status_indexes=self.host_status_indexes
        )
        return self._formatHistoryRows(data, ['id', 'load_avg', 'cpu_info'])
    
    # 格式化addtime列
    def toAddtime(self, data, tomem=False):
        import time
        if tomem:
            import psutil
            mPre = (psutil.virtual_memory().total / 1024 / 1024) / 100
        length = len(data)
        he = 1
        if length > 100:
            he = 1
        if length > 1000:
            he = 3
        if length > 10000:
            he = 15
        if he == 1:
            for i in range(length):
                data[i]['addtime'] = time.strftime(
                    '%m/%d %H:%M', time.localtime(float(data[i]['addtime'])))
                if tomem and data[i]['mem'] > 100:
                    data[i]['mem'] = data[i]['mem'] / mPre

            return data
        else:
            count = 0
            tmp = []
            for value in data:
                if count < he:
                    count += 1
                    continue
                value['addtime'] = time.strftime(
                    '%m/%d %H:%M', time.localtime(float(value['addtime'])))
                if tomem and value['mem'] > 100:
                    value['mem'] = value['mem'] / mPre
                tmp.append(value)
                count = 0
            return tmp

    # 防止线过于密集，每个host_id最多只取平均分布的100条
    def lessenData(self, data, count = 100):
        length = len(data)
        if length > count:
            step = int(length / count)
            data = data[::step]
        return data

    # 从ES获取面板报告
    def getLogPathListFromES(self, host_ip):
      try:
        es = jh.getES()
        query = host_query_utils.buildLogPathListSearchBody(host_ip)
        response = es.search(index=host_query_utils.FILEBEAT_INDEXES, body=query)
        path_list = [] 

        for bucket in response["aggregations"]["unique_paths"]["buckets"]:
            path = bucket["key"]
            latest_update = bucket["latest_update"]["hits"]["hits"][0]["_source"]["@timestamp"]
            path_list.append({
                "path": path,
                "lastest_update": latest_update
            })
        
        return path_list
      except Exception as e:
        traceback.print_exc()
        return None
      
    def getLogDetailFromES(self, host_ip, log_file_path):
      try:
        es = jh.getES()
        query = host_query_utils.buildLogDetailSearchBody(host_ip, log_file_path)
        response = es.search(index=host_query_utils.FILEBEAT_INDEXES, body=query)
        log_details = {}
        log_details["log_content"] = []

        if response["hits"]["hits"]:
            # 获取最新的一条日志记录
            latest_log = response["hits"]["hits"][0]["_source"]
            log_details["last_updated"] = jh.convertToLocalTime(latest_log.get("@timestamp"))
            for hit in response["hits"]["hits"]:
                log_details["log_content"].append({
                    "create_time": jh.convertToLocalTime(hit["_source"]["@timestamp"]),
                    "content": hit["_source"]["message"]
                })

        return log_details
      except Exception as e:
        traceback.print_exc()
        return None
