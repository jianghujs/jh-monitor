var monitorTaskList = [];
var currentMonitorTaskSearch = '';

function mtText(value, fallback) {
  var text = normalizeText(value);
  return text === '' ? (fallback || '--') : text;
}

function mtEscape(value) {
  return escapeHTML(mtText(value, ''));
}

function mtAttr(value) {
  return mtEscape(value).replace(/"/g, '&quot;');
}

function mtStatusLabel(type, value) {
  var status = normalizeText(value).toLowerCase();
  var text = status || 'unknown';
  var color = '#999';
  if (type === 'install') {
    if (status === 'installed') {
      text = '已安装';
      color = 'rgb(92, 184, 92)';
    } else if (status === 'failed') {
      text = '失败';
      color = 'red';
    } else if (status === 'pending') {
      text = '待安装';
      color = '#faad14';
    } else {
      text = '未知';
    }
  } else {
    if (status === 'normal') {
      text = '正常';
      color = 'rgb(92, 184, 92)';
    } else if (status === 'warning') {
      text = '提醒';
      color = '#faad14';
    } else if (status === 'error') {
      text = '异常';
      color = 'red';
    } else {
      text = '待分析';
    }
  }
  return '<span class="monitor-task-status" style="color:' + color + '">' + text + '</span>';
}

function getMonitorTaskList(p, search) {
  p = p || 1;
  if (typeof search !== 'undefined') {
    currentMonitorTaskSearch = search || '';
  }
  var loadT = layer.load();
  $.post('/monitor_task/list', {
    p: p,
    limit: 100,
    search: currentMonitorTaskSearch
  }, function(rdata) {
    layer.close(loadT);
    monitorTaskList = (rdata && rdata.data) ? rdata.data : [];
    renderMonitorTaskRows(monitorTaskList);
    $('#monitorTaskPage').html(rdata && rdata.page ? rdata.page : '');
  }, 'json').fail(function() {
    layer.close(loadT);
    layer.msg('获取监控任务失败', {icon: 2});
  });
}

function mtTaskDetailTooltip(item) {
  var lines = [];
  lines.push('任务ID: ' + normalizeText(item.task_id));
  if (normalizeText(item.log_path)) { lines.push('日志路径: ' + normalizeText(item.log_path)); }
  if (normalizeText(item.host_name)) { lines.push('主机: ' + normalizeText(item.host_name)); }
  if (normalizeText(item.host_ip)) { lines.push('IP: ' + normalizeText(item.host_ip)); }
  lines.push('检查频率: ' + mtIntervalLabel(mtIntervalFromTask(item)));
  var grace = toNumber(item.grace_seconds, 0);
  if (grace > 0) { lines.push('宽限: ' + grace + '秒'); }
  if (normalizeText(item.install_status)) { lines.push('安装状态: ' + normalizeText(item.install_status)); }
  var runAt = mtFormatTime(item.last_run_at);
  if (runAt) { lines.push('最后日志: ' + runAt); }
  var eventAt = mtFormatTime(item.last_event_at);
  if (eventAt) { lines.push('日志写入: ' + eventAt); }
  return lines.join('\n');
}
function mtFormatDate(d) {
  if (!d || isNaN(d.getTime())) return '';
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
}
function mtFormatTime(value) {
  var text = normalizeText(value);
  if (!text) return '';
  if (/^\d+(\.\d+)?$/.test(text)) {
    var ts = parseInt(text, 10);
    if (ts > 100000000000) ts = Math.floor(ts / 1000);
    if (ts > 0) return mtFormatDate(new Date(ts * 1000));
  }
  var match = text.match(/^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}:\d{2})/);
  if (match) return match[1] + ' ' + match[2];
  return text;
}

