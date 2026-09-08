var haLocalPairs = [];
var haLocalLogTimer = null;
var haLocalRefreshTimer = null;
var haLocalRefreshInterval = 60000;

function haLocalApi(path, data, callback, method) {
  $.ajax({url: '/ha/api/local/' + path, type: method || 'POST', data: data || {}, dataType: 'json'}).done(function(res) {
    if (!res || !res.status) { layer.msg((res && res.msg) || '请求失败', {icon: 2}); callback(null, res || {}); return; }
    callback(res.data || {}, res);
  }).fail(function() { layer.msg('接口连接失败', {icon: 2}); callback(null, {status: false}); });
}

function haLocalEscape(value) { return String(value == null ? '' : value).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
function haLocalStatusClass(status) { return 'ha-local-' + ({normal:'normal',warning:'warning',danger:'danger',switching:'switching'}[status] || 'unknown'); }
function haLocalStatusText(status) { return ({normal:'正常',warning:'提醒',danger:'异常',switching:'切换中',unknown:'待上报'}[status] || '待上报'); }
function haLocalRole(role) { return role === 'master' ? '主机' : role === 'standby' ? '备机' : '--'; }
function haLocalRoleTag(role) { return role === 'master' ? '<span class="ha-local-role-tag ha-local-role-master">主</span>' : role === 'standby' ? '<span class="ha-local-role-tag ha-local-role-standby">备</span>' : '--'; }
function haLocalOnlineTag(status) { return status === 'online' ? '<span class="ha-local-online-tag ha-local-online">在线</span>' : status === 'offline' ? '<span class="ha-local-online-tag ha-local-offline">离线</span>' : '<span class="ha-local-online-tag ha-local-online-unknown">待上报</span>'; }
function haLocalHealth(status) { return ({normal:'正常',warning:'提醒',danger:'异常'}[status] || '--'); }
function haLocalHealthTag(status) { return status === 'normal' ? '<span class="ha-local-status ha-local-normal">正常</span>' : status === 'warning' ? '<span class="ha-local-status ha-local-warning">提醒</span>' : status === 'danger' ? '<span class="ha-local-status ha-local-danger">异常</span>' : '<span class="ha-local-status ha-local-unknown">待上报</span>'; }
function haLocalTaskStatusTag(status) { return status === 'running' || status === 'pending' ? '<span class="ha-local-status ha-local-switching">' + (status === 'running' ? '进行中' : '等待中') + '</span>' : status === 'success' ? '<span class="ha-local-status ha-local-normal">成功</span>' : status === 'failed' ? '<span class="ha-local-status ha-local-danger">失败</span>' : status === 'recovered' ? '<span class="ha-local-status ha-local-warning">已恢复</span>' : '<span class="ha-local-status ha-local-unknown">--</span>'; }

function haLocalLoadPairs() {
  haLocalApi('list', {}, function(data) {
    haLocalPairs = (data && data.list) || [];
    var rows = haLocalPairs.map(function(pair) {
      var host = pair.host || {};
      return '<tr><td><div class="ha-local-main">' + haLocalEscape(pair.pair_name || '--') + '</div><div class="ha-local-subtext ha-local-pair-id-line"><span class="ha-local-pair-id-text" title="' + haLocalEscape(pair.pair_id) + '">' + haLocalEscape(pair.pair_id) + '</span><button type="button" class="ha-local-copy-btn" title="复制主备关系 ID" onclick="haLocalCopyPairId(\'' + haLocalEscape(pair.pair_id) + '\')"><i class="glyphicon glyphicon-duplicate"></i></button></div></td>' +
        '<td><div class="ha-local-main">' + haLocalEscape(host.host_name || '--') + '</div><div class="ha-local-host-sub"><span class="ha-local-subtext">' + haLocalEscape(host.host_ip || host.host_id || '等待注册') + '</span>' + haLocalOnlineTag(host.online_status) + '</div></td>' +
        '<td>' + haLocalRoleTag(host.role) + '</td>' +
        '<td><span class="ha-local-status ' + haLocalStatusClass(pair.status) + '">' + haLocalStatusText(pair.status) + '</span><div class="ha-local-subtext" title="' + haLocalEscape(pair.status_text) + '">' + haLocalEscape(pair.status_text || '--') + '</div></td>' +
        '<td>' + haLocalEscape(pair.last_report_at || '--') + '</td><td class="text-right ha-local-actions"><a class="btlink" href="javascript:;" onclick="haLocalOpenDetail(\'' + haLocalEscape(pair.pair_id) + '\')">详情</a><a class="btlink" href="javascript:;" onclick="haLocalDeletePair(\'' + haLocalEscape(pair.pair_id) + '\')">删除</a></td></tr>';
    }).join('');
    $('#haLocalPairBody').html(rows);
    $('#haLocalEmpty').toggle(!haLocalPairs.length); $('#haLocalTableWrap').toggle(!!haLocalPairs.length);
  });
}

function haLocalStartRefresh() {
  if (haLocalRefreshTimer) clearInterval(haLocalRefreshTimer);
  haLocalRefreshTimer = setInterval(function() {
    haLocalLoadPairs();
  }, haLocalRefreshInterval);
  haLocalUpdateRefreshButton(true);
}

function haLocalStopRefresh() {
  if (haLocalRefreshTimer) {
    clearInterval(haLocalRefreshTimer);
    haLocalRefreshTimer = null;
  }
  haLocalUpdateRefreshButton(false);
}

function haLocalUpdateRefreshButton(isRefreshing) {
  var $button = $('#haLocalToggleRefresh');
  if (!$button.length) return;
  if (isRefreshing) {
    $button.html('<span class="glyphicon glyphicon-pause"></span> <span>停止刷新</span>');
    $button.removeClass('btn-success').addClass('btn-default');
  } else {
    $button.html('<span class="glyphicon glyphicon-play"></span> <span>开始刷新</span>');
    $button.removeClass('btn-default').addClass('btn-success');
  }
}

function haLocalSetRefreshInterval(seconds) {
  haLocalRefreshInterval = seconds * 1000;
  $('#haLocalCurrentInterval').text(seconds);
  if (haLocalRefreshTimer) {
    haLocalStopRefresh();
    haLocalStartRefresh();
  }
}

function haLocalToggleRefresh() {
  if (haLocalRefreshTimer) {
    haLocalStopRefresh();
  } else {
    haLocalStartRefresh();
  }
}

function haLocalOpenCreate() {
  var html = '<div class="bt-form ha-local-dialog pd20"><div class="line"><span class="tname">关系名称</span><div class="info-r"><input id="haLocalPairName" class="bt-input-text" placeholder="例如：生产环境主备" style="width:300px"></div></div><div class="line"><span class="tname"></span><div class="info-r c9">添加后，将生成的主备关系 ID 填入本地版插件的云监控配置。</div></div></div>';
  layer.open({type: 1, title: '添加主备关系', area: '500px', content: html, btn: ['添加', '取消'], yes: function(index) {
    haLocalApi('pair/create', {pair_name: $('#haLocalPairName').val()}, function(data) {
      if (!data) return;
      layer.close(index); haLocalShowPairId(data); haLocalLoadPairs();
    });
  }});
}

function haLocalShowPairId(data) {
  var html = '<div class="pd20"><div class="ha-local-pair-id">' + haLocalEscape(data.pair_id) + '</div><div class="c9 mt10">请将此 ID 填入本地版插件的云监控配置。</div></div>';
  layer.open({type: 1, title: '主备关系 ID', area: '560px', content: html, btn: ['已填写']});
}

function haLocalCopyPairId(pairId) {
  var input = document.createElement('textarea');
  input.value = pairId;
  input.setAttribute('readonly', 'readonly');
  input.style.position = 'fixed';
  input.style.opacity = '0';
  document.body.appendChild(input);
  input.select();
  try {
    document.execCommand('copy');
    layer.msg('主备关系 ID 已复制', {icon: 1});
  } catch (e) {
    layer.msg('复制失败，请手动复制', {icon: 2});
  }
  document.body.removeChild(input);
}

function haLocalDeletePair(pairId) {
  layer.confirm('删除后将清除该主备关系的机器状态、切换任务和日志，确定删除？', {title: '删除主备关系', icon: 0}, function(index) {
    haLocalApi('pair/delete', {pair_id: pairId}, function(data) {
      if (!data) return;
      layer.close(index); layer.msg('主备关系已删除', {icon: 1}); haLocalLoadPairs();
    });
  });
}

function haLocalOpenDetail(pairId) {
  haLocalApi('detail', {pair_id: pairId}, function(pair) {
    if (!pair) return;
    var host = pair.host || {}; var tasks = pair.tasks || [];
    var taskRows = tasks.map(function(task) { return '<tr><td>' + haLocalEscape(task.switch_task_id) + '</td><td>' + haLocalRoleTag(task.target_role) + '</td><td>' + haLocalTaskStatusTag(task.status) + '</td><td>' + haLocalEscape(task.current_step || task.status_text || '--') + '</td><td class="text-right"><a class="btlink" href="javascript:;" onclick="haLocalOpenLog(\'' + haLocalEscape(task.switch_task_id) + '\')">查看日志</a></td></tr>'; }).join('') || '<tr><td colspan="5" class="c9">暂无切换任务</td></tr>';
    var html = '<div class="pd20"><table class="table table-hover ha-local-detail-table"><tbody><tr><th>主备关系 ID</th><td>' + haLocalEscape(pair.pair_id) + '</td></tr><tr><th>关系名称</th><td>' + haLocalEscape(pair.pair_name || '--') + '</td></tr><tr><th>关系状态</th><td><span class="ha-local-status ' + haLocalStatusClass(pair.status) + '">' + haLocalStatusText(pair.status) + '</span><span class="ha-local-detail-text">' + haLocalEscape(pair.status_text || '--') + '</span></td></tr><tr><th>当前机器</th><td>' + haLocalEscape(host.host_name || '--') + '<span class="ha-local-detail-text">' + haLocalEscape(host.host_ip || host.host_id || '--') + '</span>' + haLocalOnlineTag(host.online_status) + '</td></tr><tr><th>角色与自检</th><td>' + haLocalRoleTag(host.role) + haLocalHealthTag(host.health_status) + '</td></tr><tr><th>最近上报</th><td>' + haLocalEscape(pair.last_report_at || '--') + '</td></tr></tbody></table><table class="table table-hover"><thead><tr><th>任务</th><th>目标</th><th>状态</th><th>当前步骤</th><th></th></tr></thead><tbody>' + taskRows + '</tbody></table></div>';
    layer.open({type: 1, title: '主备关系详情 - ' + haLocalEscape(pair.pair_id), area: ['900px', '650px'], content: html});
  });
}

function haLocalOpenLog(taskId) {
  if (haLocalLogTimer) { clearInterval(haLocalLogTimer); haLocalLogTimer = null; }
  var offset = 0; var content = '';
  var index = layer.open({type: 1, title: '切换日志 - ' + haLocalEscape(taskId), area: ['900px', '620px'], content: '<pre id="haLocalTaskLog" class="ha-local-task-log">加载中...</pre>', end: function() { if (haLocalLogTimer) clearInterval(haLocalLogTimer); haLocalLogTimer = null; }});
  function poll() {
    $.ajax({url: '/ha/api/local/switch-log', type: 'GET', data: {switch_task_id: taskId, offset: offset}, dataType: 'json'}).done(function(res) {
      if (!res || !res.status) return;
      var data = res.data || {}; content += data.content || ''; offset = data.next_offset || offset;
      var box = $('#haLocalTaskLog'); if (box.length) { box.text(content || '暂无日志'); box.scrollTop(box[0].scrollHeight); }
    });
  }
  poll(); haLocalLogTimer = setInterval(poll, 2000); return index;
}

$(function() {
  haLocalLoadPairs();
  $('#haLocalCurrentInterval').text(haLocalRefreshInterval / 1000);
  haLocalStartRefresh();
});
