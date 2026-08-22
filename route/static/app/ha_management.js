var haPairs = [];
var haCurrentSearch = '';
var haSwitchDialogIndex = null;
var haSwitchLogLayerIndex = null;
var haSwitchLogTimer = null;
var haSwitchLogHeartbeatTimer = null;
var haSwitchLogHeartbeat = 0;
var haSwitchLiveBaseText = '';
var haSwitchWizard = {step: 1, pairId: '', targetHostId: '', options: null, prepared: false, prepareRunId: '', prepareLog: '', prepareStatus: ''};
var haLogPager = {};
var haRefreshTimer = null;
var haRefreshInterval = 60000;
var haHealthRefreshTimer = null;
var haHealthRefreshLoading = false;
var haHealthRefreshInterval = 3000;
var haSortSaving = false;
var haSortResumeRefresh = false;
var haSortDragContext = null;
var haStatusTipIndex = null;
var haStatusTipCloseTimer = null;

function haApi(action, data, callback, options) {
  options = options || {};
  $.post('/ha/' + action, data || {}, function(res) {
    if (typeof res === 'string') {
      try { res = JSON.parse(res); } catch (e) { res = {status: false, msg: res}; }
    }
    if (!res || !res.status) {
      if (!options.quiet) layer.msg((res && res.msg) || 'HA接口请求失败', {icon: 2});
      if (callback) callback(null, res || {});
      return;
    }
    if (callback) callback(res.data || {}, res);
  }, 'json').fail(function() {
    if (!options.quiet) layer.msg('HA接口连接失败', {icon: 2});
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
  if (!pair || !hostId) return null;
  var hosts = pair.hosts || [];
  for (var i = 0; i < hosts.length; i++) {
    var aliasIds = hosts[i].host_alias_ids || [];
    if (hosts[i].host_id === hostId || aliasIds.indexOf(hostId) !== -1) return hosts[i];
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

function haPairLogPager(pairId) {
  if (!haLogPager[pairId]) haLogPager[pairId] = {page: 1, page_size: 20, loading: false};
  return haLogPager[pairId];
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

function canDragSortHaList() {
  return normalizeText(haCurrentSearch).trim() === '';
}

function updateHaSortHandleState(enabled, title) {
  var handleTitle = title || (enabled ? '拖动排序' : '仅完整列表支持拖动排序');
  $('#haPairBody .ha-sort-handle').toggleClass('disabled', !enabled).attr('title', handleTitle);
}

function getHaSortRowIds() {
  return $('#haPairBody tr').map(function() {
    return $(this).attr('data-ha-row-id');
  }).get().filter(function(item) {
    return !!item;
  });
}

function isSameHaSortRowOrder(beforeRows, afterRows) {
  if (!beforeRows || !afterRows || beforeRows.length !== afterRows.length) return false;
  for (var i = 0; i < beforeRows.length; i++) {
    if (beforeRows[i] !== afterRows[i]) return false;
  }
  return true;
}

function createHaSortPlaceholder(row) {
  var columnCount = row.children().length || 1;
  var height = Math.max(row.outerHeight() - 8, 24);
  return $("<tr class='ha-sort-placeholder'><td colspan='" + columnCount + "'><div class='ha-sort-placeholder-inner' style='height:" + height + "px'></div></td></tr>");
}

function createHaSortPreviewTable(row) {
  var preview = $("<div class='ha-sort-drag-preview'></div>");
  var table = $("<table class='table table-hover ha-table'></table>");
  var tbody = $('<tbody></tbody>');
  row.children().each(function() {
    $(this).width($(this).outerWidth());
  });
  tbody.append(row);
  table.append(tbody);
  preview.append(table);
  $('body').append(preview);
  return preview;
}

function moveHaSortPreview(pageX, pageY) {
  if (!haSortDragContext || !haSortDragContext.preview) return;
  haSortDragContext.preview.css({
    left: pageX - haSortDragContext.pointerOffsetLeft,
    top: pageY - haSortDragContext.pointerOffsetTop
  });
}

function updateHaSortPlaceholderPosition(pageY) {
  if (!haSortDragContext || !haSortDragContext.placeholder) return;
  var body = haSortDragContext.body;
  var placeholder = haSortDragContext.placeholder;
  var inserted = false;
  body.children('tr').not(placeholder).each(function() {
    var currentRow = $(this);
    var middleY = currentRow.offset().top + (currentRow.outerHeight() / 2);
    if (pageY < middleY) {
      currentRow.before(placeholder);
      inserted = true;
      return false;
    }
  });
  if (!inserted) body.append(placeholder);
}

function updateHaSortAutoScroll(pageY) {
  if (!haSortDragContext || !haSortDragContext.scrollContainer) return;
  var scrollContainer = haSortDragContext.scrollContainer;
  if (!scrollContainer.length) return;
  var offset = scrollContainer.offset();
  if (!offset) return;
  var threshold = 48;
  var topEdge = offset.top;
  var bottomEdge = topEdge + scrollContainer.outerHeight();
  var delta = 0;
  if (pageY < topEdge + threshold) {
    delta = -Math.max(6, Math.ceil((topEdge + threshold - pageY) / 4));
  } else if (pageY > bottomEdge - threshold) {
    delta = Math.max(6, Math.ceil((pageY - (bottomEdge - threshold)) / 4));
  }
  if (delta !== 0) scrollContainer.scrollTop(scrollContainer.scrollTop() + delta);
}

function cleanupHaSortDragContext() {
  if (!haSortDragContext) return;
  if (haSortDragContext.preview) haSortDragContext.preview.remove();
  $(document).off('.haSortDrag');
  $('body').removeClass('host-sort-dragging');
  haSortDragContext = null;
}

function startHaSortDrag(event, row) {
  var draggedRow = $(row);
  var body = $('#haPairBody');
  var placeholder = createHaSortPlaceholder(draggedRow);
  haSortDragContext = {
    started: true,
    body: body,
    dragRow: draggedRow,
    placeholder: placeholder,
    preview: null,
    scrollContainer: body.closest('.tablescroll'),
    initialOrder: getHaSortRowIds(),
    pointerOffsetLeft: event.pageX - draggedRow.offset().left,
    pointerOffsetTop: event.pageY - draggedRow.offset().top
  };
  draggedRow.before(placeholder);
  haSortDragContext.preview = createHaSortPreviewTable(draggedRow);
  moveHaSortPreview(event.pageX, event.pageY);
  updateHaSortPlaceholderPosition(event.pageY);
  $('body').addClass('host-sort-dragging');
  haSortResumeRefresh = !!haRefreshTimer;
  if (haSortResumeRefresh) haStopAutoRefresh();
}

function finishHaSortDrag() {
  if (!haSortDragContext || !haSortDragContext.started) {
    cleanupHaSortDragContext();
    return false;
  }
  var placeholder = haSortDragContext.placeholder;
  var draggedRow = haSortDragContext.dragRow;
  var beforeOrder = haSortDragContext.initialOrder || [];
  if (placeholder && placeholder.length) {
    placeholder.before(draggedRow);
    placeholder.remove();
  }
  var afterOrder = getHaSortRowIds();
  cleanupHaSortDragContext();
  if (!isSameHaSortRowOrder(beforeOrder, afterOrder)) {
    saveHaListSort();
    return true;
  }
  if (haSortResumeRefresh && !haSortSaving) {
    haSortResumeRefresh = false;
    haStartAutoRefresh();
  }
  return false;
}

function bindHaSortPointerEvents() {
  $('#haPairBody').off('mousedown.haSort', '.ha-sort-handle').on('mousedown.haSort', '.ha-sort-handle', function(event) {
    if ($(this).hasClass('disabled')) return false;
    if (event.which !== 1) return true;
    event.preventDefault();
    var draggedRow = $(this).closest('tr');
    var startX = event.pageX;
    var startY = event.pageY;
    var dragStarted = false;
    $(document).off('.haSortDrag')
      .on('mousemove.haSortDrag', function(moveEvent) {
        if (!dragStarted) {
          var diffX = Math.abs(moveEvent.pageX - startX);
          var diffY = Math.abs(moveEvent.pageY - startY);
          if (Math.max(diffX, diffY) < 4) return;
          dragStarted = true;
          startHaSortDrag(event, draggedRow);
        }
        if (!haSortDragContext || !haSortDragContext.started) return;
        moveHaSortPreview(moveEvent.pageX, moveEvent.pageY);
        updateHaSortAutoScroll(moveEvent.pageY);
        updateHaSortPlaceholderPosition(moveEvent.pageY);
      })
      .on('mouseup.haSortDrag', function() {
        if (dragStarted) {
          finishHaSortDrag();
          return;
        }
        $(document).off('.haSortDrag');
      });
    return false;
  });
}

function saveHaListSort() {
  if (!canDragSortHaList()) return;
  var rowIds = getHaSortRowIds();
  if (rowIds.length <= 1) {
    if (haSortResumeRefresh) {
      haSortResumeRefresh = false;
      haStartAutoRefresh();
    }
    return;
  }
  haSortSaving = true;
  var sortLoading = layer.msg('正在保存排序!', {icon: 16, time: 0, shade: [0.3, '#000']});
  $.post('/ha/save_list_sort', {row_ids: rowIds}, function(res) {
    if (typeof res === 'string') {
      try { res = JSON.parse(res); } catch (e) { res = {status: false, msg: res}; }
    }
    layer.close(sortLoading);
    layer.msg((res && res.msg) || '排序保存完成', {icon: res && res.status ? 1 : 2});
    if (res && res.status) haLoadPairs();
  }, 'json').fail(function() {
    layer.close(sortLoading);
    layer.msg('排序保存失败!', {icon: 2});
  }).always(function() {
    haSortSaving = false;
    if (haSortResumeRefresh) {
      haSortResumeRefresh = false;
      haStartAutoRefresh();
    }
  });
}

function initHaDragSort() {
  cleanupHaSortDragContext();
  bindHaSortPointerEvents();
  if (!canDragSortHaList()) {
    updateHaSortHandleState(false, '搜索结果不支持拖动排序，请清空搜索后排序');
    return;
  }
  if ($('#haPairBody tr').length <= 1) {
    updateHaSortHandleState(false, '至少需要两条主备关系才能拖动排序');
    return;
  }
  updateHaSortHandleState(true, '拖动排序');
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
    '<div class="ha-log-toolbar">' +
      '<div><div class="monitor-task-section-title">自检状态</div><div class="ha-muted">展示 ha_manager 插件上报的真实自检明细；缺失明细时显示摘要或等待上报。</div></div>' +
      '<button type="button" id="haHealthRefreshBtn" class="btn btn-default btn-sm" onclick="haRefreshHealthPage(\'' + haAttr(pair.pair_id) + '\')">刷新</button>' +
    '</div>' +
    '<div class="ha-check-grid">' + hostCards + '</div>' +
    '</div>';
}

function haRefreshHealthPage(pairId, silent) {
  if (haHealthRefreshLoading) return;
  haHealthRefreshLoading = true;
  if (!silent) $('#haHealthRefreshBtn').prop('disabled', true).text('刷新中');
  haApi('get_detail', {pair_id: pairId}, function(data) {
    haHealthRefreshLoading = false;
    if (!silent) $('#haHealthRefreshBtn').prop('disabled', false).text('刷新');
    if (!data) return;
    haStorePair(data);
    haRenderDetailTab(pairId, 'health', null, true);
  }, {quiet: true});
}

function haStartHealthAutoRefresh(pairId) {
  haStopHealthAutoRefresh();
  haHealthRefreshTimer = setInterval(function() {
    haRefreshHealthPage(pairId, true);
  }, haHealthRefreshInterval);
}

function haStopHealthAutoRefresh() {
  if (haHealthRefreshTimer) {
    clearInterval(haHealthRefreshTimer);
    haHealthRefreshTimer = null;
  }
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

function haFailoverMark(host) {
  var failover = host.failover || {};
  if (failover.recovery_status === 'recovery_guard') return '<span class="ha-status-pill ha-pill-warning">恢复保护</span>';
  if (failover.mode === 'degraded_master' || failover.pending_switch_required) return '<span class="ha-status-pill ha-pill-warning">降级运行</span>';
  if (failover.recovery_status === 'recovering_standby') return '<span class="ha-status-pill ha-pill-switching">恢复中</span>';
  return '';
}

function haFailoverStatusText(failover) {
  failover = failover || {};
  if (failover.recovery_status === 'recovery_guard') return '恢复保护';
  if (failover.recovery_status === 'recovering_standby') return '恢复中';
  if (failover.recovery_status === 'recovered') return '已恢复';
  if (failover.mode === 'degraded_master' || failover.pending_switch_required) return '降级运行';
  return '';
}

function haPendingSwitchTargetText(pair, failover) {
  failover = failover || {};
  var hostId = failover.pending_switch_host_id || '';
  if (!hostId) return '对端';
  var host = haFindHost(pair, hostId) || {};
  return host.name || host.ip || hostId;
}

function haPairFailoverSummary(pair) {
  var rows = [];
  (pair.hosts || []).forEach(function(host) {
    var failover = host.failover || {};
    var statusText = haFailoverStatusText(failover);
    if (statusText && statusText !== '已恢复') {
      var text = (host.name || host.host_id || '--') + ': ' + statusText;
      if (failover.recovery_status === 'recovery_guard') {
        text += '，待恢复为备机';
      } else if (failover.pending_switch_required || failover.pending_switch_host_id) {
        text += '，待 ' + haPendingSwitchTargetText(pair, failover) + ' 切换为 ' + (failover.pending_switch_role || '备机');
      }
      rows.push(text);
    }
  });
  return rows.join('；');
}

function haDetailHostCard(pair, host, index) {
  var isMaster = host.role === 'master';
  var currentMark = haIsCurrentDatacenterHost(pair, host, index) ? '<span class="ha-current-site-tag">本机房</span>' : '';
  var roleText = isMaster ? '当前主机' : (host.role === 'standby' ? '当前备机' : '角色未知');
  var cls = isMaster ? 'ha-detail-host-card is-master' : 'ha-detail-host-card';
  return '<div class="' + cls + '">' +
    '<div class="ha-detail-host-top">' +
      '<div class="ha-detail-host-title">' + haHostStatusDot(pair, host) + haRoleMark(host.role) + '<span title="' + haAttr(host.name) + '">' + haEscape(host.name) + '</span>' + haFailoverMark(host) + '</div>' +
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
  if (status === 'success' || status === 'done' || status === 'prepare_success' || status.indexOf('_done') !== -1) return 'success';
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

function haStatusTone(status) {
  if (status === 'normal' || status === 'success' || status === 'online') return 'ok';
  if (status === 'warning' || status === 'switching' || status === 'running') return 'warning';
  if (status === 'danger' || status === 'failed' || status === 'offline' || status === 'error') return 'danger';
  return 'muted';
}

function haCheckTone(status) {
  var normalized = haCheckStatus(status);
  if (normalized === 'ok') return 'ok';
  if (normalized === 'failed') return 'danger';
  return 'muted';
}

function haStatusTipRow(label, value, tone) {
  tone = tone || 'muted';
  return '<div class="ha-status-tip-row is-' + haAttr(tone) + '"><span class="ha-status-tip-label">' + haEscape(label) + '</span><span class="ha-status-tip-value">' + haEscape(value || '--') + '</span></div>';
}

function haStatusTipCheckVisible(item) {
  var text = [item.group, item.name, item.key, item.actual, item.message].join(' ').toLowerCase();
  return text.indexOf('openresty') === -1 && text.indexOf('web 服务') === -1;
}

function haStatusIssueTooltipHtml(pair) {
  pair = pair || {};
  var actualMaster = haFindHost(pair, pair.actual_master_host_id) || {};
  var desiredMaster = haFindHost(pair, pair.desired_master_host_id) || {};
  var html = '<div class="ha-status-tip-simple">';
  var statusTone = haStatusTone(pair.status);
  html += haStatusTipRow('当前状态', haStatusLabel(pair.status), statusTone);
  html += haStatusTipRow('状态说明', pair.status_text || '--', statusTone === 'ok' ? 'muted' : statusTone);
  html += haStatusTipRow('实际主机', (actualMaster.name || '--') + ' / ' + (actualMaster.ip || '--'), 'muted');
  html += haStatusTipRow('期望主机', (desiredMaster.name || '--') + ' / ' + (desiredMaster.ip || '--'), pair.desired_master_host_id && pair.actual_master_host_id && pair.desired_master_host_id !== pair.actual_master_host_id ? 'warning' : 'muted');
  (pair.hosts || []).forEach(function(host, index) {
    var hostName = host.name || host.host_id || ('主机' + (index + 1));
    var failedChecks = haNormalizeChecks(host).filter(function(item) {
      return haCheckStatus(item.status) === 'failed' && haStatusTipCheckVisible(item);
    });
    failedChecks.slice(0, 8).forEach(function(item) {
      var value = (item.actual || item.message || '异常') + (item.expected ? '，期望' + item.expected : '');
      html += haStatusTipRow(hostName + ' / ' + (item.name || '自检项'), value, haCheckTone(item.status));
    });
    if (failedChecks.length > 8) {
      html += haStatusTipRow(hostName + ' / 更多', '其余 ' + (failedChecks.length - 8) + ' 项请查看详情自检状态', 'warning');
    }
  });
  html += '</div>';
  return html;
}

function haBindStatusTooltip() {
  $('#haPairBody').off('mouseenter.haStatusTip mouseleave.haStatusTip', '.ha-status-tip-target');
  $('#haPairBody').on('mouseenter.haStatusTip', '.ha-status-tip-target', function() {
    var that = this;
    if (haStatusTipCloseTimer) {
      clearTimeout(haStatusTipCloseTimer);
      haStatusTipCloseTimer = null;
    }
    if (haStatusTipIndex) layer.close(haStatusTipIndex);
    var pair = haFindPair($(that).attr('data-ha-pair-id') || '');
    if (!pair) return;
    haStatusTipIndex = layer.tips(haStatusIssueTooltipHtml(pair), that, {time: 0, tips: [1, '#fff'], maxWidth: 560});
    var tipElem = $('#layui-layer' + haStatusTipIndex);
    tipElem.addClass('ha-status-tip-layer');
    tipElem.off('mouseenter.haStatusTip mouseleave.haStatusTip');
    tipElem.on('mouseenter.haStatusTip', function() {
      if (haStatusTipCloseTimer) {
        clearTimeout(haStatusTipCloseTimer);
        haStatusTipCloseTimer = null;
      }
    });
    tipElem.on('mouseleave.haStatusTip', function() {
      haStatusTipCloseTimer = setTimeout(function() {
        if (!$(that).is(':hover')) layer.closeAll('tips');
      }, 120);
    });
  }).on('mouseleave.haStatusTip', '.ha-status-tip-target', function() {
    var that = this;
    haStatusTipCloseTimer = setTimeout(function() {
      if (haStatusTipIndex && $('#layui-layer' + haStatusTipIndex).is(':hover')) return;
      if (!$(that).is(':hover')) layer.closeAll('tips');
    }, 120);
  });
}

function haRenderList(search) {
  if (typeof search !== 'undefined') haCurrentSearch = search || '';
  var keyword = normalizeText(haCurrentSearch).toLowerCase();
  var rows = haPairs.slice().filter(function(pair) {
    if (!keyword) return true;
    var haystack = [pair.pair_name, pair.pair_id, pair.status_text]
      .concat(pair.hosts.map(function(host) { return host.name + ' ' + host.host_id + ' ' + host.ip; }))
      .join(' ').toLowerCase();
    return haystack.indexOf(keyword) !== -1;
  });
  if (rows.length === 0) {
    $('#haPairBody').html('');
    $('#haEmptyState').show();
    initHaDragSort();
    return;
  }
  $('#haEmptyState').hide();
  var html = '';
  rows.forEach(function(pair) {
    var failoverSummary = haPairFailoverSummary(pair);
    var latestAlert = pair.latest_alert_event || {};
    var latestAlertRecovered = latestAlert.event_type === 'ha_alert_recovery' && latestAlert.status === 'sent';
    var alertExtra = latestAlert.title ? '<div class="ha-sub"><span class="ha-status-pill ' + (latestAlertRecovered ? 'ha-pill-normal' : 'ha-pill-warning') + '" title="' + haAttr(latestAlertRecovered ? '异常已恢复' : (latestAlert.message || latestAlert.title)) + '">' + (latestAlertRecovered ? '恢复' : '通知') + '</span> ' + haEscape(latestAlertRecovered ? '异常已恢复' : latestAlert.title) + ' <span class="c9">' + haEscape(latestAlert.addtime || '') + '</span></div>' : '';
    var pairNameExtra = (failoverSummary ? '<div class="ha-sub"><span class="ha-status-pill ha-pill-warning" title="' + haAttr(failoverSummary) + '">故障恢复</span> ' + haEscape(failoverSummary) + '</div>' : '') + alertExtra;
    html += '<tr data-ha-row-id="' + haAttr(pair.id) + '">' +
      '<td class="text-center"><span class="ha-sort-handle" aria-hidden="true" title="拖动排序"><i></i><i></i><i></i></span></td>' +
      '<td><div class="ha-main">' + haEscape(pair.pair_name) + '</div><div class="ha-sub">' + haEscape(pair.pair_id) + '</div>' + pairNameExtra + '</td>' +
      '<td>' + haHostsCell(pair) + '</td>' +
      '<td class="text-center"><div class="ha-status-tip-target" data-ha-pair-id="' + haAttr(pair.pair_id) + '"><div class="ha-status-line"><span class="ha-status-pill ' + haStatusClass(pair.status) + '">' + haStatusLabel(pair.status) + '</span></div><div class="ha-status-desc">' + haEscape(pair.status_text || '') + '</div></div></td>' +
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
  haBindStatusTooltip();
  initHaDragSort();
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
  return haSwitchWizardSteps() + '<div class="ha-wizard-body">' + haSwitchWizardHostSelect(pair) + '</div>';
}

function haToggleSyncOptions() {
  var root = haSwitchWizardRoot().length ? haSwitchWizardRoot() : $(document);
  var checked = root.find('input[type="checkbox"][name="sync_files"]').last().prop('checked') === true;
  root.find('.ha-sync-options').toggle(checked);
}

function haOpenSwitchDialog(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  var target = pair.hosts[0].host_id === pair.actual_master_host_id ? pair.hosts[1] : pair.hosts[0];
  haSwitchWizard = {step: 1, pairId: pair.pair_id, targetHostId: target.host_id, options: $.extend(true, {}, haDefaultSwitchOptions()), prepared: false, prepareRunId: '', prepareLog: '', prepareStatus: ''};
  haSwitchDialogIndex = layer.open({
    type: 1,
    title: haSwitchDialogTitle(pair),
    area: ['780px', '560px'],
    closeBtn: 1,
    shadeClose: false,
    content: '<div id="haSwitchWizardBox" class="ha-switch-wizard"></div>',
    success: function() {
      haRenderSwitchWizard();
    },
    end: function() {
      haSwitchDialogIndex = null;
    },
  });
}

function haDefaultSwitchOptions() {
  return {
    local_ip: '',
    remote_ip: '',
    remote_ssh_port: '22',
    run_checksum: true,
    sync_files: true,
    sync_file_dirs: '/www/wwwroot,/www/wwwstorage',
    sync_ignore_dirs: '.git,node_modules,logs,run',
    restore_site_setting: false,
    restore_plugin_setting: false,
    run_xtrabackup_inc_restore: false,
    promote_mysql: true,
    checksum_confirmed: false
  };
}

function haSwitchWizardRoot() {
  return haSwitchDialogIndex ? $('#layui-layer' + haSwitchDialogIndex).find('#haSwitchWizardBox') : $('#haSwitchWizardBox');
}

function haSwitchDialogTitle(pair) {
  pair = pair || haFindPair(haSwitchWizard.pairId) || {};
  var target = haFindHost(pair, haSwitchWizard.targetHostId) || {};
  var targetText = target.name || target.ip || target.host_id || '未选择主机';
  return '切换主备 - 切换到 ' + targetText;
}

function haUpdateSwitchDialogTitle(pair) {
  if (haSwitchDialogIndex === null) return;
  $('#layui-layer' + haSwitchDialogIndex).find('.layui-layer-title').text(haSwitchDialogTitle(pair));
}

function haSwitchWizardSteps() {
  var items = [{num: 1, text: '选择主机'}, {num: 2, text: '预上线'}, {num: 3, text: '正式切换'}];
  return '<div class="ha-wizard-steps">' + items.map(function(item) {
    var cls = item.num === haSwitchWizard.step ? 'active' : item.num < haSwitchWizard.step ? 'done' : '';
    return '<div class="ha-wizard-step ' + cls + '"><span class="ha-wizard-step-num">' + item.num + '</span>' + item.text + '</div>';
  }).join('') + '</div>';
}

function haSwitchWizardHostSelect(pair) {
  return '<div class="ha-switch-hosts">' + pair.hosts.map(function(host, index) {
    var checked = host.host_id === haSwitchWizard.targetHostId ? 'checked' : '';
    var roleText = haRoleMark(host.role);
    var siteTag = haIsCurrentDatacenterHost(pair, host, index) ? '<span class="ha-current-site-tag">本机房</span>' : '';
    var failoverMark = haFailoverMark(host);
    return '<label class="ha-switch-host"><input type="radio" name="haSwitchTargetHost" value="' + haAttr(host.host_id) + '" onchange="haSwitchTargetChanged(this.value)" ' + checked + '>' +
      '<span class="ha-switch-host-title"><span class="ha-switch-host-name">' + haEscape(host.name) + '</span>' + siteTag + failoverMark + '</span>' +
      '<div class="ha-switch-host-meta">当前角色: ' + roleText + ' <span class="ml10">IP: ' + haEscape(host.ip || '--') + '</span></div>' +
    '</label>';
  }).join('') + '</div>';
}

function haSwitchTargetChanged(hostId) {
  haSwitchWizard.targetHostId = hostId || '';
  haUpdateSwitchDialogTitle();
  haRenderSwitchWizard();
}

function haCanSkipSwitch(pair, target) {
  var masters = (pair.hosts || []).filter(function(host) { return host.role === 'master'; });
  return masters.length === 1 && target && target.host_id === masters[0].host_id && pair.status === 'normal';
}

function haBuildSwitchOptionsForm(o) {
  o = o || haDefaultSwitchOptions();
  return '<form class="bt-form ha-form" id="haLocalSwitchForm">' +
    '<div class="ha-switch-options"><div class="ha-switch-options-title">预上线选项</div>' +
      '<div class="ha-option-grid">' +
        '<label class="ha-option-check"><input type="checkbox" name="sync_files" onchange="haToggleSyncOptions()" ' + (o.sync_files ? 'checked' : '') + '><span>同步文件</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" name="run_checksum" ' + (o.run_checksum ? 'checked' : '') + '><span>检查 checksum</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" name="restore_site_setting" ' + (o.restore_site_setting ? 'checked' : '') + '><span>恢复网站配置</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" name="restore_plugin_setting" ' + (o.restore_plugin_setting ? 'checked' : '') + '><span>面板插件配置</span></label>' +
        '<label class="ha-option-check"><input type="checkbox" name="run_xtrabackup_inc_restore" ' + (o.run_xtrabackup_inc_restore ? 'checked' : '') + '><span>执行增量恢复</span></label>' +
      '</div>' +
      '<div class="ha-sync-options ha-sync-group">' +
        '<div class="ha-sync-field"><span>同步目录</span><input class="bt-input-text" type="text" name="sync_file_dirs" value="' + haEscape(o.sync_file_dirs) + '" /></div>' +
        '<div class="ha-sync-field"><span>忽略目录</span><input class="bt-input-text" type="text" name="sync_ignore_dirs" value="' + haEscape(o.sync_ignore_dirs) + '" /></div>' +
      '</div>' +
    '</div>' +
    '</form>';
}

function haSwitchWizardRiskTip() {
  return '<div class="ha-switch-risk-tip"><span>提示：</span>为减少服务中断时间，请确保程序（JianghuJS、Docker）和配置正确后执行上线操作。</div>';
}

function haBuildSwitchWizardBody(pair) {
  var pairHosts = pair.hosts || [];
  if (haSwitchWizard.step === 1) {
    var target = haFindHost(pair, haSwitchWizard.targetHostId) || pairHosts[0] || {};
    return '<div class="c6 mb10">选择切换完成后作为主机的机器。</div>' + haSwitchWizardHostSelect(pair) +
      '<div class="ms-sub mt10">当前目标: ' + haEscape(target.name || '--') + ' / ' + haEscape(target.ip || '--') + '</div>';
  }
  if (haSwitchWizard.step === 2) {
    return '<div class="c6 mb10">选择预上线要执行的检查和同步动作。</div>' + haBuildSwitchOptionsForm(haSwitchWizard.options);
  }
  return haBuildPrepareResultContent(haSwitchWizard.prepareRunId, haSwitchWizard.prepareLog, haSwitchWizard.prepareStatus === 'success');
}

function haRenderSwitchWizard() {
  var root = haSwitchWizardRoot();
  if (!root.length) return;
  var pair = haFindPair(haSwitchWizard.pairId);
  if (!pair) return;
  var actions = '';
  if (haSwitchWizard.step === 1) {
    actions = '<button type="button" class="btn btn-success btn-sm" onclick="haWizardGoOptions()">下一步</button>';
  } else if (haSwitchWizard.step === 2) {
    actions = '<button type="button" class="btn btn-default btn-sm" onclick="haWizardBackHost()">上一步</button><button type="button" class="btn btn-success btn-sm" onclick="haWizardRunPrepare()">开始预上线</button>';
  } else {
    actions = '<button type="button" class="btn btn-default btn-sm" onclick="haWizardBackOptions()">返回预上线选项</button>' + (haSwitchWizard.prepareStatus === 'success' ? '<button type="button" class="btn btn-success btn-sm" onclick="haStartFinalizeFromWizard()">正式切换</button>' : '');
  }
  haUpdateSwitchDialogTitle(pair);
  root.html(haSwitchWizardSteps() + '<div class="ha-wizard-body">' + haBuildSwitchWizardBody(pair) + '</div><div class="ha-wizard-actions">' + actions + '</div>');
  haToggleSyncOptions();
}

function haWizardGoOptions() {
  var pair = haFindPair(haSwitchWizard.pairId);
  if (!pair) return;
  var selectedHostId = haSwitchWizardRoot().find('[name=haSwitchTargetHost]:checked').val();
  var target = haFindHost(pair, selectedHostId);
  if (!target) return layer.msg('请选择切换后的主机', {icon: 2});
  if (haCanSkipSwitch(pair, target)) return layer.msg('当前主备关系已符合选择，无需切换', {icon: 0});
  haSwitchWizard.targetHostId = target.host_id;
  haSwitchWizard.step = 2;
  haRenderSwitchWizard();
}

function haWizardBackHost() {
  haSwitchWizard.step = 1;
  haRenderSwitchWizard();
}

function haWizardBackOptions() {
  haSwitchWizard.step = 2;
  haRenderSwitchWizard();
}

function haReadSwitchOptions() {
  var root = haSwitchWizardRoot();
  var form = root.find('#haLocalSwitchForm').last();
  var data = $.extend(true, {}, haSwitchWizard.options || haDefaultSwitchOptions());
  if (!form.length) return data;
  form.serializeArray().forEach(function(item) { data[item.name] = item.value; });
  ['run_checksum','sync_files','restore_site_setting','restore_plugin_setting','run_xtrabackup_inc_restore'].forEach(function(key) {
    data[key] = form.find('input[type="checkbox"][name="' + key + '"]').prop('checked') === true;
  });
  data.allow_checksum_diff = false;
  data.checksum_confirmed = false;
  data.promote_mysql = true;
  haSwitchWizard.options = $.extend(true, {}, data);
  return data;
}

function haSwitchOptionsConfirmHtml(options) {
  options = options || haDefaultSwitchOptions();
  return '<div class="ha-switch-confirm-options">' +
    '<div>同步文件：<b>' + (options.sync_files ? '是' : '否') + '</b></div>' +
    '<div>检查 checksum：<b>' + (options.run_checksum ? '是' : '否') + '</b></div>' +
    '<div>执行增量恢复：<b>' + (options.run_xtrabackup_inc_restore ? '是' : '否') + '</b></div>' +
    '<div>同步目录：' + haEscape(options.sync_file_dirs || '--') + '</div>' +
    '<div>忽略目录：' + haEscape(options.sync_ignore_dirs || '--') + '</div>' +
  '</div>';
}

function haWizardRunPrepare() {
  var pair = haFindPair(haSwitchWizard.pairId);
  var target = pair ? haFindHost(pair, haSwitchWizard.targetHostId) : null;
  if (!pair || !target) return layer.msg('目标主机不存在', {icon: 2});
  var options = haReadSwitchOptions();
  var content = haSwitchWizardRiskTip() + '<div>确认在目标主机（' + haEscape(target.name || target.ip || target.host_id) + '）执行预备上线？</div>' + haSwitchOptionsConfirmHtml(options);
  layer.confirm(content, {icon: 3, title: '确认预备上线', btn: ['确认执行', '取消']}, function(confirmIndex) {
    layer.close(confirmIndex);
    options.confirm_failover = true;
    haCreateSwitchTask(pair, target, options, 'prepare');
  });
}

function haStartFinalizeFromWizard() {
  var pair = haFindPair(haSwitchWizard.pairId);
  var target = pair ? haFindHost(pair, haSwitchWizard.targetHostId) : null;
  if (!pair || !target) return layer.msg('目标主机不存在', {icon: 2});
  var options = $.extend(true, {}, haSwitchWizard.options || haDefaultSwitchOptions());
  var content = haSwitchWizardRiskTip() + '<div>确认执行正式上线并切换主备？<br>将执行旧主机下线和目标主机（' + haEscape(target.name || target.ip || target.host_id) + '）正式上线流程。</div>';
  layer.confirm(content, {icon: 3, title: '确认正式上线', btn: ['确认执行', '取消']}, function(confirmIndex) {
    layer.close(confirmIndex);
    if (haSwitchDialogIndex) {
      layer.close(haSwitchDialogIndex);
      haSwitchDialogIndex = null;
    }
    options.confirm_failover = true;
    haCreateSwitchTask(pair, target, options, 'finalize');
  });
}

function haCreateSwitchTask(pair, target, options, action) {
  var payload = $.extend(true, {}, options || {});
  payload.pair_id = pair.pair_id;
  payload.target_host_id = target.host_id;
  payload.action = action;
  haApi('request_switch', payload, function(data) {
    if (!data) return;
    if (action === 'prepare') {
      haSwitchWizard.prepareRunId = data.switch_run_id;
      haSwitchWizard.prepareStatus = 'running';
      haSwitchWizard.prepareLog = '预上线任务已创建，等待目标插件领取执行...';
      haSwitchWizard.step = 3;
      haRenderSwitchWizard();
      haShowSwitchLogWindow('正在执行预备上线...', data.switch_run_id, true);
      return;
    }
    haShowSwitchLogWindow('正在执行正式上线...', data.switch_run_id, false);
    layer.msg('正式上线任务已创建', {icon: 1});
    haLoadPairs();
  });
}

function haStopSwitchLogPolling() {
  if (haSwitchLogTimer) {
    clearInterval(haSwitchLogTimer);
    haSwitchLogTimer = null;
  }
  if (haSwitchLogHeartbeatTimer) {
    clearInterval(haSwitchLogHeartbeatTimer);
    haSwitchLogHeartbeatTimer = null;
  }
}

function haCloseSwitchLogWindow() {
  if (haSwitchLogLayerIndex !== null) {
    var index = haSwitchLogLayerIndex;
    haSwitchLogLayerIndex = null;
    layer.close(index);
  }
  var liveLayer = $('#haSwitchLiveLog').closest('.layui-layer');
  if (liveLayer.length) {
    var layerId = liveLayer.attr('id') || '';
    var layerIndex = parseInt(layerId.replace('layui-layer', ''), 10);
    if (!isNaN(layerIndex)) layer.close(layerIndex);
  }
}

function haUpdateSwitchLogWindow(logText, stateText, stateClass) {
  haSwitchLiveBaseText = logText || '正在准备切换任务...';
  var displayText = haSwitchLiveBaseText;
  if (stateClass === 'ha-live-state-running') {
    displayText += haSwitchLogHeartbeatText();
  }
  $('#haSwitchLiveLog').text(displayText);
  $('#haSwitchLiveState').removeClass('ha-live-state-running ha-live-state-success ha-live-state-failed').addClass(stateClass || 'ha-live-state-running').text(stateText || '执行中');
  var box = document.getElementById('haSwitchLiveLog');
  if (box) box.scrollTop = box.scrollHeight;
}

function haSwitchLogHeartbeatText() {
  return '\n\n|- 正在执行中，等待新的日志输出' + new Array(haSwitchLogHeartbeat + 1).join('.');
}

function haTickSwitchLogHeartbeat() {
  if (!$('#haSwitchLiveState').hasClass('ha-live-state-running')) return;
  haSwitchLogHeartbeat = (haSwitchLogHeartbeat + 1) % 4;
  $('#haSwitchLiveLog').text((haSwitchLiveBaseText || '正在准备切换任务...') + haSwitchLogHeartbeatText());
  var box = document.getElementById('haSwitchLiveLog');
  if (box) box.scrollTop = box.scrollHeight;
}

function haRefreshSwitchLogWindow(switchRunId, prepareMode) {
  haApi('read_log', {switch_run_id: switchRunId, offset: 0}, function(data) {
    if (!data) return;
    var logText = data.content || '';
    var run = data.run && data.run.switch_run_id === switchRunId ? data.run : {};
    var status = run.status || '';
    var currentPhase = run.current_phase || '';
    var currentStep = run.current_step || '';
    var prepareDone = prepareMode && (status === 'prepare_success' || status === 'success' || /预上线完成|预备上线完成/.test(currentStep + '\n' + logText));
    var finalizeDone = !prepareMode && (status === 'success' || /正式上线完成/.test(currentStep + '\n' + logText));
    var done = prepareDone || finalizeDone;
    var failed = status === 'waiting_retry' || status === 'failed' || status === 'cancelled';
    var stateClass = done ? 'ha-live-state-success' : failed ? 'ha-live-state-failed' : 'ha-live-state-running';
    var stateText = done ? (prepareMode ? '预上线完成' : '正式上线完成') : failed ? '执行失败' : '执行中';
    haUpdateSwitchLogWindow(logText, stateText, stateClass);
    if (prepareMode) {
      haSwitchWizard.prepareLog = logText;
      haSwitchWizard.prepareStatus = done ? 'success' : failed ? 'failed' : 'running';
      if (haSyncPrepareWizardStatus(run, logText)) return;
    } else if (done || failed) {
      haStopSwitchLogPolling();
      if (done) {
        setTimeout(function() {
          haLoadPairs(function() {
            haConfirmJumpToHealth(switchRunId, run.pair_id || '');
          });
        }, 3000);
      } else {
        haLoadPairs();
      }
    }
    haApi('get_list', {}, function(listData) {
      if (listData && $.isArray(listData.list)) haPairs = listData.list;
    }, {quiet: true});
  });
}

function haFindPairBySwitchRunId(switchRunId, pairId) {
  for (var i = 0; i < haPairs.length; i++) {
    if (pairId && haPairs[i].pair_id === pairId) return haPairs[i];
    if (haPairs[i].switch_run_id === switchRunId || haPairs[i].current_switch_run_id === switchRunId || haPairs[i].last_switch_run_id === switchRunId) return haPairs[i];
  }
  return haPairs.length === 1 ? haPairs[0] : null;
}

function haConfirmJumpToHealth(switchRunId, pairId) {
  var pair = haFindPairBySwitchRunId(switchRunId, pairId);
  if (!pair) return;
  var jumpToHealth = function() {
    haCloseSwitchLogWindow();
    haOpenDetailDialog(pair.pair_id, 'health');
  };
  if (typeof openTimoutLayer === 'function') {
    openTimoutLayer('切换完毕，即将自动跳转自检页面', jumpToHealth, {confirmBtn: '立即跳转', cancelBtn: '取消', timeout: 3});
    return;
  }
  layer.confirm('切换完毕，是否立即查看自检页面？', {title: '提示', btn: ['立即跳转', '取消']}, function(index) {
    layer.close(index);
    jumpToHealth();
  });
}

function haShowSwitchLogWindow(title, switchRunId, prepareMode) {
  haStopSwitchLogPolling();
  haSwitchLogHeartbeat = 0;
  haSwitchLiveBaseText = '正在准备切换任务...';
  var html = '<div class="ha-live-log-wrap">' +
    '<div class="ha-live-log-head"><span id="haSwitchLiveState" class="ha-live-state ha-live-state-running">执行中</span><span class="ha-live-run-id">' + haEscape(switchRunId) + '</span></div>' +
    '<pre id="haSwitchLiveLog" class="ha-live-log-box">正在准备切换任务...</pre>' +
    '<div class="ha-live-log-tip">执行期间请勿重复发起切换；窗口关闭后仍可在“日志”页签查看。</div>' +
    '</div>';
  haSwitchLogLayerIndex = layer.open({
    title: title,
    type: 1,
    closeBtn: 2,
    shade: 0.3,
    shadeClose: false,
    area: '760px',
    offset: '20%',
    content: html,
    end: function() {
      haStopSwitchLogPolling();
      haSwitchLogLayerIndex = null;
    }
  });
  haRefreshSwitchLogWindow(switchRunId, prepareMode);
  haSwitchLogHeartbeatTimer = setInterval(haTickSwitchLogHeartbeat, 500);
  haSwitchLogTimer = setInterval(function() { haRefreshSwitchLogWindow(switchRunId, prepareMode); }, 1500);
}

function haShowSwitchReadOnlyLogWindow(title, switchRunId) {
  if (!switchRunId) return layer.msg('切换任务不存在', {icon: 2});
  haApi('read_log', {switch_run_id: switchRunId, offset: 0}, function(data) {
    if (!data) return;
    var html = '<div class="ha-live-log-wrap">' +
      '<div class="ha-live-log-head"><span class="ha-live-state ha-live-state-success">完整日志</span><span class="ha-live-run-id">' + haEscape(switchRunId) + '</span></div>' +
      '<pre class="ha-live-log-box">' + haEscape(data.content || '暂无日志') + '</pre>' +
      '<div class="ha-live-log-tip">该窗口不会自动关闭，需要手动关闭。</div>' +
      '</div>';
    layer.open({
      title: title,
      type: 1,
      closeBtn: 2,
      shade: 0.3,
      shadeClose: false,
      area: '760px',
      offset: '20%',
      content: html,
      btn: ['刷新', '关闭'],
      yes: function(index) {
        layer.close(index);
        haShowSwitchReadOnlyLogWindow(title, switchRunId);
      }
    });
  });
}

$(document).off('click', '.ha-prepare-log-link').on('click', '.ha-prepare-log-link', function() {
  var runId = $(this).data('run-id') || '';
  haShowSwitchReadOnlyLogWindow('预上线日志', runId);
});

$(document).off('click', '.ha-refresh-prepare-status').on('click', '.ha-refresh-prepare-status', function() {
  var runId = $(this).data('run-id') || '';
  if (!runId) return;
  haApi('read_log', {switch_run_id: runId, offset: 0}, function(data) {
    if (!data) return;
    if (haSyncPrepareWizardStatus(data.run || {}, data.content || '')) {
      layer.msg('已刷新预上线状态', {icon: 1});
      return;
    }
    layer.msg('当前预上线仍在执行中', {icon: 0});
  });
});

function haPrepareResultStatusMeta(status) {
  if (status === 'ok') return {text: '完成', cls: 'normal'};
  if (status === 'warning') return {text: '提醒', cls: 'warning'};
  if (status === 'failed') return {text: '失败', cls: 'danger'};
  return {text: '未执行', cls: 'info'};
}

function haSwitchResultPill(cls, text) {
  var status = cls === 'danger' ? 'danger' : cls === 'warning' ? 'warning' : cls === 'normal' ? 'normal' : 'info';
  return '<span class="ha-status-pill ' + haStatusClass(status) + '">' + haEscape(text) + '</span>';
}

function haParsePrepareResults(logText, success) {
  var names = {xtrabackup: '增量恢复', checksum: 'checksum 检查', sync: 'rsync 同步', site_setting: '恢复网站配置', plugin_setting: '面板插件配置'};
  var order = ['xtrabackup', 'checksum', 'sync', 'site_setting', 'plugin_setting'];
  var resultMap = {};
  order.forEach(function(key) { resultMap[key] = {key: key, name: names[key], status: 'skipped', detail: '未执行'}; });
  (logText || '').split('\n').forEach(function(line) {
    var idx = line.indexOf('PREPARE_RESULT ');
    if (idx === -1) return;
    var parts = line.substring(idx + 'PREPARE_RESULT '.length).trim().split(' ');
    var key = parts.shift();
    var status = parts.shift();
    if (!resultMap[key]) return;
    resultMap[key] = {key: key, name: names[key], status: status || 'ok', detail: parts.join(' ') || '执行完成'};
  });
  var rows = order.map(function(key) { return resultMap[key]; }).filter(function(item) { return item.status !== 'skipped'; });
  if (!rows.length) rows = [{key: 'prepare', name: '预备上线', status: success ? 'ok' : 'failed', detail: success ? '执行完成' : '等待执行或执行失败'}];
  return rows;
}

function haBuildPrepareResultContent(switchRunId, logText, success) {
  var rows = haParsePrepareResults(logText, success).map(function(item) {
    var meta = haPrepareResultStatusMeta(item.status);
    return '<tr><td>' + haEscape(item.name) + '</td><td>' + haSwitchResultPill(meta.cls, meta.text) + '</td><td>' + haEscape(item.detail) + '</td></tr>';
  }).join('');
  return '<div><div class="ha-muted mb10">Run ID: ' + haEscape(switchRunId || '') + '</div>' +
    '<table class="table table-hover ha-detail-data-table"><thead><tr><th>流程</th><th style="width:90px">结果</th><th>说明</th></tr></thead><tbody>' + rows + '</tbody></table>' +
    '<div class="mt10"><a class="btlink ha-prepare-log-link" href="javascript:;" data-run-id="' + haAttr(switchRunId || '') + '">查看完整日志</a> <a class="btlink ha-refresh-prepare-status" href="javascript:;" data-run-id="' + haAttr(switchRunId || '') + '">刷新状态</a></div></div>';
}

function haSyncPrepareWizardStatus(run, logText) {
  if (!run || !run.switch_run_id || !haSwitchWizard.pairId) return false;
  if (haSwitchWizard.prepareRunId && haSwitchWizard.prepareRunId !== run.switch_run_id) return false;
  var status = run.status || '';
  var currentPhase = run.current_phase || '';
  var currentStep = run.current_step || '';
  var done = (status === 'prepare_success' || status === 'success' || /预上线完成|预备上线完成/.test(currentStep + '\n' + (logText || '')));
  var failed = status === 'waiting_retry' || status === 'failed' || status === 'cancelled';
  if (!done && !failed) return false;
  haSwitchWizard.prepareRunId = run.switch_run_id;
  haSwitchWizard.prepareLog = logText || haSwitchWizard.prepareLog;
  haSwitchWizard.prepareStatus = done ? 'success' : 'failed';
  haSwitchWizard.step = 3;
  haRenderSwitchWizard();
  if (done || failed) {
    haStopSwitchLogPolling();
    haCloseSwitchLogWindow();
  }
  return true;
}

function haOpenDetailDialog(pairId, defaultTab) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  var tabs = [
    {title: '组别概览', tab: 'summary'},
    {title: '主机列表', tab: 'hosts'},
    {title: '自检状态', tab: 'health'},
    {title: '日志', tab: 'log'}
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
        var tab = defaultTab || 'summary';
        var tabEl = $('.ha-detail-menu p').filter(function() { return $(this).attr('onclick').indexOf("'" + tab + "'") !== -1; }).get(0);
        haRenderDetailTab(pair.pair_id, tab, tabEl);
      });
    },
    end: function() {
      haStopHealthAutoRefresh();
    }
  });
}

function haRenderDetailTab(pairId, tab, el, skipRefresh) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  haStopHealthAutoRefresh();
  if (el) $(el).addClass('bgw').siblings().removeClass('bgw');
  var html = '';
  if (tab === 'hosts') html = haDetailHostsHtml(pair);
  else if (tab === 'health') html = haDetailChecksHtml(pair);
  else if (tab === 'log') html = haDetailLogHtml(pair);
  else html = haDetailSummaryHtml(pair);
  $('#haDetailCon').html(html);
  if (tab === 'health') haStartHealthAutoRefresh(pairId);
  if (tab === 'log' && !skipRefresh) haRefreshLogPage(pairId);
}

function haOpenLogDialog(pairId) {
  var pager = haPairLogPager(pairId);
  pager.page = 1;
  haOpenDetailDialog(pairId, 'log');
}

function haDetailSummaryHtml(pair) {
  var actualMaster = haFindHost(pair, pair.actual_master_host_id) || {};
  var desiredMaster = haFindHost(pair, pair.desired_master_host_id) || {};
  var warnings = pair.warnings && pair.warnings.length ? pair.warnings.join('；') : '无待处理提醒';
  var failoverSummary = haPairFailoverSummary(pair);
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
      (failoverSummary ? haDetailMetric('故障恢复', failoverSummary, '') : '') +
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

function haDetailLogHtml(pair) {
  var pager = haPairLogPager(pair.pair_id);
  var runData = pair.switch_runs || {list: [], page: pager.page || 1, page_size: 20, total: 0, total_page: 1};
  if ($.isArray(runData)) runData = {list: runData, page: 1, page_size: 20, total: runData.length, total_page: 1};
  pager.page = runData.page || pager.page || 1;
  pager.page_size = runData.page_size || 20;
  var runs = runData.list || [];
  var rows = runs.map(function(run) {
    var action = haSwitchRunActionText(run);
    var status = haNormalizeSwitchStatus(run.status || '');
    var route = haSwitchRunHostRoute(pair, run);
    return '<tr>' +
      '<td><div class="ha-log-run-type">' + haEscape(action) + '</div><div class="ha-log-run-route" title="' + haAttr(route.title) + '"><span>' + haEscape(route.from) + '</span><b>→</b><span>' + haEscape(route.to) + '</span></div><div class="ha-log-run-id" title="' + haAttr(run.switch_run_id || '') + '">' + haEscape(run.switch_run_id || '') + '</div></td>' +
      '<td><span class="ha-log-status ' + haSwitchStatusClass(status) + '">' + haEscape(haSwitchRunStatusText(run.status || '')) + '</span></td>' +
      '<td><div class="ha-log-step" title="' + haAttr(run.current_step || run.current_phase || '--') + '">' + haEscape(run.current_step || run.current_phase || '--') + '</div></td>' +
      '<td><div class="ha-log-time">' + haEscape(run.addtime || '--') + '</div></td>' +
      '<td><div class="ha-log-time">' + haEscape(run.finish_time || run.update_time || '--') + '</div></td>' +
      '<td class="text-right"><button type="button" class="btn btn-default btn-xs ha-log-view-btn" onclick="haShowSwitchReadOnlyLogWindow(\'' + haAttr(action + '日志') + '\', \'' + haAttr(run.switch_run_id || '') + '\')">查看</button></td>' +
    '</tr>';
  }).join('');
  if (!rows) rows = '<tr><td colspan="6" class="ha-muted text-center ha-log-empty">暂无日志记录。</td></tr>';
  var total = runData.total || 0;
  var page = runData.page || 1;
  var totalPage = runData.total_page || 1;
  var prevDisabled = page <= 1 ? 'disabled' : '';
  var nextDisabled = page >= totalPage ? 'disabled' : '';
  var alertEvents = pair.alert_events || [];
  var alertRows = alertEvents.map(function(item) {
    var cls = item.status === 'sent' ? 'ha-pill-normal' : item.status === 'failed' ? 'ha-pill-danger' : 'ha-pill-warning';
    return '<tr>' +
      '<td><div class="ha-log-run-type">' + haEscape(item.title || item.event_type || '--') + '</div><div class="ha-log-run-id" title="' + haAttr(item.alert_key || '') + '">' + haEscape(item.alert_type || item.alert_key || '--') + '</div></td>' +
      '<td><span class="ha-log-status ' + cls + '">' + haEscape(item.status || '--') + '</span></td>' +
      '<td><div class="ha-log-step" title="' + haAttr(item.message || '--') + '">' + haEscape(item.message || '--') + '</div></td>' +
      '<td><div class="ha-log-time">' + haEscape(item.sent_by_host_id || '--') + '</div></td>' +
      '<td><div class="ha-log-time">' + haEscape(item.addtime || '--') + '</div></td>' +
    '</tr>';
  }).join('');
  if (!alertRows) alertRows = '<tr><td colspan="5" class="ha-muted text-center">暂无异常通知事件。</td></tr>';
  return '<div class="ha-detail-section">' +
    '<div class="ha-log-toolbar">' +
      '<div><div class="monitor-task-section-title">日志</div><div class="ha-muted">每页 20 条，预切换和正式上线分别记录。</div></div>' +
      '<button type="button" id="haLogRefreshBtn" class="btn btn-default btn-sm" onclick="haRefreshLogPage(\'' + haAttr(pair.pair_id) + '\')">刷新</button>' +
    '</div>' +
    '<div class="ha-log-list-shell ha-alert-event-shell"><table class="table table-hover ha-detail-data-table"><thead><tr><th width="255">异常通知</th><th width="100">状态</th><th>内容</th><th width="170">通知方</th><th width="145">时间</th></tr></thead><tbody>' + alertRows + '</tbody></table></div>' +
    '<div class="ha-log-list-shell"><table class="table table-hover ha-detail-data-table ha-switch-run-table"><thead><tr><th width="255">任务</th><th width="100">状态</th><th>当前步骤</th><th width="145">创建时间</th><th width="145">完成/更新时间</th><th width="76" class="text-right">操作</th></tr></thead><tbody>' + rows + '</tbody></table></div>' +
    '<div class="ha-log-pager"><span>共 ' + haEscape(total) + ' 条</span><span>第 ' + haEscape(page) + ' / ' + haEscape(totalPage) + ' 页</span><button type="button" class="btn btn-default btn-xs" ' + prevDisabled + ' onclick="haGoLogPage(\'' + haAttr(pair.pair_id) + '\', ' + (page - 1) + ')">上一页</button><button type="button" class="btn btn-default btn-xs" ' + nextDisabled + ' onclick="haGoLogPage(\'' + haAttr(pair.pair_id) + '\', ' + (page + 1) + ')">下一页</button></div>' +
    '</div>';
}

function haRefreshLogPage(pairId) {
  var pair = haFindPair(pairId);
  if (!pair) return layer.msg('主备关系不存在', {icon: 2});
  var pager = haPairLogPager(pairId);
  if (pager.loading) return;
  pager.loading = true;
  $('#haLogRefreshBtn').prop('disabled', true).text('刷新中');
  haApi('get_logs', {pair_id: pairId, page: pager.page || 1, page_size: pager.page_size || 20}, function(data) {
    pager.loading = false;
    $('#haLogRefreshBtn').prop('disabled', false).text('刷新');
    if (!data) return;
    pair.switch_runs = data;
    haStorePair(pair);
    haRenderDetailTab(pairId, 'log', null, true);
  }, {quiet: true});
}

function haGoLogPage(pairId, page) {
  var pager = haPairLogPager(pairId);
  pager.page = Math.max(1, page || 1);
  haRefreshLogPage(pairId);
}

function haSwitchRunHostText(pair, hostId) {
  var host = haFindHost(pair, hostId) || {};
  if (!hostId) return '--';
  if (host.host_id) return (host.name || host.host_id) + (host.ip ? ' / ' + host.ip : '');
  return hostId;
}

function haSwitchRunHostShort(pair, hostId) {
  var host = haFindHost(pair, hostId) || {};
  if (!hostId) return '--';
  return host.name || host.ip || hostId;
}

function haSwitchRunHostRoute(pair, run) {
  var fromId = run.old_master_host_id || '';
  var toId = run.new_master_host_id || run.desired_master_host_id || '';
  return {
    from: haSwitchRunHostShort(pair, fromId),
    to: haSwitchRunHostShort(pair, toId),
    title: haSwitchRunHostText(pair, fromId) + ' -> ' + haSwitchRunHostText(pair, toId)
  };
}

function haSwitchRunActionText(run) {
  var phase = run.current_phase || '';
  var status = run.status || '';
  if (phase === 'prepare_online' || status === 'pending_prepare' || status === 'prepare_success') return '预切换';
  if (phase === 'offline' || phase === 'online' || phase === 'peer_log' || status === 'pending_finalize' || status === 'pending_online' || status === 'success') return '正式上线';
  return phase || '切换任务';
}

function haSwitchRunStatusText(status) {
  if (status === 'prepare_success') return '预切换完成';
  if (status === 'success') return '成功';
  if (status === 'failed' || status === 'waiting_retry' || status === 'cancelled') return status === 'cancelled' ? '已取消' : '失败';
  if (status === 'running' || status === 'pending_prepare' || status === 'pending_finalize' || status === 'pending_online') return '执行中';
  return status || '等待';
}

function haRefreshList() {
  haLoadPairs(function() {
    layer.msg('已刷新主备状态', {icon: 1});
  });
}

function haStartAutoRefresh() {
  if (haRefreshTimer) clearInterval(haRefreshTimer);
  haRefreshTimer = setInterval(function() {
    haLoadPairs();
  }, haRefreshInterval);
  haUpdateRefreshButtonState(true);
}

function haStopAutoRefresh() {
  if (haRefreshTimer) {
    clearInterval(haRefreshTimer);
    haRefreshTimer = null;
  }
  haUpdateRefreshButtonState(false);
}

function haUpdateRefreshButtonState(isRefreshing) {
  var $btn = $('#haToggleRefresh');
  if (!$btn.length) return;
  if (isRefreshing) {
    $btn.html('<span class="glyphicon glyphicon-pause"></span> <span>停止刷新</span>');
    $btn.removeClass('btn-success').addClass('btn-default');
  } else {
    $btn.html('<span class="glyphicon glyphicon-play"></span> <span>开始刷新</span>');
    $btn.removeClass('btn-default').addClass('btn-success');
  }
}

function haSetRefreshInterval(interval) {
  haRefreshInterval = interval * 1000;
  $('#haCurrentInterval').text(interval);
  if (haRefreshTimer) {
    haStopAutoRefresh();
    haStartAutoRefresh();
  }
}

function haToggleRefresh() {
  if (haRefreshTimer) haStopAutoRefresh();
  else haStartAutoRefresh();
}

$(function() {
  $('#haCurrentInterval').text(haRefreshInterval / 1000);
  setTimeout(function() {
    haLoadPairs();
    haStartAutoRefresh();
  }, 200);
});
