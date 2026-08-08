var haPairs = [];
var haCurrentSearch = '';

function haApi(action, data, callback) {
  $.post('/ha/' + action, data || {}, function(res) {
    if (typeof res === 'string') {
      try { res = JSON.parse(res); } catch (e) { res = {status: false, msg: res}; }
    }
    if (!res || !res.status) {
      layer.msg((res && res.msg) || 'HA接口请求失败', {icon: 2});
      if (callback) callback(null, res || {});
      return;
    }
    if (callback) callback(res.data || {}, res);
  }, 'json').fail(function() {
    layer.msg('HA接口连接失败', {icon: 2});
    if (callback) callback(null, {status: false});
  });
}

function haLoadPairs(callback) {
  haApi('get_list', {}, function(data) {
    if (data && $.isArray(data.list)) {
      haPairs = data.list;
    } else {
      haPairs = [];
    }
    haRenderList(haCurrentSearch);
    if (callback) callback();
  });
}

function haText(value, fallback) {
  var text = normalizeText(value);
  return text === '' ? (fallback || '--') : text;
}

function haEscape(value) {
  return escapeHTML(haText(value, ''));
}

function haAttr(value) {
  return haEscape(value).replace(/"/g, '&quot;');
}

function haFindPair(pairId) {
  for (var i = 0; i < haPairs.length; i++) {
    if (haPairs[i].pair_id === pairId) return haPairs[i];
  }
  return null;
}

function haFindHost(pair, hostId) {
  for (var i = 0; i < pair.hosts.length; i++) {
    if (pair.hosts[i].host_id === hostId) return pair.hosts[i];
  }
  return null;
}

function haStatusClass(status) {
  if (status === 'danger') return 'ha-pill-danger';
  if (status === 'warning') return 'ha-pill-warning';
  if (status === 'switching') return 'ha-pill-switching';
  return 'ha-pill-normal';
}

function haStatusLabel(status) {
  if (status === 'danger') return '异常';
  if (status === 'warning') return '提醒';
  if (status === 'switching') return '切换中';
  return '正常';
}

function haStatusWeight(status) {
  return {danger: 0, switching: 1, warning: 2, normal: 3}[status] || 4;
}

var haCheckTemplate = [
  {group: '计划任务', name: '备份数据库', master: '关闭', standby: '开启'},
  {group: '计划任务', name: 'xtrabackup', master: '关闭', standby: '开启'},
  {group: '计划任务', name: 'xtrabackup-inc 全量备份', master: '关闭', standby: '开启'},
  {group: '计划任务', name: 'xtrabackup-inc 增量备份', master: '关闭', standby: '开启'},
  {group: '计划任务', name: '备份网站配置', master: '开启', standby: '关闭'},
  {group: '计划任务', name: '备份插件配置', master: '开启', standby: '关闭'},
  {group: '计划任务', name: 'lsyncd 实时任务定时同步', master: '开启', standby: '关闭'},
  {group: '计划任务', name: "续签 Let's Encrypt 证书", master: '开启', standby: '关闭'},
  {group: '计划任务', name: '恢复网站配置', master: '关闭', standby: '开启'},
  {group: '计划任务', name: '恢复插件配置', master: '关闭', standby: '开启'},
  {group: '监控提醒', name: 'SSL 证书到期预提醒', master: '开启', standby: '关闭'},
  {group: '监控提醒', name: '主从同步异常提醒', master: '开启', standby: '关闭'},
  {group: '监控提醒', name: 'Rsync 状态异常提醒', master: '开启', standby: '关闭'},
  {group: 'SSH 同步', name: 'authorized_keys 同步公钥', master: '已删除', standby: '已添加'},
  {group: 'rsync', name: 'rsyncd 任务', master: '运行中', standby: '已停止'},
  {group: 'rsync', name: 'lsyncd 服务', master: '运行中', standby: '已停止'},
  {group: 'Web 服务', name: 'OpenResty', master: '运行中', standby: '已停止'},
  {group: '数据库', name: 'MySQL 主从状态', master: '无主从配置（作为主）', standby: '作为从库（复制链路正常）'}
];

function haBuildHostChecks(pair, host) {
  var isMaster = host.role === 'master';
  var isOffline = host.online !== 'online';
  var isSwitching = pair.status === 'switching';
  var result = {};
  haCheckTemplate.forEach(function(item) {
    var expected = isMaster ? item.master : item.standby;
    var actual = expected;
    var status = 'pass';
    if (isOffline) {
      actual = '未知（插件离线）';
      status = 'unknown';
    } else if (isSwitching && isMaster && item.group !== '数据库') {
      if (item.name.indexOf('OpenResty') !== -1 || item.name.indexOf('备份数据库') !== -1 || item.name.indexOf('rsyncd') !== -1) {
        actual = item.standby;
        status = 'warning';
      }
    } else if (!isMaster && pair.status === 'warning' && item.name.indexOf('MySQL') !== -1) {
      actual = '复制延迟 38s';
      status = 'warning';
    } else if (isMaster && pair.status === 'warning' && item.name.indexOf('lsyncd') !== -1) {
      actual = 'lsyncd warning';
      status = 'warning';
    }
    result[item.name] = {expected: expected, actual: actual, status: status};
  });
  return result;
}

function haCheckStatusIcon(status) {
  if (status === 'pass') return '<span class="ha-check-icon ha-check-pass" title="正常">✓</span>';
  if (status === 'warning') return '<span class="ha-check-icon ha-check-warn" title="提醒">!</span>';
  if (status === 'unknown') return '<span class="ha-check-icon ha-check-unknown" title="未知">?</span>';
  return '<span class="ha-check-icon ha-check-fail" title="异常">✗</span>';
}

function haDetailChecksHtml(pair) {
  var hostCards = pair.hosts.map(function(host, index) {
    var checks = haBuildHostChecks(pair, host);
    var rows = '';
    var currentGroup = '';
    haCheckTemplate.forEach(function(item) {
      if (item.group !== currentGroup) {
        currentGroup = item.group;
        rows += '<tr class="ha-check-group-row"><td colspan="2">' + haEscape(item.group) + '</td></tr>';
      }
      var check = checks[item.name];
      var matched = check.status === 'pass';
      var actualCls = matched ? 'ha-check-actual-pass' : 'ha-check-actual-fail';
      var statusTitle = '当前状态: ' + check.actual + '\n期望状态: ' + check.expected;
      rows += '<tr>' +
        '<td class="ha-check-name">' + haEscape(item.name) + '</td>' +
        '<td class="ha-check-actual ' + actualCls + '" title="' + haAttr(statusTitle) + '">' + haCheckStatusIcon(matched ? 'pass' : 'fail') + haEscape(check.actual) + '</td>' +
      '</tr>';
    });
    var dot = haHostStatusDot(pair, host);
    var switchState = haHostSwitchState(pair, host);
    var switchingMark = switchState.status === 'running' ? '<span class="ha-switching-state" title="' + haAttr(switchState.step) + '"><span class="ha-loading-icon"></span>切换中</span>' : '';
    var nameCls = host.online === 'online' ? 'ha-host-name' : 'ha-host-name ha-host-name-offline';
    return '<div class="ha-check-host-card">' +
      '<div class="ha-check-host-head">' + dot + haRoleMark(host.role) +
        '<span class="' + nameCls + '">' + haEscape(host.name) + '</span>' +
        (index === 0 ? '<span class="ha-current-site-tag">本机房</span>' : '') + switchingMark +
      '</div>' +
      '<table class="table table-hover ha-check-table"><colgroup><col><col class="ha-check-status-col"></colgroup><thead><tr><th>检查项</th><th class="ha-check-status-head">状态</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '</div>';
  }).join('');
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">自检状态</div>' +
    '<div class="ha-muted mb10">基于上下线脚本的每个步骤，检查每台机器当前角色下的期望状态是否满足。</div>' +
    '<div class="ha-check-grid">' + hostCards + '</div>' +
    '</div>';
}

function haRoleMark(role) {
  var cls = role === 'master' ? 'ha-role-master' : 'ha-role-standby';
  var text = role === 'master' ? '主' : '备';
  return '<span class="ha-role-mark ' + cls + '">' + text + '</span>';
}

function haHostCell(host) {
  var onlineText = host.online === 'online' ? '在线' : '离线';
  var onlineCls = host.online === 'online' ? 'ha-online' : 'ha-offline';
  return '<div class="ha-main">' + haRoleMark(host.role) + haEscape(host.name) + '</div>' +
    '<div class="ha-sub">' + haEscape(host.ip) + ' / <span class="' + onlineCls + '">' + onlineText + '</span></div>' +
    '<div class="ha-sub">host_id: ' + haEscape(host.host_id) + '</div>';
}

function haHostStatusDot(pair, host) {
  var state = haHostSwitchState(pair, host);
  if (state.status === 'running') {
    return '<span class="ha-host-dot ha-host-dot-switching" title="正在切换中：' + haAttr(state.step) + '"></span>';
  }
  if (host.online !== 'online') {
    return '<span class="ha-host-dot ha-host-dot-offline" title="主机离线或插件失联"></span>';
  }
  return '<span class="ha-host-dot ha-host-dot-online" title="主机在线"></span>';
}

function haHostLine(pair, host, isCurrentDatacenter) {
  var currentMark = isCurrentDatacenter ? '<span class="ha-current-site-tag" title="当前机房主机">本机房</span>' : '';
  var nameCls = host.online === 'online' ? 'ha-host-name' : 'ha-host-name ha-host-name-offline';
  return '<div class="ha-host-line">' +
    haHostStatusDot(pair, host) +
    haRoleMark(host.role) +
    '<span class="' + nameCls + '" title="' + haAttr(host.name) + '">' + haEscape(host.name) + '</span>' + currentMark +
    '<span class="ha-host-ip">' + haEscape(host.ip) + '</span>' +
    '</div>';
}

function haHostsCell(pair) {
  return '<div class="ha-host-list-cell">' + pair.hosts.map(function(host, index) {
    return haHostLine(pair, host, index === 0);
  }).join('') + '</div>';
}

function haHealthItem(label, value) {
  return '<div class="ha-health-item"><div class="ha-health-label">' + haEscape(label) + '</div><div class="ha-health-value" title="' + haAttr(value) + '">' + haEscape(value) + '</div></div>';
}

function haHostHealth(pair, host, index) {
  var isOffline = host.online !== 'online';
  var isMaster = host.role === 'master';
  var statusText = isOffline ? '插件失联' : '插件在线';
  var mysqlText = isOffline ? '未知' : (isMaster ? pair.health.mysql : (pair.status === 'switching' ? '等待提升或同步' : '复制链路正常'));
  var rsyncText = isOffline ? '未知' : (isMaster ? pair.health.rsync : '备用同步正常');
  var openrestyText = isOffline ? '未知' : (isMaster ? pair.health.openresty : '备用机待启动');
  var reportTime = isOffline ? '超过 5 分钟未上报' : pair.last_report_at;
  var level = isOffline ? 'danger' : (pair.status === 'warning' && index === 0 ? 'warning' : 'normal');
  return {
    plugin: statusText,
    mysql: mysqlText,
    rsync: rsyncText,
    openresty: openrestyText,
    last_report_at: reportTime,
    level: level
  };
}

function haHealthLevelText(level) {
  if (level === 'danger') return '红色异常';
  if (level === 'warning') return '橙色提醒';
  return '正常';
}

function haHostSwitchState(pair, host) {
  if (pair.status === 'switching') {
    if (host.host_id === pair.actual_master_host_id) {
      return {phase: 'offline', status: 'success', step: '旧主机下线流程已完成或等待确认', next: '等待目标主机上线'};
    }
    if (host.host_id === pair.desired_master_host_id) {
      return {phase: 'online', status: 'running', step: pair.status_text || '上线中', next: '执行数据库提升、同步任务和 OpenResty 启动'};
    }
  }
  if (pair.status === 'danger' && host.online !== 'online') {
    return {phase: 'offline', status: 'error', step: '插件失联，无法领取下线阶段', next: '人工确认后可切换到备用机'};
  }
  if (host.host_id === pair.actual_master_host_id) {
    return {phase: 'stable', status: 'success', step: '当前承载主机角色', next: '无执行中任务'};
  }
  return {phase: 'standby', status: 'waiting', step: '备用机待命', next: '等待手动切换或云监控期望状态变更'};
}

function haSwitchStatusText(status) {
  if (status === 'success') return '成功';
  if (status === 'running') return '执行中';
  if (status === 'error') return '失败';
  return '等待';
}

function haSwitchStatusClass(status) {
  if (status === 'error') return 'ha-pill-danger';
  if (status === 'running') return 'ha-pill-switching';
  if (status === 'success') return 'ha-pill-normal';
  return 'ha-pill-warning';
}

function haHostLogText(pair, host) {
  var lines = (pair.log || '').split('\n').filter(function(line) {
    return line.indexOf('[' + host.host_id + ']') !== -1;
  });
  if (lines.length) return lines.join('\n');
  if (host.online !== 'online') {
    return '[暂无主机日志] 插件离线或尚未完成日志上报。';
  }
  return '[暂无主机日志] 当前主机没有参与最近一次切换阶段。';
}

function haPairSyncCell(pair) {
  var actualMaster = haFindHost(pair, pair.actual_master_host_id) || {};
  var desiredMaster = haFindHost(pair, pair.desired_master_host_id) || {};
  if (pair.status === 'switching') {
    return '<div class="ha-sync-wait">切换中</div><div class="ha-sub">期望: ' + haEscape(desiredMaster.name || '--') + '</div>';
  }
  if (pair.desired_master_host_id === pair.actual_master_host_id) {
    return '<div class="ha-sync-ok">一致</div><div class="ha-sub">' + haEscape(actualMaster.name || '--') + '</div>';
  }
  return '<div class="ha-sync-bad">不一致</div><div class="ha-sub">实际: ' + haEscape(actualMaster.name || '--') + '</div>';
}

function haStatusTooltip(pair) {
  var actualMaster = haFindHost(pair, pair.actual_master_host_id) || {};
  var desiredMaster = haFindHost(pair, pair.desired_master_host_id) || {};
  var warnings = pair.warnings && pair.warnings.length ? pair.warnings.join('；') : '无待处理提醒';
  var operation = pair.status === 'switching' ? (pair.status_text || '切换中') : '无执行中操作';
  return '提醒: ' + warnings + '\n' +
    '当前状态: ' + haStatusLabel(pair.status) + '\n' +
    '状态说明: ' + (pair.status_text || '--') + '\n' +
    '正在执行: ' + operation + '\n' +
    '实际主机: ' + (actualMaster.name || '--') + ' / ' + (actualMaster.ip || '--') + '\n' +
    '期望主机: ' + (desiredMaster.name || '--') + ' / ' + (desiredMaster.ip || '--');
}

function haRenderList(search) {
  if (typeof search !== 'undefined') haCurrentSearch = search || '';
  var keyword = normalizeText(haCurrentSearch).toLowerCase();
  var rows = haPairs.slice().sort(function(a, b) {
    return haStatusWeight(a.status) - haStatusWeight(b.status);
  }).filter(function(pair) {
    if (!keyword) return true;
    var haystack = [pair.pair_name, pair.pair_id, pair.status_text]
      .concat(pair.hosts.map(function(host) { return host.name + ' ' + host.host_id + ' ' + host.ip; }))
      .join(' ').toLowerCase();
    return haystack.indexOf(keyword) !== -1;
  });
  if (rows.length === 0) {
    $('#haPairBody').html('');
    $('#haEmptyState').show();
    return;
  }
  $('#haEmptyState').hide();
  var html = '';
  rows.forEach(function(pair) {
    var statusTip = haStatusTooltip(pair);
    html += '<tr>' +
      '<td><div class="ha-main">' + haEscape(pair.pair_name) + '</div><div class="ha-sub">' + haEscape(pair.pair_id) + '</div></td>' +
      '<td>' + haHostsCell(pair) + '</td>' +
      '<td class="text-center"><span class="ha-status-pill ' + haStatusClass(pair.status) + '" title="' + haAttr(statusTip) + '">' + haStatusLabel(pair.status) + '</span><div class="ha-status-desc" title="' + haAttr(pair.status_text || '') + '">' + haEscape(pair.status_text || '') + '</div></td>' +
      '<td class="text-center"><div class="ha-sub">' + haEscape(pair.last_report_at) + '</div></td>' +
      '<td class="text-right ha-op-links">' +
        '<a class="btlink" href="javascript:;" onclick="haOpenDetailDialog(\'' + haAttr(pair.pair_id) + '\')">详情</a>' +
        '<a class="btlink" href="javascript:;" onclick="haOpenSwitchDialog(\'' + haAttr(pair.pair_id) + '\')">切换</a>' +
        '<a class="btlink" href="javascript:;" onclick="haOpenLogDialog(\'' + haAttr(pair.pair_id) + '\')">日志</a>' +
      '</td>' +
      '</tr>';
  });
  $('#haPairBody').html(html);
}

function haSwitchOptionsHtml(pair, target) {
  var hostSelect = '<div class="ha-switch-hosts">' + pair.hosts.map(function(host) {
    var checked = host.host_id === target.host_id ? 'checked' : '';
    var roleText = host.role === 'master' ? '主' : '备';
    return '<label class="ha-switch-host"><input type="radio" name="haSwitchTargetHost" value="' + haAttr(host.host_id) + '" ' + checked + '>' +
      '<span class="ha-switch-host-name">' + haEscape(host.name) + '</span>' +
      '<div class="ha-switch-host-meta">当前: ' + roleText + ' / IP: ' + haEscape(host.ip || '--') + '</div>' +
    '</label>';
  }).join('') + '</div>';
  return '<div class="pd15">' +
    '<div class="c6 mb10">选择要切换为主机的目标主机，确认后云监控会创建切换任务并等待插件领取执行。</div>' +
    hostSelect +
    '<div class="ha-switch-options"><div class="ha-switch-options-title">切换选项</div>' +
      '<div class="ha-option-grid">' +
        '<label class="ha-option-check"><input type="checkbox" id="haSyncFiles" onchange="haToggleSyncOptions()" checked><span>同步文件</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" id="haRunChecksum" checked><span>检查 checksum</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" id="haAllowChecksumDiff"><span>允许忽略 checksum 差异</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" id="haRestoreSite"><span>恢复网站配置</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" id="haRestorePlugin"><span>面板插件配置</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" id="haRunXtrabackup"><span>执行增量恢复</span></label>' +
      '</div>' +
      '<div class="ha-sync-options ha-sync-group">' +
        '<div class="ha-sync-field"><span>同步目录</span><input class="bt-input-text" value="/www/wwwroot,/www/wwwstorage"></div>' +
        '<div class="ha-sync-field"><span>忽略目录</span><input class="bt-input-text" value="node_modules,logs,run"></div>' +
      '</div>' +
    '</div>' +
    '</div>';
}

function haToggleSyncOptions() {
  $('.ha-sync-options').toggle($('#haSyncFiles').is(':checked'));
}

function haOpenSwitchDialog(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  var target = pair.hosts[0].host_id === pair.actual_master_host_id ? pair.hosts[1] : pair.hosts[0];
  layer.open({
    type: 1,
    title: '手动切换 - ' + pair.pair_name,
    area: ['750px', '500px'],
    content: haSwitchOptionsHtml(pair, target),
    btn: ['确认发起切换', '取消'],
    success: function() {
      haToggleSyncOptions();
    },
    yes: function(index) {
      var selectedHostId = $('[name=haSwitchTargetHost]:checked').val();
      target = haFindHost(pair, selectedHostId) || target;
      var payload = {
        pair_id: pair.pair_id,
        target_host_id: target.host_id,
        sync_files: $('#haSyncFiles').is(':checked') ? 1 : 0,
        run_checksum: $('#haRunChecksum').is(':checked') ? 1 : 0,
        allow_checksum_diff: $('#haAllowChecksumDiff').is(':checked') ? 1 : 0,
        restore_site_setting: $('#haRestoreSite').is(':checked') ? 1 : 0,
        restore_plugin_setting: $('#haRestorePlugin').is(':checked') ? 1 : 0,
        run_xtrabackup_inc_restore: $('#haRunXtrabackup').is(':checked') ? 1 : 0
      };
      haApi('request_switch', payload, function(data) {
        if (!data) return;
        layer.close(index);
        layer.msg('切换任务已创建', {icon: 1});
        haLoadPairs();
      });
    }
  });
}

function haOpenDetailDialog(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  var tabs = [
    {title: '组别概览', tab: 'summary'},
    {title: '主机列表', tab: 'hosts'},
    {title: '自检状态', tab: 'health'},
    {title: '切换状态', tab: 'switch'},
    {title: '切换日志', tab: 'log'}
  ];
  var html = '<div class="bt-form ha-detail-shell">' +
    '<div class="bt-w-menu pull-left ha-detail-menu">' +
      tabs.map(function(item, index) {
        return '<p class="' + (index === 0 ? 'bgw' : '') + '" onclick="haRenderDetailTab(\'' + haAttr(pair.pair_id) + '\', \'' + item.tab + '\', this)" title="' + haAttr(item.title) + '">' + haEscape(item.title) + '</p>';
      }).join('') +
    '</div>' +
    '<div id="haDetailCon" class="bt-w-con ha-detail-con pd15"></div>' +
  '</div>';
  layer.open({
    type: 1,
    title: '主备详情[' + pair.pair_name + ']',
    area: ['1040px', '640px'],
    closeBtn: 1,
    content: html,
    success: function() {
      haRenderDetailTab(pair.pair_id, 'summary');
    }
  });
}

function haRenderDetailTab(pairId, tab, el) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  if (el) $(el).addClass('bgw').siblings().removeClass('bgw');
  var html = '';
  if (tab === 'hosts') html = haDetailHostsHtml(pair);
  else if (tab === 'health') html = haDetailChecksHtml(pair);
  else if (tab === 'switch') html = haDetailSwitchHtml(pair);
  else if (tab === 'log') html = haDetailLogHtml(pair);
  else html = haDetailSummaryHtml(pair);
  $('#haDetailCon').html(html);
}

