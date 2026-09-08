var haLocalPairs = [];
var haLocalLogTimer = null;
var haLocalRefreshTimer = null;
var haLocalRefreshInterval = 60000;
var haLocalSortSaving = false;
var haLocalSortResumeRefresh = false;
var haLocalSortDragContext = null;

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
function haLocalPairHosts(pair) { return pair.hosts && pair.hosts.length ? pair.hosts : (pair.host ? [pair.host] : []); }
function haLocalHostsHtml(pair) {
  var hosts = haLocalPairHosts(pair);
  if (!hosts.length) return '<span class="ha-local-subtext">等待注册</span>';
  return hosts.map(function(host) {
    return '<span class="ha-local-host-compact" title="' + haLocalEscape((host.host_name || host.host_id || '--') + ' / ' + (host.host_ip || host.host_id || '--')) + '"><span class="ha-local-host-name">' + haLocalEscape(host.host_name || host.host_id || '--') + '</span>' + haLocalOnlineTag(host.online_status) + '</span>';
  }).join('');
}
function haLocalHostRolesHtml(pair) {
  var hosts = haLocalPairHosts(pair);
  return hosts.length ? hosts.map(function(host) { return '<span class="ha-local-host-role-summary">' + haLocalRoleTag(host.role) + '</span>'; }).join('') : '--';
}

function haLocalLoadPairs() {
  if (haLocalSortSaving || haLocalSortDragContext) return;
  haLocalApi('list', {}, function(data) {
    if (haLocalSortSaving || haLocalSortDragContext) return;
    haLocalPairs = (data && data.list) || [];
    var rows = haLocalPairs.map(function(pair) {
      return '<tr data-ha-pair-row-id="' + haLocalEscape(pair.pair_id) + '"><td class="text-center"><span class="ha-local-sort-handle" aria-hidden="true"><i></i><i></i><i></i></span></td><td><div class="ha-local-main">' + haLocalEscape(pair.pair_name || '--') + '</div><div class="ha-local-subtext ha-local-pair-id-line"><span class="ha-local-pair-id-text" title="' + haLocalEscape(pair.pair_id) + '">' + haLocalEscape(pair.pair_id) + '</span><button type="button" class="ha-local-copy-btn" title="复制主备关系 ID" onclick="haLocalCopyPairId(\'' + haLocalEscape(pair.pair_id) + '\')"><i class="glyphicon glyphicon-duplicate"></i></button></div></td>' +
        '<td><div class="ha-local-host-summary"><span class="ha-local-host-count">' + haLocalPairHosts(pair).length + ' 台</span>' + haLocalHostsHtml(pair) + '</div></td>' +
        '<td>' + haLocalHostRolesHtml(pair) + '</td>' +
        '<td><span class="ha-local-status ' + haLocalStatusClass(pair.status) + '">' + haLocalStatusText(pair.status) + '</span><div class="ha-local-subtext" title="' + haLocalEscape(pair.status_text) + '">' + haLocalEscape(pair.status_text || '--') + '</div></td>' +
        '<td>' + haLocalEscape(pair.last_report_at || '--') + '</td><td class="text-right ha-local-actions"><a class="btlink" href="javascript:;" onclick="haLocalOpenDetail(\'' + haLocalEscape(pair.pair_id) + '\')">详情</a><a class="btlink" href="javascript:;" onclick="haLocalOpenEdit(\'' + haLocalEscape(pair.pair_id) + '\')">编辑</a><a class="btlink" href="javascript:;" onclick="haLocalDeletePair(\'' + haLocalEscape(pair.pair_id) + '\')">删除</a></td></tr>';
    }).join('');
    $('#haLocalPairBody').html(rows);
    $('#haLocalEmpty').toggle(!haLocalPairs.length); $('#haLocalTableWrap').toggle(!!haLocalPairs.length);
    haLocalInitSort();
  });
}

function haLocalGetSortRowIds() {
  return $('#haLocalPairBody tr').map(function() {
    return $(this).attr('data-ha-pair-row-id');
  }).get().filter(function(pairId) {
    return !!pairId;
  });
}

function haLocalIsSameSortOrder(beforeRows, afterRows) {
  if (!beforeRows || !afterRows || beforeRows.length !== afterRows.length) return false;
  for (var i = 0; i < beforeRows.length; i++) {
    if (beforeRows[i] !== afterRows[i]) return false;
  }
  return true;
}

function haLocalCreateSortPlaceholder(row) {
  var columnCount = row.children().length;
  var height = Math.max(row.outerHeight() - 8, 24);
  return $("<tr class='ha-local-sort-placeholder'><td colspan='" + columnCount + "'><div class='ha-local-sort-placeholder-inner' style='height:" + height + "px'></div></td></tr>");
}

