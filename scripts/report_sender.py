# coding: utf-8

import datetime
import random
import time

from report_analyser import (
    HostReportAnalyser,
    OVERVIEW_REPORT_INDEX,
    PAGE_SIZE,
    SINGLE_REPORT_INDEX,
    build_delivery_state,
    normalize_delivery_state,
    jh,
    value_tool,
)


class HostReportSender(HostReportAnalyser):
    def _get_single_delivery_host_ids(self, due_rows, enabled_rows):
        """总览触发后，单机报告检查所有已启用主机，异常主机再单独发送。"""
        target_rows = enabled_rows or due_rows or []
        host_ids = []
        for row in target_rows:
            host_id = row.get('host_id')
            if host_id and host_id not in host_ids:
                host_ids.append(host_id)
        return host_ids

    def _build_single_report_delivery_query(self, host_ids, report_date):
        """兼容历史 mapping，按 host_id + report_date 查询待发送单机报告。"""
        return {
            'query': {
                'bool': {
                    'filter': [
                        {
                            'bool': {
                                'should': [
                                    {'terms': {'host_id.keyword': host_ids}},
                                    {'terms': {'host_id': host_ids}},
                                ],
                                'minimum_should_match': 1
                            }
                        },
                        {'term': {'report_date': report_date}}
                    ]
                }
            }
        }

    def _append_delivery_history(self, doc, status, recipients=None, error_message=''):
        """在 extra_info 中追加最近的发送历史。"""
        recipients = recipients or []
        extra_info = doc.get('extra_info') or {}
        history = extra_info.get('delivery_history') or []
        history.append({
            'status': status,
            'time': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'recipients': recipients,
            'error': error_message
        })
        extra_info['delivery_history'] = history[-20:]
        doc['extra_info'] = extra_info
        return doc

    def _get_email_recipients(self):
        """读取邮件通知配置中的收件人列表。"""
        recipients = []
        try:
            notify_data = jh.getNotifyData(True)
            email_data = notify_data.get('email', {}) if isinstance(notify_data, dict) else {}
            config_data = email_data.get('data', {}) if isinstance(email_data, dict) else {}
            raw_recipients = config_data.get('to_mail_addr', '')
            if isinstance(raw_recipients, list):
                recipients = [item for item in raw_recipients if str(item).strip() != '']
            else:
                for item in str(raw_recipients).replace(';', ',').split(','):
                    item = item.strip()
                    if item != '':
                        recipients.append(item)
        except Exception:
            recipients = []
        return recipients

    def _validate_report_for_delivery(self, document, report_type, report_date):
        """校验报告文档是否满足发送条件。"""
        errors = []
        if not isinstance(document, dict):
            return ['report_not_found']
        if str(document.get('report_date', '')) != str(report_date):
            errors.append('invalid_report_date')
        validation = document.get('validation', {}) or {}
        if report_type != 'single' and not validation.get('is_complete', False):
            errors.append('incomplete_report_document')
        if str(document.get('html_content', '')).strip() == '':
            errors.append('empty_html_content')
        if report_type == 'single' and not document.get('is_abnormal'):
            errors.append('normal_report_not_sent')
        return errors

    def _build_delivery_title(self, document, title_prefix=''):
        """统一拼装带时间的邮件标题。"""
        title = title_prefix or document.get('title', '服务器报告')
        report_time = str(document.get('report_time_text', document.get('report_time', ''))).strip()
        if report_time != '' and report_time not in title:
            return '{0} {1}'.format(title, report_time)
        return title

    def _send_report_document(self, index_name, doc_id, document, title_prefix=''):
        """发送单份报告，并回写发送结果。"""
        recipients = self._get_email_recipients()
        delivery = normalize_delivery_state(document.get('delivery', {}))
        retry_count = value_tool.safeInt(delivery.get('retry_count', 0))
        title = self._build_delivery_title(document, title_prefix)
        self.log_tool.step(
            '[report-delivery] 开始发送报告',
            index=index_name,
            doc_id=doc_id,
            previous_status=delivery.get('status', ''),
            previous_last_sent_time=delivery.get('last_sent_time', ''),
            retry_count=retry_count,
            recipients=recipients,
            title=title,
        )
        try:
            send_ok = jh.notifyMessage(
                msg=document.get('html_content', ''),
                msgtype='html',
                title=title,
                stype='host_report_pipeline_{0}'.format(doc_id),
                trigger_time=0
            )
            if send_ok:
                document['delivery'] = build_delivery_state(
                    status='success',
                    last_sent_time=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    recipients=recipients,
                    retry_count=retry_count,
                    last_error=''
                )
                self._append_delivery_history(document, 'success', recipients, '')
                self._es.index(index_name, doc_id, document=document, refresh='wait_for')
                self.log_tool.detail_ok('[report-delivery] 发送成功', index=index_name, doc_id=doc_id)
                return True, ''
            error_message = 'notify_message_returned_false'
        except Exception as ex:
            error_message = str(ex)

        document['delivery'] = build_delivery_state(
            status='failed',
            last_sent_time=delivery.get('last_sent_time'),
            recipients=recipients,
            retry_count=retry_count + 1,
            last_error=error_message
        )
        self._append_delivery_history(document, 'failed', recipients, error_message)
        self._es.index(index_name, doc_id, document=document, refresh='wait_for')
        self.log_tool.detail_fail('[report-delivery] 发送失败', index=index_name, doc_id=doc_id, error=error_message)
        return False, error_message

    def _mark_report_skipped(self, index_name, doc_id, document, error_message):
        """将不满足发送条件的报告标记为 skipped。"""
        delivery = normalize_delivery_state(document.get('delivery', {}))
        document['delivery'] = build_delivery_state(
            status='skipped',
            last_sent_time=delivery.get('last_sent_time'),
            recipients=delivery.get('recipients', []),
            retry_count=value_tool.safeInt(delivery.get('retry_count', 0)),
            last_error=error_message
        )
        self._append_delivery_history(document, 'skipped', delivery.get('recipients', []), error_message)
        self._es.index(index_name, doc_id, document=document, refresh='wait_for')
        self.log_tool.warn('[report-delivery] 跳过发送', index=index_name, doc_id=doc_id, reason=error_message)

    def run_delivery(self, due_rows=None, report_config=None, report_date=None, enabled_rows=None):
        """执行发送阶段：先发总览，再发异常单机报告。"""
        window = self.get_report_window(report_date)
        if due_rows is None or report_config is None or enabled_rows is None:
            report_config, enabled_rows, due_rows = self.get_schedule_state()
        if len(due_rows) == 0:
            self.log_tool.warn('[report-delivery] 未到发送时间，跳过本轮', report_date=window['report_date'])
            return {'status': 'skipped', 'reason': 'not_due', 'report_date': window['report_date']}
        notify_data = jh.getNotifyData(True)
        email_enabled = False
        if isinstance(notify_data, dict) and 'email' in notify_data and notify_data['email'].get('enable'):
            email_enabled = True
        self.log_tool.start(
            '[report-delivery] 开始执行发送流水线',
            report_date=window['report_date'],
            enabled_rows=len(enabled_rows or []),
            due_rows=len(due_rows),
            due_host_ids=[row.get('host_id') for row in due_rows if row.get('host_id')],
            email_enabled=email_enabled,
        )
        if not email_enabled:
            self.log_tool.fail('[report-delivery] 邮件未配置，发送中止', report_date=window['report_date'])
            return {'status': 'blocked', 'reason': 'email_not_configured', 'report_date': window['report_date']}

        overview_doc_id = window['report_date']
        overview_document = self._es.get(OVERVIEW_REPORT_INDEX, overview_doc_id)
        if isinstance(overview_document, dict):
            overview_document = overview_document.get('_source', {})
        overview_errors = self._validate_report_for_delivery(overview_document, 'overview', window['report_date'])
        self.log_tool.step(
            '[report-delivery] 校验总览报告',
            doc_id=overview_doc_id,
            validation=value_tool.getNested(overview_document, ['validation', 'status'], ''),
            delivery=value_tool.getNested(overview_document, ['delivery', 'status'], ''),
            errors=overview_errors,
        )
        if len(overview_errors) > 0:
            if isinstance(overview_document, dict):
                self._mark_report_skipped(OVERVIEW_REPORT_INDEX, overview_doc_id, overview_document, '；'.join(overview_errors))
            return {'status': 'blocked', 'reason': 'overview_not_ready', 'errors': overview_errors, 'report_date': window['report_date']}

        host_ids = self._get_single_delivery_host_ids(due_rows, enabled_rows)
        single_documents = []
        if len(host_ids) > 0:
            single_documents = self._es.searchAll(
                index=SINGLE_REPORT_INDEX,
                body=self._build_single_report_delivery_query(host_ids, window['report_date']),
                page_size=PAGE_SIZE,
                scroll='1m'
            )
        matched_host_ids = [doc.get('host_id') for doc in single_documents]
        missing_host_ids = [host_id for host_id in host_ids if host_id not in matched_host_ids]
        self.log_tool.detail_ok(
            '[report-delivery] 单机异常报告加载完成',
            report_date=window['report_date'],
            expected_hosts=host_ids,
            matched_docs=len(single_documents),
            matched_host_ids=matched_host_ids,
        )
        if len(missing_host_ids) > 0:
            self.log_tool.warn(
                '[report-delivery] 部分主机缺少单机报告文档',
                report_date=window['report_date'],
                missing_host_ids=missing_host_ids,
            )
        single_success = 0
        single_failed = 0
        single_skipped = 0

        overview_success, overview_error = self._send_report_document(
            OVERVIEW_REPORT_INDEX,
            overview_doc_id,
            overview_document,
            title_prefix=overview_document.get('title', '{0}-全部主机概览报告'.format(jh.getConfig('title')))
        )
        if not overview_success:
            return {
                'status': 'failed',
                'reason': 'overview_send_failed',
                'error': overview_error,
                'report_date': window['report_date']
            }

        # 概览发送成功后等待 5 秒，再开始发送单机异常报告，避免与概览邮件混在一起
        if len(single_documents) > 0:
            self.log_tool.step('[report-delivery] 等待 5 秒后开始发送单机异常报告', report_date=window['report_date'])
            time.sleep(5)

        for index, document in enumerate(single_documents):
            doc_id = '{0}:{1}'.format(window['report_date'], document.get('host_id', ''))
            validation_errors = self._validate_report_for_delivery(document, 'single', window['report_date'])
            if len(validation_errors) > 0:
                self._mark_report_skipped(SINGLE_REPORT_INDEX, doc_id, document, '；'.join(validation_errors))
                single_skipped += 1
                continue

            # 单机报告之间随机间隔 1-2 秒，降低邮件网关压力
            if index > 0:
                sleep_seconds = random.uniform(1, 2)
                self.log_tool.step('[report-delivery] 单机报告发送间隔等待', sleep='{0:.2f}s'.format(sleep_seconds))
                time.sleep(sleep_seconds)

            single_icon = '🔴' if document.get('is_abnormal') else '🟢'
            title = '{0} {1}-{2}({3})-服务器报告 {4}'.format(
                single_icon,
                jh.getConfig('title'),
                document.get('host_name', ''),
                document.get('host_ip', ''),
                window['report_date']
            )
            success, error_message = self._send_report_document(SINGLE_REPORT_INDEX, doc_id, document, title_prefix=title)
            if success:
                single_success += 1
            else:
                single_failed += 1
                self.log_tool.detail_fail('[report-delivery] 单机报告发送失败', doc_id=doc_id, error=error_message)

        all_done = (single_failed == 0 and overview_success)

        if all_done:
            self.log_tool.done(
                '[report-delivery] 发送流水线全部成功',
                report_date=window['report_date'],
                overview_sent=overview_success,
                single_success=single_success,
                single_failed=single_failed,
                single_skipped=single_skipped,
            )
        else:
            self.log_tool.fail(
                '[report-delivery] 发送流水线部分失败',
                report_date=window['report_date'],
                overview_sent=overview_success,
                single_success=single_success,
                single_failed=single_failed,
                single_skipped=single_skipped,
            )
        return {
            'status': 'ok' if all_done else 'partial',
            'report_date': window['report_date'],
            'overview_sent': overview_success,
            'single_success': single_success,
            'single_failed': single_failed,
            'single_skipped': single_skipped,
        }



__all__ = [
    'HostReportSender',
    'HostReportSendPipeline',
]


HostReportSendPipeline = HostReportSender