function haDetailSummaryHtml(pair) {
  var actualMaster = haFindHost(pair, pair.actual_master_host_id) || {};
  var desiredMaster = haFindHost(pair, pair.desired_master_host_id) || {};
  var warnings = pair.warnings && pair.warnings.length ? pair.warnings.join('；') : '无待处理提醒';
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">组别概览</div>' +
    '<table class="table table-hover" style="margin-bottom:10px"><tbody>' +
    '<tr><td width="130">主备关系</td><td>' + haEscape(pair.pair_name) + '</td></tr>' +
    '<tr><td>状态</td><td><span class="ha-status-pill ' + haStatusClass(pair.status) + '" title="' + haAttr(pair.status_text || '') + '">' + haStatusLabel(pair.status) + '</span></td></tr>' +
    '<tr><td>实际主机</td><td>' + haEscape(actualMaster.name || '--') + ' / ' + haEscape(actualMaster.ip || '--') + '</td></tr>' +
    '<tr><td>期望主机</td><td>' + haEscape(desiredMaster.name || '--') + ' / ' + haEscape(desiredMaster.ip || '--') + '</td></tr>' +
    '<tr><td>切换任务</td><td>' + haEscape(pair.switch_run_id) + '</td></tr>' +
    '<tr><td>日志路径</td><td>' + haEscape(pair.log_path) + '</td></tr>' +
    '<tr><td>最近上报</td><td>' + haEscape(pair.last_report_at) + '</td></tr>' +
    '<tr><td>提醒摘要</td><td>' + haEscape(warnings) + '</td></tr>' +
    '</tbody></table>' +
    '</div>';
}