function haLocalCreateSortPreview(row, tableWidth) {
  var preview = $("<div class='ha-local-sort-drag-preview'><table class='table table-hover ha-local-table'><tbody></tbody></table></div>");
  var clonedRow = row.clone();
  row.children().each(function(index) {
    clonedRow.children().eq(index).width($(this).outerWidth());
  });
  preview.find('tbody').append(clonedRow);
  preview.find('table').width(tableWidth);
  $('body').append(preview);
  return preview;
}

function haLocalMoveSortPreview(pageX, pageY) {
  if (!haLocalSortDragContext || !haLocalSortDragContext.preview) return;
  haLocalSortDragContext.preview.css({
    left: pageX - haLocalSortDragContext.pointerOffsetLeft,
    top: pageY - haLocalSortDragContext.pointerOffsetTop
  });
}

function haLocalUpdateSortPlaceholder(pageY) {
  if (!haLocalSortDragContext || !haLocalSortDragContext.placeholder) return;
  var body = haLocalSortDragContext.body;
  var placeholder = haLocalSortDragContext.placeholder;
  var inserted = false;
  body.children('tr').not(placeholder).each(function() {
    var row = $(this);
    if (pageY < row.offset().top + row.outerHeight() / 2) {
      row.before(placeholder);
      inserted = true;
      return false;
    }
  });
  if (!inserted) body.append(placeholder);
}

function haLocalUpdateSortAutoScroll(pageY) {
  if (!haLocalSortDragContext || !haLocalSortDragContext.scrollContainer.length) return;
  var scrollContainer = haLocalSortDragContext.scrollContainer;
  var offset = scrollContainer.offset();
  if (!offset) return;
  var threshold = 48;
  var bottom = offset.top + scrollContainer.outerHeight();
  var delta = 0;
  if (pageY < offset.top + threshold) delta = -Math.max(6, Math.ceil((offset.top + threshold - pageY) / 4));
  if (pageY > bottom - threshold) delta = Math.max(6, Math.ceil((pageY - (bottom - threshold)) / 4));
  if (delta) scrollContainer.scrollTop(scrollContainer.scrollTop() + delta);
}

function haLocalCleanupSortDrag() {
  if (haLocalSortDragContext && haLocalSortDragContext.preview) haLocalSortDragContext.preview.remove();
  $(document).off('.haLocalSortDrag');
  $('body').removeClass('ha-local-sort-dragging');
  haLocalSortDragContext = null;
}

function haLocalStartSortDrag(event, draggedRow) {
  var row = $(draggedRow);
  var offset = row.offset();
  var tableWidth = row.closest('table').outerWidth();
  var placeholder = haLocalCreateSortPlaceholder(row);
  haLocalSortDragContext = {
    body: $('#haLocalPairBody'),
    row: row,
    placeholder: placeholder,
    preview: null,
    scrollContainer: row.closest('.tablescroll'),
    initialOrder: haLocalGetSortRowIds(),
    pointerOffsetLeft: event.pageX - offset.left,
    pointerOffsetTop: event.pageY - offset.top
  };
  row.before(placeholder);
  row.detach();
  haLocalSortDragContext.preview = haLocalCreateSortPreview(row, tableWidth);
  haLocalMoveSortPreview(event.pageX, event.pageY);
  haLocalUpdateSortPlaceholder(event.pageY);
  $('body').addClass('ha-local-sort-dragging');
  haLocalSortResumeRefresh = !!haLocalRefreshTimer;
  if (haLocalSortResumeRefresh) haLocalStopRefresh();
}

function haLocalFinishSortDrag() {
  if (!haLocalSortDragContext) return;
  var context = haLocalSortDragContext;
  context.placeholder.before(context.row);
  context.placeholder.remove();
  var afterOrder = haLocalGetSortRowIds();
  var changed = !haLocalIsSameSortOrder(context.initialOrder, afterOrder);
  haLocalCleanupSortDrag();
  if (changed) {
    haLocalSaveSort(afterOrder);
  } else if (haLocalSortResumeRefresh) {
    haLocalSortResumeRefresh = false;
    haLocalStartRefresh();
  }
}

