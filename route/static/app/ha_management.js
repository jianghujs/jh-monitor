var haPairs = [
  {
    pair_id: 'HA_JIANGHU_DEMO',
    pair_name: '江湖演示',
    status: 'danger',
    status_text: '主机离线',
    desired_master_host_id: 'H_DEMO_MEGA',
    actual_master_host_id: 'H_DEMO_MEGA',
    last_report_at: '2026-08-05 15:42:18',
    switch_run_id: 'HSR_20260805153000_f7a2',
    log_path: 'logs/ha_switch/2026-08/HSR_20260805153000_f7a2.log',
    hosts: [
      {host_id: 'H_DEMO_MEGA', name: '江湖演示@Mega', ip: '10.0.8.11', role: 'master', online: 'offline'},
      {host_id: 'H_DEMO_POLARIS', name: '江湖演示@Polaris', ip: '10.8.8.11', role: 'standby', online: 'online'}
    ],
    health: {mysql: '未知', rsync: '同步正常', openresty: '备用正常'},
    warnings: ['江湖演示@Mega 超过 5 分钟未上报', '建议确认业务流量后切换到 Polaris'],
    log: [
      '[2026-08-05 15:30:00] [system] [pending] 创建切换任务 HSR_20260805153000_f7a2',
      '[2026-08-05 15:30:02] [H_DEMO_MEGA] [offline] [error] 插件失联，等待上报',
      '[2026-08-05 15:42:18] [system] [danger] 当前主机离线，建议切换到备用机'
    ].join('\n')
  },
  {
    pair_id: 'HA_DEV02',
    pair_name: 'Dev02',
    status: 'warning',
    status_text: '部分异常',
    desired_master_host_id: 'H_DEV02_MEGA',
    actual_master_host_id: 'H_DEV02_MEGA',
    last_report_at: '2026-08-05 16:01:45',
    switch_run_id: 'HSR_20260804190000_c1e9',
    log_path: 'logs/ha_switch/2026-08/HSR_20260804190000_c1e9.log',
    hosts: [
      {host_id: 'H_DEV02_MEGA', name: 'Dev02@Mega', ip: '10.0.9.21', role: 'master', online: 'online'},
      {host_id: 'H_DEV02_POLARIS', name: 'Dev02@Polaris', ip: '10.8.9.21', role: 'standby', online: 'online'}
    ],
    health: {mysql: '主从延迟 38s', rsync: 'lsyncd warning', openresty: '运行中'},
    warnings: ['mysql 主从延迟超过提醒阈值', 'Rsync 状态异常提醒已触发'],
    log: [
      '[2026-08-04 19:00:00] [system] [success] 上次切换完成',
      '[2026-08-05 16:01:45] [H_DEV02_MEGA] [warning] mysql 主从延迟 38s',
      '[2026-08-05 16:01:45] [H_DEV02_MEGA] [warning] lsyncd 存在 warning 状态'
    ].join('\n')
  },
  {
    pair_id: 'HA_DEV03',
    pair_name: 'Dev03',
    status: 'normal',
    status_text: '状态正常',
    desired_master_host_id: 'H_DEV03_POLARIS',
    actual_master_host_id: 'H_DEV03_POLARIS',
    last_report_at: '2026-08-05 16:03:10',
    switch_run_id: 'HSR_20260803101500_9bd3',
    log_path: 'logs/ha_switch/2026-08/HSR_20260803101500_9bd3.log',
    hosts: [
      {host_id: 'H_DEV03_MEGA', name: 'Dev03@Mega', ip: '10.0.10.31', role: 'standby', online: 'online'},
      {host_id: 'H_DEV03_POLARIS', name: 'Dev03@Polaris', ip: '10.8.10.31', role: 'master', online: 'online'}
    ],
    health: {mysql: '主从正常', rsync: '同步正常', openresty: '运行中'},
    warnings: [],
    log: [
      '[2026-08-03 10:15:00] [system] [pending] 创建切换任务',
      '[2026-08-03 10:16:12] [H_DEV03_MEGA] [offline] [success] 下线流程完成',
      '[2026-08-03 10:21:08] [H_DEV03_POLARIS] [online] [success] 上线流程完成',
      '[2026-08-03 10:21:20] [system] [success] 外部回调完成'
    ].join('\n')
  },
  {
    pair_id: 'HA_MD_XUANFENG',
    pair_name: 'MD 旋风',
    status: 'switching',
    status_text: '上线中',
    desired_master_host_id: 'H_MDXF_POLARIS',
    actual_master_host_id: 'H_MDXF_MEGA',
    last_report_at: '2026-08-05 16:04:02',
    switch_run_id: 'HSR_20260805160000_7bc0',
    log_path: 'logs/ha_switch/2026-08/HSR_20260805160000_7bc0.log',
    hosts: [
      {host_id: 'H_MDXF_MEGA', name: 'MD旋风@Mega', ip: '10.0.11.41', role: 'master', online: 'online'},
      {host_id: 'H_MDXF_POLARIS', name: 'MD旋风@Polaris', ip: '10.8.11.41', role: 'standby', online: 'online'}
    ],
    health: {mysql: '提升为主中', rsync: '等待启动', openresty: '等待启动'},
    warnings: ['正在执行备用机上线流程'],
    log: [
      '[2026-08-05 16:00:00] [system] [pending] 创建切换任务 HSR_20260805160000_7bc0',
      '[2026-08-05 16:00:11] [H_MDXF_MEGA] [offline] [success] 下线流程完成',
      '[2026-08-05 16:02:20] [H_MDXF_POLARIS] [online] [running] 将当前数据库提升为主',
      '[2026-08-05 16:04:02] [H_MDXF_POLARIS] [online] [running] 调整计划任务'
    ].join('\n')
  },
  {
    pair_id: 'HA_JIANGHU_PLATFORM',
    pair_name: '江湖平台',
    status: 'warning',
    status_text: '备用机离线',
    desired_master_host_id: 'H_JH_PLATFORM_MEGA',
    actual_master_host_id: 'H_JH_PLATFORM_MEGA',
    last_report_at: '2026-08-05 16:08:33',
    switch_run_id: 'HSR_20260802143000_5e21',
    log_path: 'logs/ha_switch/2026-08/HSR_20260802143000_5e21.log',
    hosts: [
      {host_id: 'H_JH_PLATFORM_MEGA', name: '江湖平台@Mega', ip: '10.0.12.51', role: 'master', online: 'online'},
      {host_id: 'H_JH_PLATFORM_POLARIS', name: '江湖平台@Polaris', ip: '10.8.12.51', role: 'standby', online: 'offline'}
    ],
    health: {mysql: '无主从配置（作为主）', rsync: '同步正常', openresty: '运行中'},
    warnings: ['江湖平台@Polaris 超过 5 分钟未上报', '当前主机仍在线，备用机不可接管前不建议切换'],
    log: [
      '[2026-08-05 16:05:00] [H_JH_PLATFORM_MEGA] [report] [success] 主机状态上报正常',
      '[2026-08-05 16:08:33] [H_JH_PLATFORM_POLARIS] [collect] [warning] 备用机插件离线或 SSH 采集失败',
      '[2026-08-05 16:08:33] [system] [warning] 当前主机在线，备用机离线'
    ].join('\n')
  }
];