function haDetailHostsHtml(pair) {
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">主机列表</div>' +
    '<table class="table table-hover" style="margin-bottom:10px"><thead><tr><th>主机</th><th>IP</th><th>实际角色</th><th>在线状态</th></tr></thead><tbody>' +
      pair.hosts.map(function(host) {
        return '<tr><td><div class="ha-main">' + haEscape(host.name) + '</div><div class="ha-sub">' + haEscape(host.host_id || '') + '</div></td><td>' + haEscape(host.ip) + '</td><td>' + haRoleMark(host.role) + haEscape(host.role) + '</td><td>' + (host.online === 'online' ? '<span class="ha-online">在线</span>' : '<span class="ha-offline">离线</span>') + '</td></tr>';
      }).join('') +
    '</tbody></table>' +
    '<div class="ha-muted">主机数据来自 ha_manager 插件注册和状态上报。</div>' +
    '</div>';
}

function haDetailSwitchHtml(pair) {
  var hostRows = pair.hosts.map(function(host) {
    var state = haHostSwitchState(pair, host);
    return '<tr>' +
      '<td><div class="ha-main">' + haRoleMark(host.role) + haEscape(host.name) + '</div><div class="ha-sub">' + haEscape(host.ip) + ' / ' + haEscape(host.host_id) + '</div></td>' +
      '<td>' + haEscape(state.phase) + '</td>' +
      '<td><span class="ha-status-pill ' + haSwitchStatusClass(state.status) + '">' + haSwitchStatusText(state.status) + '</span></td>' +
      '<td>' + haEscape(state.step) + '</td>' +
      '<td>' + haEscape(state.next) + '</td>' +
      '<td>' + haEscape(pair.log_path) + '</td>' +
    '</tr>';
  }).join('');
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">步骤摘要</div>' +
    '<div class="ha-health-row">' +
      haHealthItem('offline', pair.status === 'switching' ? '已完成或等待中' : '无执行中任务') +
      haHealthItem('online', pair.status === 'switching' ? pair.status_text : '无执行中任务') +
      haHealthItem('callback', pair.status === 'normal' ? '最近成功' : '等待切换完成') +
    '</div>' +
    '<table class="table table-hover mtb15 ha-switch-detail-table"><thead><tr><th width="190">主机</th><th width="80">阶段</th><th width="90">状态</th><th>当前步骤</th><th>下一步</th><th width="210">日志文件</th></tr></thead><tbody>' + hostRows + '</tbody></table>' +
    '<table class="table table-hover mtb15"><tbody>' +
      '<tr><td width="130">切换任务</td><td>' + haEscape(pair.switch_run_id) + '</td></tr>' +
      '<tr><td>当前阶段</td><td>' + (pair.status === 'switching' ? haEscape(pair.status_text) : '无执行中任务') + '</td></tr>' +
      '<tr><td>日志文件</td><td>' + haEscape(pair.log_path) + '</td></tr>' +
      '<tr><td>操作</td><td><a class="btlink" href="javascript:;" onclick="haOpenSwitchDialog(\'' + haAttr(pair.pair_id) + '\')">发起切换</a><a class="btlink ml10" href="javascript:;" onclick="haOpenLogDialog(\'' + haAttr(pair.pair_id) + '\')">查看日志</a></td></tr>' +
    '</tbody></table>' +
    '</div>';
}