function renderMonitorTaskRows(rows) {
  var body = '';
  if (!rows || rows.length === 0) {
    $('#monitorTaskBody').html('<tr><td colspan="5" class="text-center c7">暂无监控任务</td></tr>');
    return;
  }
  rows.forEach(function(item) {
    var enabled = toNumber(item.enabled, 0) === 1;
    var statusText = mtStatusLabel('analysis', item.last_status);
    var msg = mtEscape(item.last_msg || item.install_msg || '');
    var runAt = mtFormatTime(item.last_run_at);
    if (msg) statusText += '<div class="monitor-task-sub" title="' + mtAttr(item.last_msg || item.install_msg || '') + '">' + msg + '</div>';
    if (runAt) statusText += '<div class="monitor-task-sub">日志时间: ' + mtEscape(runAt) + '</div>';
    var taskId = mtAttr(item.task_id);
    var toggleText = enabled ? '停用' : '启用';
    var opt = '';
    opt += '<a href="javascript:;" class="btlink" onclick="openMonitorTaskEdit(\'' + taskId + '\')">编辑</a>';
    opt += ' | <a href="javascript:;" class="btlink" onclick="showMonitorTaskInstallCommand(\'' + taskId + '\')">复制命令</a>';
    opt += ' | <a href="javascript:;" class="btlink" onclick="refreshMonitorTaskStatus(\'' + taskId + '\',\'' + mtEscape(item.task_name) + '\')" title="查询ES最新日志并刷新任务状态">刷新状态</a>';
    opt += ' | <a href="javascript:;" class="btlink" onclick="setMonitorTaskEnabled(\'' + taskId + '\',' + (enabled ? 0 : 1) + ')">' + toggleText + '</a>';
    opt += ' | <a href="javascript:;" class="btlink" onclick="deleteMonitorTask(\'' + taskId + '\')">删除</a>';
    body += '<tr>' +
      '<td><div class="monitor-task-main monitor-task-detail" data-detail="' + mtAttr(mtTaskDetailTooltip(item)) + '">' + mtEscape(item.task_name) + '</div><div class="monitor-task-sub">' + mtEscape(item.task_id) + '</div></td>' +
      '<td class="text-center">' + mtEscape(mtIntervalLabel(mtIntervalFromTask(item))) + '</td>' +
      '<td class="text-center">' + mtStatusLabel('install', item.install_status) + '</td>' +
      '<td class="text-center">' + statusText + '</td>' +
      '<td class="text-right" style="color:#bbb">' + opt + '</td>' +
      '</tr>';
  });
  $('#monitorTaskBody').html(body);
}

function mtIntervalFromTask(task) {
  task = task || {};
  return {
    value: toNumber(task.interval_value, 1),
    unit: normalizeText(task.interval_unit) || 'day'
  };
}

function mtIntervalLabel(interval) {
  var labels = { day: '天', hour: '小时', minute: '分钟' };
  return toNumber(interval.value, 1) + (labels[interval.unit] || '天');
}

function mtIntervalUnitOptions(selectedUnit) {
  var units = [['day', '天'], ['hour', '小时'], ['minute', '分钟']];
  var html = '';
  units.forEach(function(item) {
    var selected = item[0] === selectedUnit ? ' selected' : '';
    html += '<option value="' + item[0] + '"' + selected + '>' + item[1] + '</option>';
  });
  return html;
}

function buildMonitorTaskForm(task) {
  task = task || {};
  var interval = mtIntervalFromTask(task);
  return '<form id="monitorTaskForm" class="pd15">' +
    '<input type="hidden" name="task_id" value="' + mtAttr(task.task_id || '') + '">' +
    '<div class="line mtb10"><span class="tname">监控项名称</span><input name="task_name" class="bt-input-text" style="width:330px" value="' + mtAttr(task.task_name || '') + '" placeholder="主备 NAS 同步"></div>' +
    '<div class="line mtb10"><span class="tname">检查频率</span><input name="interval_value" type="number" min="1" class="bt-input-text" style="width:80px" value="' + mtAttr(interval.value) + '"><select name="interval_unit" class="bt-input-text ml-2" style="width:90px">' + mtIntervalUnitOptions(interval.unit) + '</select></div>' +
    '<div class="line mtb10"><span class="tname">启用状态</span><select name="enabled" class="bt-input-text" style="width:120px"><option value="1"' + (toNumber(task.enabled, 1) === 1 ? ' selected' : '') + '>启用</option><option value="0"' + (toNumber(task.enabled, 1) === 0 ? ' selected' : '') + '>停用</option></select></div>' +
    '</form>';
}

function buildMonitorTaskSubmitData(formSelector) {
  var data = {};
  $(formSelector).serializeArray().forEach(function(item) {
    data[item.name] = item.value;
  });
  return data;
}

function findMonitorTask(taskId) {
  for (var i = 0; i < monitorTaskList.length; i++) {
    if (monitorTaskList[i].task_id === taskId) {
      return monitorTaskList[i];
    }
  }
  return null;
}