function haLocalSaveSort(pairIds) {
  if (pairIds.length <= 1) {
    if (haLocalSortResumeRefresh) {
      haLocalSortResumeRefresh = false;
      haLocalStartRefresh();
    }
    return;
  }
  haLocalSortSaving = true;
  var loading = layer.msg('正在保存排序', {icon: 16, time: 0, shade: [0.3, '#000']});
  $.post('/ha/api/local/pair/sort', {pair_ids: pairIds}, function(res) {
    layer.close(loading);
    layer.msg((res && res.msg) || '排序保存失败', {icon: res && res.status ? 1 : 2});
    if (res && res.status) {
      haLocalSortSaving = false;
      haLocalLoadPairs();
    }
  }, 'json').fail(function() {
    layer.close(loading);
    layer.msg('排序保存失败', {icon: 2});
  }).always(function() {
    haLocalSortSaving = false;
    if (haLocalSortResumeRefresh) {
      haLocalSortResumeRefresh = false;
      haLocalStartRefresh();
    }
  });
}

function haLocalBindSortEvents() {
  $('#haLocalPairBody').off('mousedown.haLocalSort', '.ha-local-sort-handle').on('mousedown.haLocalSort', '.ha-local-sort-handle', function(event) {
    if ($(this).hasClass('disabled') || event.which !== 1) return false;
    event.preventDefault();
    var draggedRow = $(this).closest('tr');
    var startX = event.pageX;
    var startY = event.pageY;
    var started = false;
    $(document).off('.haLocalSortDrag').on('mousemove.haLocalSortDrag', function(moveEvent) {
      if (!started) {
        if (Math.max(Math.abs(moveEvent.pageX - startX), Math.abs(moveEvent.pageY - startY)) < 4) return;
        started = true;
        haLocalStartSortDrag(event, draggedRow);
      }
      haLocalMoveSortPreview(moveEvent.pageX, moveEvent.pageY);
      haLocalUpdateSortAutoScroll(moveEvent.pageY);
      haLocalUpdateSortPlaceholder(moveEvent.pageY);
    }).on('mouseup.haLocalSortDrag', function() {
      if (started) haLocalFinishSortDrag();
      else $(document).off('.haLocalSortDrag');
    });
    return false;
  });
}