function haDetailLogHtml(pair) {
  var hostLogs = pair.hosts.map(function(host) {
    var state = haHostSwitchState(pair, host);
    return '<div class="ha-host-log-panel">' +
      '<div class="ha-host-log-head">' +
        '<div><div class="ha-main">' + haRoleMark(host.role) + haEscape(host.name) + '</div><div class="ha-sub">' + haEscape(host.ip) + ' / ' + haEscape(host.host_id) + '</div></div>' +
        '<span class="ha-status-pill ' + haSwitchStatusClass(state.status) + '">' + haSwitchStatusText(state.status) + '</span>' +
      '</div>' +
      '<div class="ha-log-box ha-host-log-box">' + haEscape(haHostLogText(pair, host)) + '</div>' +
    '</div>';
  }).join('');
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">切换日志</div>' +
    '<div class="ha-muted mb10">日志文件: ' + haEscape(pair.log_path) + '</div>' +
    '<div class="ha-host-log-grid">' + hostLogs + '</div>' +
    '<div class="monitor-task-section-title mtb15">完整日志</div>' +
    '<div class="ha-log-box ha-detail-log-box">' + haEscape(pair.log || '暂无日志') + '</div>' +
    '</div>';
}

function haOpenLogDialog(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  if (pair.switch_run_id) {
    haApi('read_log', {switch_run_id: pair.switch_run_id, offset: 0}, function(data) {
      if (!data) return;
      pair.log = data.content || '';
      pair.log_path = data.log_path || pair.log_path;
      haOpenLogDialog(pairId);
    });
    return;
  }
  var html = '<div class="pd15">' +
    '<div class="ha-muted mb10">日志文件: ' + haEscape(pair.log_path) + '</div>' +
    '<div class="ha-log-box">' + haEscape(pair.log || '暂无日志') + '</div>' +
    '</div>';
  layer.open({
    type: 1,
    title: '切换日志 - ' + pair.switch_run_id,
    area: ['820px', '520px'],
    content: html,
    btn: ['刷新', '关闭'],
    yes: function() {
      layer.closeAll();
      haOpenLogDialog(pairId);
    }
  });
}

function haRefreshList() {
  haLoadPairs(function() {
    layer.msg('已刷新主备状态', {icon: 1});
  });
}

$(function() {
  setTimeout(function() {
    haLoadPairs();
  }, 200);
});