function openMonitorTaskAdd() {
  layer.open({
    type: 1,
    title: '添加监控任务',
    area: ['520px', '300px'],
    content: buildMonitorTaskForm({enabled: 1, interval_value: 1, interval_unit: 'day'}),
    btn: ['保存', '取消'],
    yes: function(index) {
      $.post('/monitor_task/add', buildMonitorTaskSubmitData('#monitorTaskForm'), function(rdata) {
        layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
        if (rdata.status) {
          layer.close(index);
          getMonitorTaskList(1, currentMonitorTaskSearch);
        }
      }, 'json');
    }
  });
}

function openMonitorTaskEdit(taskId) {
  var task = findMonitorTask(taskId);
  if (!task) {
    layer.msg('任务不存在', {icon: 2});
    return;
  }
  layer.open({
    type: 1,
    title: '编辑监控任务',
    area: ['520px', '300px'],
    content: buildMonitorTaskForm(task),
    btn: ['保存', '取消'],
    yes: function(index) {
      $.post('/monitor_task/edit', buildMonitorTaskSubmitData('#monitorTaskForm'), function(rdata) {
        layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
        if (rdata.status) {
          layer.close(index);
          getMonitorTaskList(1, currentMonitorTaskSearch);
        }
      }, 'json');
    }
  });
}

function setMonitorTaskEnabled(taskId, enabled) {
  $.post('/monitor_task/set_enabled', {task_id: taskId, enabled: enabled}, function(rdata) {
    layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
    if (rdata.status) {
      getMonitorTaskList(1, currentMonitorTaskSearch);
    }
  }, 'json');
}

function deleteMonitorTask(taskId) {
  layer.confirm('确认删除该监控任务？删除后不会再参与日报分析。', {icon: 3, title: '删除监控任务'}, function(index) {
    $.post('/monitor_task/delete', {task_id: taskId}, function(rdata) {
      layer.msg(rdata.msg, {icon: rdata.status ? 1 : 2});
      if (rdata.status) {
        layer.close(index);
        getMonitorTaskList(1, currentMonitorTaskSearch);
      }
    }, 'json');
  });
}

function showMonitorTaskInstallCommand(taskId) {
  $.post('/monitor_task/get_install_command', {task_id: taskId}, function(rdata) {
    if (!rdata.status) {
      layer.msg(rdata.msg, {icon: 2});
      return;
    }
    var command = rdata.data && rdata.data.command ? rdata.data.command : '';
    var logCommand = rdata.data && rdata.data.log_command ? rdata.data.log_command : '';
    var html = '<div class="pd15">' +
      '<div class="monitor-task-section-title">1. 安装命令（在被监控主机执行一次）</div>' +
      '<textarea id="monitorTaskInstallCommand" class="bt-input-text monitor-task-command-text" readonly>' + mtEscape(command) + '</textarea>' +
      '<div class="c7 mtb10">在被监控主机上执行该命令，自动完成任务注册、日志命令安装和 filebeat 采集配置。安装完成后任务会在下一次日报生成时更新最新分析状态。</div>' +
      '<div class="monitor-task-section-title mtb10">2. 写入日志命令（放到你的业务脚本里）</div>' +
      '<textarea id="monitorTaskLogCommand" class="bt-input-text monitor-task-command-text" readonly>' + mtEscape(logCommand) + '</textarea>' +
      '<div class="c7 mtb10">--status 可选: success(成功) / warning(告警) / error(异常)，--msg 为本次结果摘要，可按需替换。</div>' +
      '</div>';
    layer.open({
      type: 1,
      title: '监控任务命令',
      area: ['720px', '580px'],
      content: html,
      btn: ['复制安装命令', '复制写入日志命令', '关闭'],
      btn1: function() {
        copyText(command);
      },
      btn2: function() {
        copyText(logCommand);
      }
    });
  }, 'json');
}

function refreshMonitorTaskStatus(taskId, taskName) {
  var loadT = layer.msg('正在刷新任务状态: ' + (taskName || taskId) + '...', {icon:16,time:0,shade:[0.3, '#000']});
  $.post('/monitor_task/refreshTaskStatus', {task_id: taskId}, function(rdata) {
    layer.close(loadT);
    showMsg(rdata.msg || '刷新完成', function() {
      getMonitorTaskList(1, currentMonitorTaskSearch);
    }, {icon: rdata.status ? 1 : 2}, 2500);
  }, 'json').fail(function() {
    layer.close(loadT);
    layer.msg('刷新任务状态失败', {icon:2});
  });
}
