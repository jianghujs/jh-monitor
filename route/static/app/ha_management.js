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

function haStorePair(pair) {
  if (!pair || !pair.pair_id) return;
  for (var i = 0; i < haPairs.length; i++) {
    if (haPairs[i].pair_id === pair.pair_id) {
      haPairs[i] = pair;
      return;
    }
  }
  haPairs.push(pair);
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

function haNormalizeChecks(host) {
  var detail = host.health_detail || {};
  var checks = [];
  if ($.isArray(host.script_checks)) checks = host.script_checks;
  else if ($.isArray(detail.script_checks)) checks = detail.script_checks;
  else if ($.isArray(detail.checks)) checks = detail.checks;
  if (checks.length) return checks;
  var summary = detail.summary || host.health_text || '';
  if (summary) {
    return [{group: '健康摘要', name: '状态摘要', expected: '', actual: summary, status: host.health_status || 'unknown', message: ''}];
  }
  return [];
}

function haCheckStatus(status) {
  status = (status || '').toLowerCase();
  if (status === 'ok' || status === 'success' || status === 'normal' || status === 'pass' || status === 'passed') return 'pass';
  if (status === 'warn' || status === 'warning') return 'warning';
  if (status === 'fail' || status === 'failed' || status === 'error' || status === 'danger') return 'failed';
  if (status === 'skip' || status === 'skipped') return 'skipped';
  return status || 'unknown';
}

function haCheckStatusIcon(status) {
  status = haCheckStatus(status);
  if (status === 'pass') return '<span class="ha-check-icon ha-check-pass" title="正常">✓</span>';
  if (status === 'warning' || status === 'skipped') return '<span class="ha-check-icon ha-check-warn" title="提醒">!</span>';
  if (status === 'unknown') return '<span class="ha-check-icon ha-check-unknown" title="未知">?</span>';
  return '<span class="ha-check-icon ha-check-fail" title="异常">✗</span>';
}

function haDetailChecksHtml(pair) {
  var hostCards = pair.hosts.map(function(host, index) {
    var checks = haNormalizeChecks(host);
    var rows = '';
    var currentGroup = '';
    if (!checks.length) {
      rows = '<tr><td colspan="2" class="ha-muted">暂无自检明细，等待插件上报。</td></tr>';
    } else {
      checks.forEach(function(item) {
        var group = item.group || '其他';
        if (group !== currentGroup) {
          currentGroup = group;
          rows += '<tr class="ha-check-group-row"><td colspan="2">' + haEscape(group) + '</td></tr>';
        }
        var status = haCheckStatus(item.status);
        var matched = status === 'pass';
        var actualCls = matched ? 'ha-check-actual-pass' : 'ha-check-actual-fail';
        var actual = item.actual || item.text || item.message || '未知';
        var expected = item.expected || '';
        var statusTitle = '当前状态: ' + actual + (expected ? '\n期望状态: ' + expected : '') + (item.message ? '\n说明: ' + item.message : '');
        rows += '<tr>' +
          '<td class="ha-check-name">' + haEscape(item.name || '未命名检查项') + '</td>' +
          '<td class="ha-check-actual ' + actualCls + '" title="' + haAttr(statusTitle) + '">' + haCheckStatusIcon(status) + haEscape(actual) + '</td>' +
        '</tr>';
      });
    }
    var sourceText = host.collect_method ? '采集来源: ' + host.collect_method + ' / ' + (host.collect_status || 'unknown') : '采集来源: 未知';
    if (host.last_report_at) sourceText += ' / ' + host.last_report_at;
    var dot = haHostStatusDot(pair, host);
    var switchState = haHostSwitchState(pair, host);
    var switchingMark = switchState.status === 'running' ? '<span class="ha-switching-state" title="' + haAttr(switchState.step) + '"><span class="ha-loading-icon"></span>切换中</span>' : '';
    var nameCls = host.online === 'online' ? 'ha-host-name' : 'ha-host-name ha-host-name-offline';
    var currentMark = haIsCurrentDatacenterHost(pair, host, index) ? '<span class="ha-current-site-tag">本机房</span>' : '';
    return '<div class="ha-check-host-card">' +
      '<div class="ha-check-host-head">' + dot + haRoleMark(host.role) +
        '<span class="' + nameCls + '">' + haEscape(host.name) + '</span>' +
        currentMark + switchingMark +
      '</div>' +
      '<div class="ha-muted mb10">' + haEscape(sourceText) + '</div>' +
      '<table class="table table-hover ha-check-table"><colgroup><col><col class="ha-check-status-col"></colgroup><thead><tr><th>检查项</th><th class="ha-check-status-head">状态</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '</div>';
  }).join('');
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">自检状态</div>' +
    '<div class="ha-muted mb10">展示 ha_manager 插件上报的真实自检明细；缺失明细时显示摘要或等待上报。</div>' +
    '<div class="ha-check-grid">' + hostCards + '</div>' +
    '</div>';
}

function haRoleMark(role) {
  var cls = role === 'master' ? 'ha-role-master' : 'ha-role-standby';
  var text = role === 'master' ? '主' : (role === 'standby' ? '备' : '?');
  return '<span class="ha-role-mark ' + cls + '">' + text + '</span>';
}

function haHostCell(host) {
  var onlineText = host.online === 'online' ? '在线' : (host.online === 'offline' ? '离线' : '未知');
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
  if (haHostLooksHealthy(host)) {
    return '<span class="ha-host-dot ha-host-dot-online" title="主机自检正常"></span>';
  }
  if (host.online !== 'online') {
    return '<span class="ha-host-dot ha-host-dot-offline" title="主机离线、插件失联或尚未上报真实状态"></span>';
  }
  return '<span class="ha-host-dot ha-host-dot-online" title="主机在线"></span>';
}

function haHostLooksHealthy(host) {
  if (host.online === 'online') return true;
  if (host.health_status === 'normal') return true;
  var checks = haNormalizeChecks(host);
  if (!checks.length) return false;
  for (var i = 0; i < checks.length; i++) {
    var status = haCheckStatus(checks[i].status);
    if (status !== 'pass' && status !== 'skipped') return false;
  }
  return true;
}

function haIsCurrentDatacenterHost(pair, host, index) {
  if (host.site_scope) return host.site_scope === 'local';
  var methods = host.host_alias_collect_methods || [];
  if (host.collect_method === 'local' || methods.indexOf('local') !== -1) return true;
  var hasLocal = false;
  (pair.hosts || []).forEach(function(item) {
    var itemMethods = item.host_alias_collect_methods || [];
    if (item.collect_method === 'local' || itemMethods.indexOf('local') !== -1) hasLocal = true;
  });
  return !hasLocal && index === 0;
}

function haOnlineLabel(host) {
  if (haHostLooksHealthy(host)) return '<span class="ha-online">正常</span>';
  if (host.online === 'offline') return '<span class="ha-offline">离线</span>';
  if (host.collect_status === 'failed') return '<span class="ha-offline">采集失败</span>';
  return '<span class="ha-muted">待上报</span>';
}

function haCollectMethodText(method) {
  if (method === 'local') return '本机插件';
  if (method === 'ssh_peer') return 'SSH采集对端';
  return method || '插件上报';
}

function haDisplayCollectMethod(host) {
  var methods = host.host_alias_collect_methods || [];
  if (host.collect_method === 'local' || methods.indexOf('local') !== -1) return 'local';
  return host.collect_method || '';
}

function haCollectLabel(host) {
  var method = haDisplayCollectMethod(host);
  if (host.collect_status === 'success') {
    return '<div><span class="ha-online">正常</span></div><div class="ha-sub">' + haEscape(haCollectMethodText(method)) + '</div>';
  }
  if (method === 'ssh_peer' && host.collect_status === 'partial') {
    return '<div><span class="ha-pill-warning ha-status-pill">部分成功</span></div><div class="ha-sub">SSH 已连接，日志采集不完整</div>';
  }
  if (host.collect_status === 'failed') {
    return '<div><span class="ha-offline">SSH采集异常</span></div><div class="ha-sub">' + haEscape(haCollectMethodText(method || '--')) + '</div>';
  }
  if (haHostLooksHealthy(host)) {
    return '<div><span class="ha-online">正常</span></div><div class="ha-sub">自检通过</div>';
  }
  return '<div><span class="ha-muted">待上报</span></div><div class="ha-sub">' + haEscape(haCollectMethodText(method || '--')) + '</div>';
}

function haHostLine(pair, host, index) {
  var currentMark = haIsCurrentDatacenterHost(pair, host, index) ? '<span class="ha-current-site-tag" title="当前机房主机">本机房</span>' : '';
  var nameCls = haHostLooksHealthy(host) ? 'ha-host-name' : 'ha-host-name ha-host-name-offline';
  var meta = [];
  if (host.collect_method) meta.push(host.collect_method);
  if (host.collect_status) meta.push(host.collect_status);
  if (host.last_report_at) meta.push(host.last_report_at);
  return '<div class="ha-host-line">' +
    haHostStatusDot(pair, host) +
    haRoleMark(host.role) +
    '<span class="' + nameCls + '" title="' + haAttr(host.name) + '">' + haEscape(host.name) + '</span>' + currentMark +
    '<span class="ha-host-ip" title="' + haAttr(meta.join(' / ')) + '">' + haEscape(host.ip) + '</span>' +
    '</div>';
}

function haHostsCell(pair) {
  return '<div class="ha-host-list-cell">' + pair.hosts.map(function(host, index) {
    return haHostLine(pair, host, index);
  }).join('') + '</div>';
}

function haHealthItem(label, value) {
  return '<div class="ha-health-item"><div class="ha-health-label">' + haEscape(label) + '</div><div class="ha-health-value" title="' + haAttr(value) + '">' + haEscape(value) + '</div></div>';
}

function haDetailMetric(label, value, extraCls) {
  return '<div class="ha-detail-metric ' + (extraCls || '') + '"><div class="ha-detail-metric-label">' + haEscape(label) + '</div><div class="ha-detail-metric-value" title="' + haAttr(value || '--') + '">' + haEscape(value || '--') + '</div></div>';
}

function haDetailHostCard(pair, host, index) {
  var isMaster = host.role === 'master';
  var currentMark = haIsCurrentDatacenterHost(pair, host, index) ? '<span class="ha-current-site-tag">本机房</span>' : '';
  var roleText = isMaster ? '当前主机' : (host.role === 'standby' ? '当前备机' : '角色未知');
  var cls = isMaster ? 'ha-detail-host-card is-master' : 'ha-detail-host-card';
  return '<div class="' + cls + '">' +
    '<div class="ha-detail-host-top">' +
      '<div class="ha-detail-host-title">' + haHostStatusDot(pair, host) + haRoleMark(host.role) + '<span title="' + haAttr(host.name) + '">' + haEscape(host.name) + '</span></div>' +
      currentMark +
    '</div>' +
    '<div class="ha-detail-host-ip">' + haEscape(host.ip || '--') + '</div>' +
    '<div class="ha-detail-host-meta"><span>' + haEscape(roleText) + '</span><span>' + haEscape(haCollectMethodText(haDisplayCollectMethod(host))) + '</span><span>' + haEscape(host.last_report_at || '未上报') + '</span></div>' +
  '</div>';
}

function haHostHealth(pair, host, index) {
  var detail = host.health_detail || {};
  var isOffline = host.online !== 'online';
  var statusText = isOffline ? '插件失联或未知' : '插件在线';
  var mysqlText = haHealthDetailText(detail.mysql, '未知');
  var rsyncText = haHealthDetailText(detail.rsync, '未知');
  var openrestyText = haHealthDetailText(detail.openresty, '未知');
  var reportTime = host.last_report_at || pair.last_report_at || '未上报';
  var level = isOffline ? 'danger' : (host.health_status === 'warning' || host.health_status === 'danger' || host.health_status === 'failed' ? 'warning' : 'normal');
  return {
    plugin: statusText,
    mysql: mysqlText,
    rsync: rsyncText,
    openresty: openrestyText,
    last_report_at: reportTime,
    level: level
  };
}

function haHealthDetailText(item, fallback) {
  if ($.isPlainObject(item)) return item.text || item.status || fallback;
  return item || fallback;
}

function haHealthLevelText(level) {
  if (level === 'danger') return '红色异常';
  if (level === 'warning') return '橙色提醒';
  return '正常';
}

function haHostSwitchState(pair, host) {
  var run = pair.switch_run || {};
  var hostSwitchStatus = haNormalizeSwitchStatus(host.switch_status || '');
  if (host.switch_phase || host.switch_status || host.current_step || host.last_error || (host.switch_run_id && hostSwitchStatus)) {
    return {
      phase: host.switch_phase || run.current_phase || 'switch',
      status: hostSwitchStatus || haNormalizeSwitchStatus(run.status || '') || 'waiting',
      step: host.last_error || host.current_step || run.current_step || pair.status_text || '切换中',
      next: host.next_step || run.next_step || '等待下一次状态上报'
    };
  }
  if (run.switch_run_id && pair.status === 'switching') {
    return {
      phase: run.current_phase || 'switch',
      status: haNormalizeSwitchStatus(run.status || 'running'),
      step: run.last_error || run.current_step || pair.status_text || '切换中',
      next: run.next_step || '等待插件上报下一步'
    };
  }
  if (host.host_id === pair.actual_master_host_id) {
    return {phase: 'stable', status: 'success', step: '当前承载主机角色', next: '无执行中任务'};
  }
  return {phase: 'standby', status: 'waiting', step: '备用机待命', next: '等待手动切换或云监控期望状态变更'};
}

function haNormalizeSwitchStatus(status) {
  status = (status || '').toLowerCase();
  if (status === 'success' || status === 'done' || status.indexOf('_done') !== -1) return 'success';
  if (status === 'failed' || status === 'error' || status === 'waiting_retry') return 'error';
  if (status === 'running' || status === 'pending' || status === 'preparing' || status === 'finalizing' || status.indexOf('_running') !== -1) return 'running';
  return status || 'waiting';
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
  var events = pair.switch_events || [];
  var lines = [];
  events.forEach(function(item) {
    if (item.origin_host_id === host.host_id) {
      lines.push('[' + (item.addtime || '--') + '] [' + (item.phase || 'event') + '] [' + (item.status || 'info') + '] ' + (item.log_text || item.step || ''));
    }
  });
  if (lines.length) return lines.join('\n');
  lines = (pair.log || '').split('\n').filter(function(line) {
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
        '<a class="btlink" href="javascript:;" onclick="haDeletePair(\'' + haAttr(pair.pair_id) + '\')">删除</a>' +
      '</td>' +
      '</tr>';
  });
  $('#haPairBody').html(html);
}

function haDeletePair(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  layer.confirm('确认删除主备关系 [' + haEscape(pair.pair_name || pair.pair_id) + ']？<br>将清理云监控侧该记录及关联状态、切换任务和事件，日志文件会保留。', {
    icon: 3,
    title: '删除主备关系',
    btn: ['确认删除', '取消']
  }, function(index) {
    haApi('delete_pair', {pair_id: pairId}, function(data) {
      if (!data) return;
      layer.close(index);
      layer.msg('已删除主备关系', {icon: 1});
      haLoadPairs();
    });
  });
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
      haApi('get_detail', {pair_id: pair.pair_id}, function(data) {
        if (data) {
          haStorePair(data);
          pair = data;
        }
        haRenderDetailTab(pair.pair_id, 'summary');
      });
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
  var statusText = pair.status_text || haStatusLabel(pair.status);
  var hostCards = (pair.hosts || []).map(function(host, index) { return haDetailHostCard(pair, host, index); }).join('');
  return '<div class="ha-detail-section">' +
    '<div class="ha-detail-status-band ' + haStatusClass(pair.status) + '">' +
      '<div><div class="ha-detail-kicker">组别概览</div><div class="ha-detail-title">' + haEscape(pair.pair_name) + '</div><div class="ha-detail-id">' + haEscape(pair.pair_id) + '</div></div>' +
      '<div class="ha-detail-status-main"><span class="ha-status-pill ' + haStatusClass(pair.status) + '" title="' + haAttr(statusText) + '">' + haStatusLabel(pair.status) + '</span><div class="ha-detail-status-text" title="' + haAttr(statusText) + '">' + haEscape(statusText) + '</div></div>' +
    '</div>' +
    '<div class="ha-detail-metrics">' +
      haDetailMetric('实际主机', (actualMaster.name || '--') + ' / ' + (actualMaster.ip || '--'), 'is-actual') +
      haDetailMetric('期望主机', (desiredMaster.name || '--') + ' / ' + (desiredMaster.ip || '--'), 'is-desired') +
      haDetailMetric('最近上报', pair.last_report_at || '--', '') +
      haDetailMetric('当前任务', pair.switch_run_id || '无执行中任务', '') +
    '</div>' +
    '<div class="ha-detail-host-grid">' + hostCards + '</div>' +
    '<div class="ha-detail-note"><span>提醒摘要</span><div title="' + haAttr(warnings) + '">' + haEscape(warnings) + '</div></div>' +
    '</div>';
}

function haDetailHostsHtml(pair) {
  var cards = (pair.hosts || []).map(function(host, index) { return haDetailHostCard(pair, host, index); }).join('');
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">主机列表</div>' +
    '<div class="ha-detail-host-grid mb12">' + cards + '</div>' +
    '<table class="table table-hover ha-detail-data-table" style="margin-bottom:10px"><thead><tr><th>主机</th><th>IP</th><th>实际角色</th><th>在线状态</th><th>采集状态</th><th>最近上报</th></tr></thead><tbody>' +
      pair.hosts.map(function(host) {
        return '<tr><td><div class="ha-main">' + haEscape(host.name) + '</div><div class="ha-sub">' + haEscape(host.host_id || '') + '</div></td>' +
          '<td>' + haEscape(host.ip) + '</td>' +
          '<td>' + haRoleMark(host.role) + haEscape(host.role) + '</td>' +
          '<td>' + haOnlineLabel(host) + '</td>' +
          '<td>' + haCollectLabel(host) + '</td>' +
          '<td>' + haEscape(host.last_report_at || '--') + '</td></tr>';
      }).join('') +
    '</tbody></table>' +
    '<div class="ha-muted">主机数据来自 ha_manager 插件注册和状态上报。</div>' +
    '</div>';
}

function haDetailSwitchHtml(pair) {
  var run = pair.switch_run || {};
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
  var phaseText = run.current_phase || (pair.status === 'switching' ? pair.status_text : '无执行中任务');
  return '<div class="ha-detail-section">' +
    '<div class="monitor-task-section-title">步骤摘要</div>' +
    '<div class="ha-health-row ha-detail-switch-row">' +
      haHealthItem('任务状态', run.status || (pair.status === 'switching' ? 'running' : '无执行中任务')) +
      haHealthItem('当前阶段', phaseText) +
      haHealthItem('回调状态', run.callback_status || pair.callback_status || '未触发') +
    '</div>' +
    '<table class="table table-hover mtb15 ha-switch-detail-table ha-detail-data-table"><thead><tr><th width="190">主机</th><th width="80">阶段</th><th width="90">状态</th><th>当前步骤</th><th>下一步</th><th width="210">日志文件</th></tr></thead><tbody>' + hostRows + '</tbody></table>' +
    '<table class="table table-hover mtb15 ha-detail-data-table"><tbody>' +
      '<tr><td width="130">切换任务</td><td>' + haEscape(pair.switch_run_id) + '</td></tr>' +
      '<tr><td>当前阶段</td><td>' + haEscape(phaseText) + '</td></tr>' +
      '<tr><td>当前步骤</td><td>' + haEscape(run.current_step || '--') + '</td></tr>' +
      '<tr><td>下一步</td><td>' + haEscape(run.next_step || '--') + '</td></tr>' +
      '<tr><td>最后错误</td><td>' + haEscape(run.last_error || '--') + '</td></tr>' +
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
