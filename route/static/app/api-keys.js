
/* 面板 API 接口的调用密钥：与总密钥、IP白名单同属“配置面板API”入口。
   原文只在弹层内存中显示，普通列表返回脱敏前缀。 */
(function () {
	if (window.__apiKeyPanelStyleReady) { return; }
	window.__apiKeyPanelStyleReady = true;
	var css = [
		'.akp-card{border:1px solid #eaedf1;border-radius:8px;padding:16px 18px;background:#fff;margin-bottom:16px;}',
		'.akp-card-head{margin-bottom:14px;}',
		'.akp-card-head-flex{display:flex;align-items:flex-start;justify-content:space-between;gap:16px;}',
		'.akp-card-title{font-size:14px;font-weight:600;color:#1f2329;}',
		'.akp-card-desc{margin-top:4px;font-size:12px;line-height:18px;color:#8a9099;max-width:760px;}',
		'.akp-field{display:flex;align-items:flex-start;margin-bottom:12px;}',
		'.akp-field:last-child{margin-bottom:0;}',
		'.akp-label{flex:none;width:76px;line-height:32px;font-size:13px;color:#5c6570;}',
		'.akp-control{flex:1 1 auto;min-width:0;display:flex;flex-wrap:wrap;align-items:center;gap:8px;}',
		'.akp-input{width:100%;max-width:380px;height:32px;line-height:32px;}',
		'.akp-input-short{max-width:200px;}',
		'.akp-textarea{width:100%;max-width:380px;height:84px;line-height:20px;padding:6px 8px;resize:vertical;}',
		'.akp-alert{margin-bottom:12px;padding:8px 12px;border-radius:6px;background:#fff7e6;border:1px solid #ffe0a3;color:#ad6800;font-size:12px;}',
		'.akp-empty{padding:32px 0;text-align:center;color:#a0a6ad;font-size:13px;}',
		'.akp-table{table-layout:fixed;}',
		'.akp-table th,.akp-table td{vertical-align:middle!important;}',
		'.akp-table td{padding:10px 8px;}',
		'.akp-name{font-size:13px;font-weight:600;color:#222;line-height:20px;word-break:break-all;}',
		'.akp-subtext{margin-top:4px;font-size:12px;color:#999;line-height:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
		'.akp-tag{display:inline-block;padding:1px 7px;border:1px solid transparent;border-radius:3px;font-size:12px;line-height:16px;white-space:nowrap;}',
		'.akp-tag-admin{color:#245580;background:#eef7ff;border-color:#b8d7ef;}',
		'.akp-tag-normal{color:#777;background:#f5f5f5;border-color:#ddd;}',
		'.akp-switch{display:inline-block;margin:0;font-size:14px;font-weight:normal;line-height:0;vertical-align:middle;}',
		'.akp-switch .btswitch-btn{margin:0;}',
		'.akp-name-off{color:#a0a6ad;}',
		'.akp-key-cell{display:flex;align-items:center;gap:2px;min-width:0;}',
		'.akp-secret{flex:1 1 auto;min-width:0;background:#f5f7fa;border:1px solid #dde3ea;border-radius:3px;padding:4px 8px;font:12px/18px Menlo,Consolas,monospace;color:#555;letter-spacing:.3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}',
		'.akp-secret.akp-plain{color:#222;background:#f0f7ff;border-color:#cfe3ff;overflow-x:auto;text-overflow:clip;}',
		'.akp-copy-btn{flex:0 0 auto;width:24px;height:24px;padding:0;border:0;background:transparent;color:#b8b8b8;line-height:24px;cursor:pointer;}',
		'.akp-copy-btn:hover{color:#20a53a;}',
		'.akp-copy-btn i{font-size:13px;}',
		'.akp-actions{white-space:nowrap;}',
		'.akp-actions .btlink+.btlink{margin-left:14px;}',
		'.akp-muted{color:#999;}',
		'.akp-mono{font-family:Menlo,Consolas,monospace;}',
		'.akp-form{padding:20px 22px;}',
		'.akp-form .akp-label{width:80px;}',
		'.akp-seg{display:inline-flex;border:1px solid #dcdfe6;border-radius:6px;overflow:hidden;}',
		'.akp-seg-item{display:inline-flex;align-items:center;gap:6px;padding:6px 16px;font-size:13px;color:#5c6570;cursor:pointer;border-left:1px solid #dcdfe6;font-weight:normal;margin:0;}',
		'.akp-seg-item:first-child{border-left:none;}',
		'.akp-seg-item input{margin:0;}',
		'.akp-seg-item.akp-seg-on{background:#20a53a;color:#fff;}',
		'.akp-hint{flex-basis:100%;width:100%;margin-top:2px;font-size:12px;color:#8a9099;line-height:18px;}',
		'.akp-perms{display:flex;flex-direction:column;gap:6px;width:100%;}',
		'.akp-perm-item{display:flex;align-items:center;gap:8px;font-size:13px;color:#333;font-weight:normal;margin:0;}',
		'.akp-perm-item input{margin:0;}',
		'.akp-perm-item em{font-style:normal;color:#a0a6ad;font-size:12px;}',
		'.akp-check{display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#333;font-weight:normal;margin:0;}',
		'.akp-check input{margin:0;}'
	].join('');
	$('<style id="api-key-panel-style"></style>').text(css).appendTo(document.head);
})();