function haLocalInitSort() {
  haLocalCleanupSortDrag();
  haLocalBindSortEvents();
  var canSort = $('#haLocalPairBody tr').length > 1;
  $('#haLocalPairBody .ha-local-sort-handle').toggleClass('disabled', !canSort).attr('title', canSort ? '拖动排序' : '至少需要两条主备关系才能拖动排序');
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

function haLocalGeneratePairId() {
  var values = [];
  if (window.crypto && window.crypto.getRandomValues) {
    var randomValues = new Uint32Array(4);
    window.crypto.getRandomValues(randomValues);
    for (var i = 0; i < randomValues.length; i++) values.push(randomValues[i].toString(16).toUpperCase().padStart(8, '0'));
  } else {
    for (var j = 0; j < 4; j++) values.push(Math.floor(Math.random() * 0x100000000).toString(16).toUpperCase().padStart(8, '0'));
  }
  return 'HA' + values.join('');
}

function haLocalResetPairId() {
  $('#haLocalPairId').val(haLocalGeneratePairId());
}

function haLocalOpenCreate() {
  var pairId = haLocalGeneratePairId();
  var html = '<div class="bt-form ha-local-dialog pd20"><div class="line"><span class="tname">关系名称</span><div class="info-r"><input id="haLocalPairName" class="bt-input-text" placeholder="例如：生产环境主备" style="width:300px"></div></div><div class="line"><span class="tname">主备关系 ID</span><div class="info-r ha-local-pair-id-input"><input id="haLocalPairId" class="bt-input-text" value="' + haLocalEscape(pairId) + '" style="width:260px"><button type="button" class="btn btn-default btn-sm" title="重新生成主备关系 ID" onclick="haLocalResetPairId()"><span class="glyphicon glyphicon-refresh"></span></button></div></div><div class="line"><span class="tname"></span><div class="info-r c9">可在两个机房填写相同 ID；仅支持字母、数字、下划线和连字符。</div></div></div>';
  layer.open({type: 1, title: '添加主备关系', area: '540px', content: html, btn: ['添加', '取消'], yes: function(index) {
    haLocalApi('pair/create', {pair_name: $('#haLocalPairName').val(), pair_id: $('#haLocalPairId').val()}, function(data) {
      if (!data) return;
      layer.close(index); haLocalShowPairId(data); haLocalLoadPairs();
    });
  }});
}

function haLocalShowPairId(data) {
  var html = '<div class="pd20"><div class="ha-local-pair-id">' + haLocalEscape(data.pair_id) + '</div><div class="c9 mt10">请将此 ID 填入本地版插件的云监控配置。</div></div>';
  layer.open({type: 1, title: '主备关系 ID', area: '560px', content: html, btn: ['已填写']});
}

function haLocalOpenEdit(pairId) {
  var pair = haLocalPairs.filter(function(item) { return item.pair_id === pairId; })[0];
  if (!pair) {
    layer.msg('主备关系不存在或列表已刷新', {icon: 2});
    return;
  }
  var html = '<div class="bt-form ha-local-dialog pd20"><div class="line"><span class="tname">关系名称</span><div class="info-r"><input id="haLocalEditPairName" class="bt-input-text" value="' + haLocalEscape(pair.pair_name || '') + '" style="width:300px"></div></div><div class="line"><span class="tname">主备关系 ID</span><div class="info-r"><input id="haLocalEditPairId" class="bt-input-text" value="' + haLocalEscape(pair.pair_id) + '" style="width:300px"></div></div><div class="line"><span class="tname"></span><div class="info-r c9">修改 ID 后，需要将本地版插件的云监控配置同步为新 ID。</div></div></div>';
  layer.open({type: 1, title: '编辑主备关系', area: '540px', content: html, btn: ['保存', '取消'], yes: function(index) {
    var newPairId = $('#haLocalEditPairId').val();
    var save = function() {
      haLocalApi('pair/update', {original_pair_id: pairId, pair_id: newPairId, pair_name: $('#haLocalEditPairName').val()}, function(data) {
        if (!data) return;
        layer.close(index);
        layer.msg(data.pair_id !== pairId ? '主备关系已更新，请同步修改本地版插件配置' : '主备关系已更新', {icon: 1});
        haLocalLoadPairs();
      });
    };
    if ($.trim(newPairId) !== pairId) {
      layer.confirm('修改主备关系 ID 后，已配置的本地版插件需要同步填写新 ID，确认修改？', {title: '确认修改主备关系 ID', icon: 0}, function(confirmIndex) {
        layer.close(confirmIndex);
        save();
      });
      return;
    }
    save();
  }});
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
    var hosts = haLocalPairHosts(pair); var tasks = pair.tasks || [];
    var hostRows = hosts.map(function(host) {
      return '<tr><td><div class="ha-local-main">' + haLocalEscape(host.host_name || '--') + '</div><div class="ha-local-subtext">' + haLocalEscape(host.host_ip || host.host_id || '--') + '</div></td><td>' + haLocalRoleTag(host.role) + '</td><td>' + haLocalOnlineTag(host.online_status) + '</td><td>' + haLocalHealthTag(host.health_status) + '</td><td>' + haLocalEscape(host.last_report_at || '--') + '</td></tr>';
    }).join('') || '<tr><td colspan="5" class="c9">暂无机器上报</td></tr>';
    var taskRows = tasks.map(function(task) { return '<tr><td>' + haLocalEscape(task.switch_task_id) + '</td><td>' + haLocalRoleTag(task.target_role) + '</td><td>' + haLocalTaskStatusTag(task.status) + '</td><td>' + haLocalEscape(task.current_step || task.status_text || '--') + '</td><td class="text-right"><a class="btlink" href="javascript:;" onclick="haLocalOpenLog(\'' + haLocalEscape(task.switch_task_id) + '\')">查看日志</a></td></tr>'; }).join('') || '<tr><td colspan="5" class="c9">暂无切换任务</td></tr>';
    var html = '<div class="pd20"><table class="table table-hover ha-local-detail-table"><tbody><tr><th>主备关系 ID</th><td>' + haLocalEscape(pair.pair_id) + '</td></tr><tr><th>关系名称</th><td>' + haLocalEscape(pair.pair_name || '--') + '</td></tr><tr><th>关系状态</th><td><span class="ha-local-status ' + haLocalStatusClass(pair.status) + '">' + haLocalStatusText(pair.status) + '</span><span class="ha-local-detail-text">' + haLocalEscape(pair.status_text || '--') + '</span></td></tr><tr><th>关系最近上报</th><td>' + haLocalEscape(pair.last_report_at || '--') + '</td></tr></tbody></table><div class="ha-local-detail-section-title">上报机器</div><table class="table table-hover ha-local-host-table"><thead><tr><th>机器</th><th>角色</th><th>在线状态</th><th>自检</th><th>最近上报</th></tr></thead><tbody>' + hostRows + '</tbody></table><div class="ha-local-detail-section-title">切换任务</div><table class="table table-hover"><thead><tr><th>任务</th><th>目标</th><th>状态</th><th>当前步骤</th><th></th></tr></thead><tbody>' + taskRows + '</tbody></table></div>';
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