var haCurrentSearch = '';

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

function haMockHostChecks(pair, host) {
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
    var checks = haMockHostChecks(pair, host);
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
    var nameCls = host.online === 'online' ? 'ha-host-name' : 'ha-host-name ha-host-name-offline';
    return '<div class="ha-check-host-card">' +
      '<div class="ha-check-host-head">' + dot + haRoleMark(host.role) +
        '<span class="' + nameCls + '">' + haEscape(host.name) + '</span>' +
        (index === 0 ? '<span class="ha-current-site-tag">本机房</span>' : '') +
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
      .concat(pair.hosts.map(function(host) { return host.name + ' ' + host.ip; }))
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
    '<div class="c6 mb10">选择要切换为主机的目标主机。本阶段仅模拟创建切换任务。</div>' +
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
    btn: ['确认发起模拟切换', '取消'],
    success: function() {
      haToggleSyncOptions();
    },
    yes: function(index) {
      var selectedHostId = $('[name=haSwitchTargetHost]:checked').val();
      target = haFindHost(pair, selectedHostId) || target;
      pair.status = 'switching';
      pair.status_text = '下线中';
      pair.desired_master_host_id = target.host_id;
      pair.switch_run_id = 'HSR_' + haBuildRunId();
      pair.log_path = 'logs/ha_switch/2026-08/' + pair.switch_run_id + '.log';
      pair.warnings = ['已创建切换任务，等待旧主机执行下线流程'];
      pair.log = '[2026-08-05 16:10:00] [system] [pending] 创建切换任务 ' + pair.switch_run_id + '\n' +
        '[2026-08-05 16:10:01] [system] [running] 等待旧主机插件领取 offline 阶段';
      layer.close(index);
      haRenderList(haCurrentSearch);
      layer.msg('UI 预览：已创建模拟切换任务', {icon: 1});
    }
  });
}

function haBuildRunId() {
  var d = new Date();
  var pad = function(n) { return n < 10 ? '0' + n : '' + n; };
  return d.getFullYear() + pad(d.getMonth() + 1) + pad(d.getDate()) + pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds()) + '_' + Math.random().toString(16).slice(2, 6);
}

function haOpenDetailDialog(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  var tabs = [
    {title: '组别概览', tab: 'summary'},
    {title: '主机列表', tab: 'hosts'},
    {title: '自检状态', tab: 'health'},
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
        return '<tr><td>' + haEscape(host.name) + '</td><td>' + haEscape(host.ip) + '</td><td>' + haRoleMark(host.role) + haEscape(host.role) + '</td><td>' + (host.online === 'online' ? '<span class="ha-online">在线</span>' : '<span class="ha-offline">离线</span>') + '</td></tr>';
      }).join('') +
    '</tbody></table>' +
    '<div class="ha-muted">后续接入真实 API 后，可在这里扩展主机 ID、插件版本、最近心跳、实际角色来源等信息。</div>' +
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
  var html = '<div class="pd15">' +
    '<div class="ha-muted mb10">日志文件: ' + haEscape(pair.log_path) + '</div>' +
    '<div class="ha-log-box">' + haEscape(pair.log || '暂无日志') + '</div>' +
    '</div>';
  layer.open({
    type: 1,
    title: '切换日志 - ' + pair.switch_run_id,
    area: ['820px', '520px'],
    content: html,
    btn: ['模拟追加日志', '关闭'],
    yes: function() {
      pair.log += '\n[2026-08-05 16:10:15] [mock] [running] UI 预览追加日志，后续由插件 API 写入';
      $('.ha-log-box').text(pair.log);
      var box = $('.ha-log-box')[0];
      if (box) box.scrollTop = box.scrollHeight;
    }
  });
}

function haRefreshMock() {
  layer.msg('UI 预览：已刷新模拟状态', {icon: 1});
  haRenderList(haCurrentSearch);
}

$(function() {
  setTimeout(function() {
    haRenderList('');
  }, 200);
});