function renderPanelApiKeys(container) {
	var root = $(container);
	if (!root.length) { return; }
	var csrf = null;
	var scopeLabels = {};

	function fail(xhr, fallback) {
		var msg = (xhr && xhr.responseJSON && xhr.responseJSON.msg) || fallback || '请求失败';
		layer.msg(msg);
	}

	function submit(data) {
		var deferred = $.Deferred();
		$.post('/config/set_api_key', $.extend({}, data, { csrf_token: csrf || '' }), function (rdata) {
			if (rdata && rdata.status) { deferred.resolve(rdata.data); return; }
			deferred.reject({ responseJSON: rdata || { msg: '操作失败' } });
		}, 'json').fail(function (xhr) { deferred.reject(xhr); });
		return deferred.promise();
	}

	function formatTime(value) {
		if (!value) { return '--'; }
		var when = new Date(value);
		var pad = function (n) { return (n < 10 ? '0' : '') + n; };
		return when.getFullYear() + '-' + pad(when.getMonth() + 1) + '-' + pad(when.getDate())
			+ ' ' + pad(when.getHours()) + ':' + pad(when.getMinutes());
	}

	function permissionText(item) {
		if (item.key_type === 'admin') { return '可访问全部接口'; }
		var names = (item.scopes || []).map(function (scope) { return scopeLabels[scope] || scope; });
		return names.length ? names.join('、') : '未分配权限';
	}

	function openEditor(item) {
		item = item || {};
		var isNew = !item.key_id;
		var currentType = item.key_type === 'admin' ? 'admin' : 'normal';
		var scopeInputs = Object.keys(scopeLabels).map(function (scope) {
			return '<label class="akp-perm-item"><input type="checkbox" name="scope" value="' + scope + '">'
				+ '<span>' + scopeLabels[scope] + '</span><em>' + scope + '</em></label>';
		}).join('') || '<div class="akp-hint" style="margin-top:0;">暂无可分配的权限</div>';
		var form = $('<div class="akp-form">'
			+ '<div class="akp-field"><label class="akp-label">密钥类型</label><div class="akp-control">'
			+ '<div class="akp-seg">'
			+ '<label class="akp-seg-item"><input type="radio" name="key_type" value="normal"><span>普通密钥</span></label>'
			+ '<label class="akp-seg-item"><input type="radio" name="key_type" value="admin"><span>管理员密钥</span></label>'
			+ '</div><div class="akp-hint akp-type-hint"></div></div></div>'
			+ '<div class="akp-field"><label class="akp-label">名称</label><div class="akp-control">'
			+ '<input class="bt-input-text akp-input" name="name" type="text" maxlength="128" placeholder="例如：江湖数据同步"></div></div>'
			+ '<div class="akp-field akp-field-perms"><label class="akp-label">接口权限</label><div class="akp-control">'
			+ '<div class="akp-perms">' + scopeInputs + '</div></div></div>'
			+ '<div class="akp-field"><label class="akp-label">备注</label><div class="akp-control">'
			+ '<input class="bt-input-text akp-input" name="remark" type="text" placeholder="选填"></div></div>'
			+ '<div class="akp-field"><label class="akp-label">有效期</label><div class="akp-control">'
			+ '<input class="bt-input-text akp-input akp-input-short" name="expires_at" type="datetime-local">'
			+ '<span class="akp-hint" style="flex-basis:auto;width:auto;margin-top:0;">留空为长期有效</span></div></div>'
			+ '<div class="akp-field"><label class="akp-label">状态</label><div class="akp-control">'
			+ '<label class="akp-check"><input type="checkbox" name="is_enabled"><span>启用该密钥</span></label></div></div>'
			+ '</div>');
		form.find('[name=name]').val(item.name || '');
		form.find('[name=remark]').val(item.remark || '');
		form.find('[name=is_enabled]').prop('checked', isNew ? true : !!item.is_enabled);
		form.find('[name=key_type][value="' + currentType + '"]').prop('checked', true);
		(item.scopes || []).forEach(function (scope) { form.find('[name=scope][value="' + scope + '"]').prop('checked', true); });
		if (item.expires_at) {
			var when = new Date(item.expires_at);
			form.find('[name=expires_at]').val(new Date(when.getTime() - when.getTimezoneOffset() * 60000).toISOString().slice(0, 16));
		}

		function syncType() {
			var type = form.find('[name=key_type]:checked').val() || 'normal';
			var admin = type === 'admin';
			form.find('.akp-seg-item').each(function () {
				$(this).toggleClass('akp-seg-on', $(this).find('input').prop('checked'));
			});
			form.find('.akp-type-hint').text(admin ? '可访问全部接口，包含以后新增的接口' : '只能访问下方勾选的接口');
			form.find('.akp-field-perms')[admin ? 'hide' : 'show']();
		}
		form.find('[name=key_type]').change(syncType);
		syncType();

		form.appendTo(document.body);
		layer.open({
			type: 1, title: isNew ? '新增调用密钥' : '编辑调用密钥', area: ['600px', '560px'], content: form,
			btn: ['保存', '取消'],
			yes: function (index) {
				var type = form.find('[name=key_type]:checked').val() || 'normal';
				var name = $.trim(form.find('[name=name]').val());
				if (!name) { layer.msg('请填写名称'); return; }
				var scopes = type === 'admin' ? []
					: form.find('[name=scope]:checked').map(function () { return this.value; }).get();
				if (type === 'normal' && !scopes.length) { layer.msg('请至少勾选一个接口权限'); return; }
				var expiry = form.find('[name=expires_at]').val();
				submit({
					action: isNew ? 'create' : 'update', key_id: item.key_id || '',
					name: name, key_type: type, remark: form.find('[name=remark]').val(),
					scopes: JSON.stringify(scopes),
					is_enabled: form.find('[name=is_enabled]').prop('checked') ? '1' : '0',
					expires_at: expiry ? new Date(expiry).toISOString() : ''
				}).then(function () {
					layer.close(index); load();
					if (isNew) { layer.msg('调用密钥已创建'); }
				}, function (xhr) { fail(xhr); });
			},
			end: function () { form.remove(); }
		});
	}

	function buildRow(item) {
		var row = $('<tr>'
			+ '<td><div class="akp-name"></div></td>'
			+ '<td class="akp-type"></td>'
			+ '<td><div class="akp-key-cell"><code class="akp-secret"></code></div></td>'
			+ '<td class="akp-perm"></td>'
			+ '<td class="akp-expiry"></td>'
			+ '<td class="akp-used"></td>'
			+ '<td class="akp-state"></td>'
			+ '<td class="text-right akp-actions"></td>'
			+ '</tr>');
		row.find('.akp-name').text(item.name).toggleClass('akp-name-off', !item.is_enabled);
		row.find('.akp-type').append($('<span class="akp-tag"></span>')
			.addClass(item.key_type === 'admin' ? 'akp-tag-admin' : 'akp-tag-normal')
			.text(item.key_type === 'admin' ? '管理员' : '普通'));
		if (item.remark) {
			$('<div class="akp-subtext"></div>').text('备注：' + item.remark).attr('title', item.remark)
				.appendTo(row.children('td').first());
		}
		row.find('.akp-perm').text(permissionText(item));
		row.find('.akp-expiry').text(item.expires_at ? formatTime(item.expires_at) : '长期有效');
		row.find('.akp-used').text(item.last_used_at ? formatTime(item.last_used_at) : '未使用');

		var switchBox = $('<label class="akp-switch"></label>')
			.attr('title', item.is_enabled ? '点击停用该密钥' : '点击启用该密钥');
		var switchInput = $('<input type="checkbox" class="btswitch btswitch-ios">')
			.prop('checked', !!item.is_enabled).appendTo(switchBox);
		$('<span class="btswitch-btn"></span>').appendTo(switchBox);
		switchInput.change(function () {
			var next = this.checked;
			switchInput.prop('disabled', true);
			submit({
				action: 'update', key_id: item.key_id, name: item.name, remark: item.remark || '',
				key_type: item.key_type || 'normal',
				scopes: JSON.stringify(item.scopes || []),
				is_enabled: next ? '1' : '0',
				expires_at: item.expires_at || ''
			}).then(function () {
				layer.msg(next ? '已启用' : '已停用');
				load();
			}, function (xhr) {
				switchInput.prop('checked', !next).prop('disabled', false);
				fail(xhr);
			});
		});
		row.find('.akp-state').append(switchBox);

		var secret = row.find('.akp-secret').text(item.key_prefix);
		var keyCell = row.find('.akp-key-cell');
		var eye = $('<button type="button" class="akp-copy-btn akp-eye" title="显示密钥"></button>')
			.html('<i class="glyphicon glyphicon-eye-open"></i>').appendTo(keyCell);
		var copy = $('<button type="button" class="akp-copy-btn" title="复制密钥"></button>')
			.html('<i class="glyphicon glyphicon-duplicate"></i>').appendTo(keyCell);
		eye.click(function () {
			if (row.data('revealed')) {
				secret.text(item.key_prefix).removeClass('akp-plain');
				eye.attr('title', '显示密钥').html('<i class="glyphicon glyphicon-eye-open"></i>');
				row.data('revealed', false);
				return;
			}
			submit({ action: 'reveal', key_id: item.key_id }).then(function (data) {
				secret.text(data.key).addClass('akp-plain');
				eye.attr('title', '隐藏密钥').html('<i class="glyphicon glyphicon-eye-close"></i>');
				row.data('revealed', true);
			}, function (xhr) { fail(xhr); });
		});
		copy.click(function () {
			submit({ action: 'reveal', key_id: item.key_id }).then(function (data) {
				if (navigator.clipboard && window.isSecureContext) {
					navigator.clipboard.writeText(data.key).then(function () { layer.msg('已复制'); }, function () { layer.msg('复制失败，请手动选择'); });
					return;
				}
				var input = $('<textarea>').val(data.key).appendTo(document.body);
				input[0].select();
				var copied = document.execCommand('copy');
				input.remove();
				layer.msg(copied ? '已复制' : '请点击眼睛图标后手动复制');
			}, function (xhr) { fail(xhr); });
		});

		function link(label, handler) {
			return $('<a class="btlink" href="javascript:;"></a>').text(label).click(handler).appendTo(row.find('.akp-actions'));
		}
		link('编辑', function () { openEditor($.extend({}, item, { scopes: item.scopes })); });
		link('删除', function () {
			layer.confirm('删除后该调用方立即失去访问权限，确定删除吗？', { title: '删除调用密钥', closeBtn: 2 }, function (index) {
				submit({ action: 'delete', key_id: item.key_id }).then(function () { layer.close(index); load(); }, function (xhr) { fail(xhr); });
			});
		});
		return row;
	}

	function renderList(data) {
		scopeLabels = data.scopes || {};
		root.empty();
		var card = $('<div class="akp-card">'
			+ '<div class="akp-card-head akp-card-head-flex"><div>'
			+ '<div class="akp-card-title">调用密钥</div>'
			+ '<div class="akp-card-desc">给每个外部系统单独分配一个密钥：管理员密钥可访问全部接口，普通密钥只能访问勾选的接口。</div>'
			+ '</div><button class="btn btn-success btn-sm akp-add">新增密钥</button></div>'
			+ '</div>');
		root.append(card);
		card.find('.akp-add').click(function () { openEditor(null); });
		if (!data.panel_api_open) {
			card.append('<div class="akp-alert">API 接口总开关未开启，调用密钥暂时不可用。</div>');
		}
		if (!data.list.length) {
			card.append('<div class="akp-empty">尚未创建调用密钥</div>');
			return;
		}
		var table = $('<div class="divtable"><div class="tablescroll">'
			+ '<table class="table table-hover akp-table">'
			+ '<colgroup><col style="width:164px;"><col style="width:74px;"><col style="width:328px;"><col style="width:158px;">'
			+ '<col style="width:100px;"><col style="width:122px;"><col style="width:72px;"><col style="width:94px;"></colgroup>'
			+ '<thead><tr><th>名称</th><th>类型</th><th>密钥</th><th>权限</th><th>有效期</th><th>最近使用</th><th>状态</th><th class="text-right">操作</th></tr></thead>'
			+ '<tbody></tbody></table></div></div>');
		var body = table.find('tbody');
		data.list.forEach(function (item) { body.append(buildRow(item)); });
		card.append(table);
	}

	function load() {
		$.post('/config/get_api_keys', '', function (rdata) {
			if (!rdata.status) { root.html('<div class="akp-empty">' + (rdata.msg || '读取失败') + '</div>'); return; }
			csrf = rdata.data.csrf_token;
			renderList(rdata.data);
		}, 'json');
	}

	load();
}
