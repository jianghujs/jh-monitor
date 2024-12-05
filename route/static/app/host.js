var refreshTimer = null;
var refreshInterval = 5000; // 默认5秒
var loadT = layer.load();
var hostList = [];

/**
 * 主机数据列表
 * @param {Number} page   当前页
 * @param {String} search 搜索条件
 */
function getWeb(page, search, host_group_id) {
	search = $("#SearchValue").prop("value");
	page = page == undefined ? '1':page;
	var order = getCookie('order');
	if(order){
		order = '&order=' + order;
	} else {
		order = '';
	}

	var host_group_select = '';
	if ( typeof(host_group_id) != 'undefined' ){
		host_group_select = '&host_group_id='+host_group_id;
	}

	var sUrl = '/host/list';
	var pdata = 'limit=1000&p=' + page + '&search=' + search + order + host_group_select;
	//取回数据
	$.post(sUrl, pdata, function(data) {
		layer.close(loadT);
		//构造数据列表
		var body = '';
		$("#webBody").html(body);
    hostList = data.data;
		for (var i = 0; i < data.data.length; i++) {

      const { net_info, load_avg } = data.data[i];
      // 主机名称
      let name = '';
      name += `
      <div class="flex align-center">
          <span>${data.data[i].host_name}</span>
          <span style='margin-left: 5px;' onclick="openEditHostName('${data.data[i].host_id}','${data.data[i].host_name}')\" title='修改名称' class='text-2xl btlink opacity-60 hover:opacity-100 cursor-pointer glyphicon glyphicon-edit'></span>
      </div>
      <div>
          <span>${data.data[i].ip}</span>
          <span style='margin-left: 5px;' onclick="copyText('${data.data[i].ip}')\" title='复制IP' class='text-2xl btlink opacity-60 hover:opacity-100 cursor-pointer glyphicon glyphicon-copy'></span>
      </div>
      `

			// 当前主机状态
			if (data.data[i].host_status == 'Running') {
				var status = "<a href='javascript:;' class='btn-defsult'><span style='color:rgb(92, 184, 92)'>运行中</span><span style='color:rgb(92, 184, 92)' class='glyphicon glyphicon-play'></span></a>";
			} else {
				var status = "<a href='javascript:;' class='btn-defsult'><span style='color:red'>已停止</span><span style='color:rgb(255, 0, 0);' class='glyphicon glyphicon-pause'></span></a>";
			}

      let host_group = `
        <div class="flex align-center">
          <span>${(formatValue(data.data[i]['host_group_name']) || '--')}</span>
          <span  onclick="openChangeHostGroup('${data.data[i].host_id}','${data.data[i].host_name}','${data.data[i].host_group_id}')\" style='color:rgb(92, 184, 92)' class='ml-2 text-2xl btlink opacity-60 hover:opacity-100 cursor-pointer glyphicon glyphicon-edit' title='修改分组'></span>
        </div>
      `;

      // 负载状态 
      var loadColor, occupy, averageText = '';
      let avg = load_avg['1min']
      let max = load_avg['max'] || 1
      occupy = Math.round((avg / max) * 100);
      if (occupy > 100) Occupy = 100;

      // 负载
      let load_status = '';
      if (occupy) {
        let load_percent = occupy;
        load_status = `<div class="load-usage" title="${load_percent}%">
          <div class="d-flex flex-column relative">
            <div class="progress relative" style="margin-bottom: 0;height: 20px;">
              <div class="progress-bar ${load_percent >= 80 ? 'progress-bar-danger': (load_percent >= 60? 'progress-bar-warning': 'progress-bar-success')}" role="progressbar" 
                aria-valuenow="${load_percent}" aria-valuemin="0" aria-valuemax="100" 
                style="width: ${load_percent}%;">
                <div style="position: absolute; width: 100%; text-align: center; color: ${load_percent > 40 ? '#fff' : '#28a745'};">
                  ${load_percent}%
                </div>
              </div>
            </div>
          </div>
        </div>`;
      } else {
        load_status = "<span>--</span>";
      }

      // CPU使用率
      let cpu_status = '';
      if (data.data[i]['cpu_info']['percent'] !== undefined) {
        let cpu_percent = data.data[i]['cpu_info']['percent'];
        cpu_status = `<div class="cpu-usage" title="${cpu_percent}%">
          <div class="d-flex flex-column">
            <div class="progress relative" style="margin-bottom: 0;height: 20px;">
              <div class="progress-bar ${cpu_percent >= 80 ? 'progress-bar-danger': (cpu_percent >= 60? 'progress-bar-warning': 'progress-bar-success')}" role="progressbar" 
                aria-valuenow="${cpu_percent}" aria-valuemin="0" aria-valuemax="100" 
                style="width: ${cpu_percent}%;">
                <div style="position: absolute; width: 100%; text-align: center; color: ${cpu_percent > 40 ? '#fff' : '#28a745'};">
                  ${cpu_percent}%
                </div>
              </div>
            </div>
          </div>
        </div>`;
      } else {
        cpu_status = "<span>--</span>";
      }

      // 内存使用率
      let mem_status = '';
      if (data.data[i].mem_info) {
        let mem_percent = data.data[i]['mem_info']['usedPercent']
        mem_status = `<div class="mem-usage" title="${mem_percent}%">
          <div class="d-flex flex-column">
            <div class="progress relative" style="margin-bottom: 0;height: 20px;">
              <div class="progress-bar ${mem_percent >= 80 ? 'progress-bar-danger': (mem_percent >= 60? 'progress-bar-warning': 'progress-bar-success')}" role="progressbar" 
                aria-valuenow="${mem_percent}" aria-valuemin="0" aria-valuemax="100" 
                style="width: ${mem_percent}%;">
                <div style="position: absolute; width: 100%; text-align: center; color: ${mem_percent > 40 ? '#fff' : '#28a745'};">
                  ${mem_percent}%
                </div>
              </div>
            </div>
          </div>
        </div>`;
      } else {
        mem_status = "<span>--</span>";
      }

      // 流量
      let net_speed = '';
      let net_total = '';
      if (net_info) {
        net_speed += "<div>" + net_info.up + "KB/S</div>";
        net_speed += "<div>" + net_info.down + "KB/S</div>";
        net_total += "<div>" + toSize(net_info.upTotal) + "</div>";
        net_total += "<div>" + toSize(net_info.downTotal) + "</div>";
      }

      // 磁盘;
      let disk_total = 0;
      let disk_used = 0;
      let disk_percent = 100;
      let disk_speed = ''
      let disk_status = '';
			if (data.data[i].disk_info && data.data[i].disk_info.length > 0) {
        disk_total = (data.data[i].disk_info[0]['total'] || 0)
        disk_used = (data.data[i].disk_info[0]['used'] || 0)
        disk_percent = data.data[i].disk_info[0]['usedPercent'] || 0;
        disk_speed += "<div>" + toSize(data.data[i].disk_info[0]['readSpeed'] || 0) + "/S</div>";
        disk_speed += "<div>" + toSize(data.data[i].disk_info[0]['writeSpeed'] || 0) + "/S</div>";
        disk_status = `<div class="disk-usage" title="${disk_percent}%（${toSize(disk_used)}/${toSize(disk_total)}）">
          <div class="d-flex flex-column">
            <div class="progress relative" style="margin-bottom: 0;height: 20px;">
              <div class="progress-bar ${disk_percent >= 80 ? 'progress-bar-danger': (disk_percent >= 60? 'progress-bar-warning': 'progress-bar-success')}" role="progressbar" 
                aria-valuenow="${disk_percent}" aria-valuemin="0" aria-valuemax="100" 
                style="width: ${disk_percent}%;">
                <div style="position: absolute; width: 100%; text-align: center; color: ${disk_percent > 40 ? '#fff' : '#28a745'};">
                  ${disk_percent}%
                </div>
              </div>
            </div>
          </div>
        </div>`;
      } else {
        disk_status = "<span>--</span>";
      }

      // 报告概览
      let report_summary = '';
      if (data.data[i].panel_report && data.data[i].panel_report.error_tips) {
        let error_tips = data.data[i].panel_report.error_tips;
        if (error_tips.length > 0) {
          report_summary += `<div style='color: red;'>${error_tips.join('<br/>')}</div>`;
        } else {
          report_summary += `<div style='color: rgb(92, 184, 92);'>正常</div>`;
        }
      } else {
        report_summary += `<div style='color: #cecece;'>暂无</div>`;
      }


      // 操作列
      let opt = ``;
      // 打开江湖面板
      if (data.data[i].host_info && data.data[i].host_info.isJHPanel) { 
        // 增加跳转 jhPanelUrl 
        // 替换 ip地址为 data.data[i].ip，端口不要替换掉
        let jhPanelUrl = (data.data[i].host_info.jhPanelUrl || '').replace(/(https?:\/\/)([^:]+)/, `$1${data.data[i].ip}`);
        opt += `<a href='${jhPanelUrl}' class='btlink' target='_blank'>打开江湖面板 | </a>`;
      }
      // 打开PVE面板
      if (data.data[i].host_info && data.data[i].host_info.isPVE) {
        opt += `<a href='${data.data[i].host_info.pvePanelUrl}' class='btlink' target='_blank'>打开PVE面板 | </a>`;
      }
      opt += `
        <a href='javascript:;' class='btlink' onclick="openHostDetail('${data.data[i].host_id}','${data.data[i].host_name}','${data.data[i].edate}','${data.data[i].addtime}')">详情</a>
        | <a href='javascript:;' class='btlink' onclick="hostDelete('${data.data[i].host_id}','${data.data[i].host_name}')" title='删除主机'>删除</a>
      `;
      

			body = "<tr><td><input type='checkbox' name='id' title='"+data.data[i].host_name+"' onclick='checkSelect();' value='" + data.data[i].id + "'></td>\
					<td>" + name + "</td>\
					<td>" + status + "</td>\
					<td>" + host_group + "</td>\
					<td class='percent-color'>" + load_status + "</td>\
					<td class='percent-color'>" + cpu_status + "</td>\
					<td class='percent-color'>" + mem_status + "</td>\
					<td>" + net_speed + "</td>\
					<td>" + net_total + "</td>\
					<td>" + disk_speed + "</td>\
					<td>" + disk_status + "</td>\
					<td>" + report_summary + "</td>\
					<td>" + toTime(data.data[i]['detail_addtime']) + "</td>\
					<td style='text-align:right; color:#bbb'>" + opt + "</td>\
        </tr>"
			
			$("#webBody").append(body);

      renderPercentColor();
			//setEdate(data.data[i].id,data.data[i].edate);
         	//设置到期日期
			function getDate(a) {
				var dd = new Date();
				dd.setTime(dd.getTime() + (a == undefined || isNaN(parseInt(a)) ? 0 : parseInt(a)) * 86400000);
				var y = dd.getFullYear();
				var m = dd.getMonth() + 1;
				var d = dd.getDate();
				return y + "-" + (m < 10 ? ('0' + m) : m) + "-" + (d < 10 ? ('0' + d) : d);
			}
            $('#webBody').on('click','#site_'+ data.data[i].id,function(){
				var _this = $(this);
				var id = $(this).attr('data-ids');
				laydate.render({
					elem: '#site_'+ id //指定元素
					,min:getDate(1)
					,max:'2099-12-31'
					,vlue:getDate(365)
					,type:'date'
					,format :'yyyy-MM-dd'
					,trigger:'click'
					,btns:['perpetual', 'confirm']
					,theme:'#20a53a'
					,done:function(dates){
						if(_this.html() == '永久'){
						 	dates = '0000-00-00';
						}
						var loadT = layer.msg(lan.site.saving_txt, { icon: 16, time: 0, shade: [0.3, "#000"]}); 
						$.post('/site/set_end_date','id='+id+'&edate='+dates,function(rdata){
							layer.close(loadT);
							layer.msg(rdata.msg,{icon:rdata.status?1:5});
						},'json');
					}
				});
            	this.click();
            });
		}
		if(body.length < 10){
			body = "<tr><td colspan='9'>当前没有主机数据</td></tr>";
			// $(".dataTables_paginate").hide();
			$("#webBody").html(body);
		}
		//输出数据列表
		$(".btn-more").hover(function(){
			$(this).addClass("open");
		},function(){
			$(this).removeClass("open");
		});
		//输出分页
		// $("#webPage").html(data.page);
		// $("#webPage").html('<div class="site_type"><span>主机分组:</span><select class="bt-input-text mr5" style="width:100px"><option value="-1">全部分组</option><option value="0">默认分组</option></select></div>');
		
		$(".btlinkbed").click(function(){
			var dataid = $(this).attr("data-id");
			var databak = $(this).text();
			if(databak == null){
				databak = '';
			}
			$(this).hide().after("<input class='baktext' type='text' data-id='"+dataid+"' name='bak' value='" + databak + "' placeholder='备注信息' onblur='getBakPost(\"sites\")' />");
			$(".baktext").focus();
		});

		readerTableChecked();
	},'json');
}

/**
 * 主机分组列表
 */
var hostGroupList = [];
function getHostGroupList() {
  
	var select = $('.host_group_list > select');
	$.post('/host/get_host_group_list',function(rdata){
    hostGroupList = rdata;
		$(select).html('');
		$(select).append('<option value="-1">全部分组</option>');
		for (var i = 0; i<rdata.length; i++) {
			$(select).append('<option value="'+rdata[i]['host_group_id']+'">'+rdata[i]['host_group_name']+'</option>');
		}

		$(select).bind('change',function(){
			var select_id = $(this).val();
			// console.log(select_id);
			getWeb(1,'',select_id);
		})
	},'json');
}
getHostGroupList();

/**
 * 主机分组管理
 */

function openHostGroupManage(){
		layer.open({
			type: 1,
			area: '350px',
			title: '主机分组管理',
			closeBtn: 1,
			shift: 0,
			content: '<div class="bt-form edit_site_type">\
					<div class="divtable mtb15" style="overflow:auto">\
						<div class="line "><div class="info-r  ml0">\
							<input name="host_group_name" class="bt-input-text mr5 host_group_name" placeholder="请填写分组名称" type="text" style="width:50%" value=""><button name="btn_submit" class="btn btn-success btn-sm mr5 ml5 btn_submit" onclick="addHostGroup();">添加</button></div>\
						</div>\
						<table id="type_table" class="table table-hover" width="100%">\
							<thead><tr><th>分组名称</th><th width="80px">操作</th></tr></thead>\
							<tbody id="hostGroupListCon"></tbody>\
						</table>\
					</div>\
				</div>'
		});
    getHostGroupListTable();
}

/**
 * 主机分组管理列表
 */
function getHostGroupListTable() {
  $.post('/host/get_host_group_list',function(rdata){
		var list = '';
		for (var i = 0; i<rdata.length; i++) {
			list +='<tr><td>' + rdata[i]['host_group_name'] + '</td>\
				<td><a class="btlink edit_type" onclick="openEditHostGroup(\''+rdata[i]['id']+'\',\''+rdata[i]['host_group_name']+'\')">编辑</a> | <a class="btlink del_type" onclick="removeHostGroup(\''+rdata[i]['id']+'\',\''+rdata[i]['host_group_id']+'\',\''+rdata[i]['host_group_name']+'\')">删除</a>\
				</td></tr>';
		}
    $('#hostGroupListCon').html(list);
	},'json');
}

/**
 * 添加主机分组
 */
function addHostGroup(){
	var host_group_name = $("input[name=host_group_name]").val();
	$.post('/host/add_host_group','host_group_name='+host_group_name, function(rdata){
		showMsg(rdata.msg,function(){
			if (rdata.status){
        getHostGroupListTable();
				getHostGroupList();
			}
		},{icon:rdata.status?1:2});
	},'json');
}

/**
 * 删除主机分组
 */
function removeHostGroup(id,host_group_id,host_group_name){
	if (id == 0){
		layer.msg('默认分组不可删除/不可编辑!',{icon:2});
		return;
	}
	layer.confirm('是否确定删除分组？',{title: '删除分组【'+ host_group_name +'】' }, function(){
		$.post('/host/remove_host_group','id='+id, function(rdata){
			showMsg(rdata.msg,function(){
				if (rdata.status){
          getHostGroupListTable();
					getHostGroupList();
				}
			},{icon:rdata.status?1:2});
		},'json');
	});
}

/**
 * 编辑主机分组
 */
function openEditHostGroup(id,host_group_name){
	if (id == 0){
		layer.msg('默认分组不可删除/不可编辑!',{icon:2});
		return;
	}

	var editHostGroupLayer = layer.open({
		type: 1,
		area: '350px',
		title: '修改分组管理【' + host_group_name + '】',
		closeBtn: 1,
		shift: 0,
		content: "<form class='bt-form bt-form pd20 pb70' id='mod_pwd'>\
                <div class='line'>\
                    <span class='tname'>分组名称</span>\
                    <div class='info-r'><input name=\"host_group_name_mod\" class='bt-input-text mr5' type='text' value='"+host_group_name+"' /></div>\
                </div>\
                <div class='bt-form-submit-btn'>\
                    <button id='submit_host_group_mod' type='button' class='btn btn-success btn-sm btn-title'>提交</button>\
                </div>\
              </form>"
	});

	$('#submit_host_group_mod').unbind().click(function(){
		var host_group_name = $('input[name=host_group_name_mod]').val();
		$.post('/host/modify_host_group_name','id='+id+'&host_group_name='+host_group_name, function(rdata){
			showMsg(rdata.msg,function(){
				if (rdata.status){
          layer.close(editHostGroupLayer);
          getHostGroupListTable();
					getHostGroupList();
				}
			},{icon:rdata.status?1:2});
		},'json');

	});
}


/**
 * 
 * 修改主机名称
 */
function openEditHostName(host_id, host_name) {
  layer.open({
    type: 1,
    title: `编辑主机名称【${host_name}】`,
    area: '440px',
    closeBtn: 1,
    shift: 0,
    content: `
    <form class='bt-form pd20 pb70' id='editHostNameForm'>
      <div class="p-10 text-xl">
        <div class='line'>
          <span class='tname'>主机名称</span>
          <div class='info-r c4'>
            <input id='Wbeizhu' class='bt-input-text' type='text' name='host_name' placeholder='主机名称' style='width:268px' value='${host_name}'/>
            <input hidden type='text' name='host_id' hidden value='${host_id}'/>
          </div>
        </div>
        
        <div class='bt-form-submit-btn'>
          <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.closeAll()'>取消</button>
          <button type='button' class='btn btn-success btn-sm btn-title' onclick="submitEditHostName()">提交</button>
        </div>
      </div>
    </form>
    `

  });
}

/**
 * 修改主机名称
 */
function submitEditHostName() {
  let editHostNameForm = $('#editHostNameForm').serialize();
	loading = layer.msg('正在修改!',{icon:16,time:0,shade: [0.3, "#000"]})
	$.post('/host/update_host_name', editHostNameForm, function(data){
		layer.close(loading);
		if (data.status){
      getWeb(1);
      layer.closeAll()
      
		} else {
			layer.msg(data.msg,{icon:0,time:3000,shade: [0.3, "#000"]})
		}
	},'json');
}

/**
 * 
 * 修改主机所属分组
 */
function openChangeHostGroup(host_id, host_name, host_group_id) {
  let hostGroupListCon = hostGroupList.map(item => `
     <option value='${item.host_group_id}' ${item.host_group_id == host_group_id? 'selected': ''}>${item.host_group_name}</option>  
  `)
  layer.open({
    type: 1,
    title: `设置主机分组【${host_name}】`,
    area: '440px',
    closeBtn: 1,
    shift: 0,
    content: `
    <form class='bt-form pd20 pb70' id='changeHostGroupForm'>
      <div class="p-10 text-xl">
        <div class='line'>
          <span class='tname'>主机分组</span>
          <div class='info-r c4'>
            <select class="bt-input-text mr5" name="host_group_id" style="width: 260px;" value="${host_group_id}">${hostGroupListCon}</select>
            <input hidden type='text' name='host_id' hidden value='${host_id}'/>
          </div>
        </div>
        
        <div class='bt-form-submit-btn'>
          <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.closeAll()'>取消</button>
          <button type='button' class='btn btn-success btn-sm btn-title' onclick="submitChangeHostGroup()">提交</button>
        </div>
      </div>
    </form>
    `
                // args['delete'] = $('select[name="delete"]').val();

  });
}


/**
 * 修改主机所属分组
 */
function submitChangeHostGroup() {
  let changeHostGroupForm = $('#changeHostGroupForm').serialize();
	loading = layer.msg('正在修改!',{icon:16,time:0,shade: [0.3, "#000"]})
	$.post('/host/change_host_group', changeHostGroupForm, function(data){
		layer.close(loading);
		if (data.status){
      getWeb(1);
      layer.closeAll()
      
		} else {
			layer.msg(data.msg,{icon:0,time:3000,shade: [0.3, "#000"]})
		}
	},'json');
}

/**
 * 添加主机
 */
function openHostAdd() {
  layer.open({
    type: 1,
    area: ['640px', '600px'],
    title: '添加主机',
    closeBtn: 1,
    shift: 0,
    content: `
    <div class="p-10 text-xl">
      <div class="mb-6" hidden>
        <h3 class="font-medium mb-4">立即接入被控享受以下功能</h3>
        <ul class="space-y-2 bg-gray-100 p-5">
          <li>全系统监控: 实时监控你的被控机器可用性、漏洞、恶意程序</li>
          <li>实时告警: 监控到异常情况时多种通知告警</li>
          <li>堡垒机: 子账号授权管理员登录服务器录音信息</li>
        </ul>
      </div>
      
      <div class="mb-6">
        <h3 class="font-medium mb-4">安装步骤</h3>
        <ol class="list-decimal list-inside space-y-2 bg-gray-100 p-5">
          <li>复制安装脚本, 进入被监控服务器的SSH终端(需要root权限)后粘贴复制的命令</li>
          <li>命令执行完成后服务器即是会看到等待接收的主机，点击接收即可以接收被监控端传入的数据</li>
        </ol>
      </div>
      
      <div class="mb-6">
        <h3 class="font-medium mb-2 mb-4">获取命令</h3>
        <div class="bg-gray-100 p-5">
          <div class="mb-4">
            <label class="block font-medium mb-4">操作系统</label>
            <div class="flex items-center rounded">
              <button class="bg-green-600 hover:bg-green-700 text-white py-2 px-4 rounded-l">Linux</button>
              <button class="bg-gray-700 hover:bg-gray-800 text-white py-2 px-4 rounded-r">Windows</button>
            </div>
          </div>
          <h3 class="font-medium mb-4">安装命令</h3>
          <div class="mb-4">
            <label class="block mb-4">国际源</label>
            <div class="flex items-center bg-gray-200 p-5 rounded">
              <div class="flex-1 overflow-x-auto break-words" id="clientInstallShellLANOfGithub"></div>
              <button class="ml-2 bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded" onclick="copyClientInstallShellLAN('clientInstallShellLANOfGithub')">复制</button>
            </div>
          </div>
          <div class="mb-4">
            <label class="block mb-4">国内源</label>
            <div class="flex items-center bg-gray-200 p-5 rounded">
              <div class="flex-1 overflow-x-auto break-words" id="clientInstallShellLANOfGitee"></div>
              <button class="ml-2 bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded" onclick="copyClientInstallShellLAN('clientInstallShellLANOfGitee')">复制</button>
            </div>
          </div>
          <div class="mb-4" hidden>
            <label class="block font-medium mb-4">被控公网安装命令</label>
            <div class="flex items-center bg-gray-200 p-5 rounded">
              <div class="flex-1 overflow-x-auto break-words">curl -sSO http://www.btkaixin.net/install/btmonitoragent.sh && bash btmonitoragent.sh https://240e:3b1:44a1:f3b0:a00:27ff:fe54:e15e:806 e3359d2264ecc6ea29663f34dbc69a6a</div>
              <button class="ml-2 bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded">复制</button>
            </div>
          </div>
          <div hidden>
            <h3 class="font-medium mb-4">主控IP</h3>
            <div class="flex space-x-4">
              <input type="text" placeholder="请输入主控IP" class="flex-1 bg-gray-200 text-white py-25 px-4 rounded" />
              <button class="bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded">获取命令</button>
            </div>
          </div>
        </div>
      </div>

      
    </div>
    `
  });

  $.post('/host/get_client_install_shell_lan','', function(data){
    let rdata = JSON.parse(data)
    if (rdata.status){
      $("#clientInstallShellLANOfGithub").html(rdata.data.github);
      $("#clientInstallShellLANOfGitee").html(rdata.data.gitee);
    }
  });
}

/**
 * 复制添加主机命令
 * @param {*} key 
 */
function copyClientInstallShellLAN(key) {
  let text = ($("#" + key).html() || '').replace(/&amp;/g, '&');
  copyText(text);
}

//添加主机
function hostAdd() {
  var loadT = layer.msg(lan.public.the_get,{icon:16,time:0,shade: [0.3, "#000"]})
  var data = $("#addhost").serialize();
  $.post('/host/add', data, function(ret) {
    if (ret.status == true) {
      getWeb(1);
      layer.closeAll();
      layer.msg('成功创建主机',{icon:1})
    } else {
      layer.msg(ret.msg, {icon: 2});
    }
    layer.close(loadT);
  },'json');
}

/**
 * 删除一个主机
 * @param {Number} host_id 主机ID
 * @param {String} name 主机名称
 */
function hostDelete(host_id, name){
	safeMessage("确认", "确定要删除主机"+"["+name+"]吗？", function(){
		var loadT = layer.msg('正在处理,请稍候...',{icon:16,time:10000,shade: [0.3, '#000']});
		$.post("/host/delete","host_id=" + host_id, function(ret){
			layer.closeAll();
			layer.msg(ret.msg,{icon:ret.status?1:2})
			getWeb(1);
		},'json');
	});
}


// -------------------------- 自动刷新 --------------------------
// 开始自动刷新
function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer);
  refreshTimer = setInterval(function() {
    getWeb();
  }, refreshInterval);
  updateRefreshButtonState(true);
}

// 停止自动刷新
function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  updateRefreshButtonState(false);
}

// 更新刷新按钮状态
function updateRefreshButtonState(isRefreshing) {
  var $btn = $('#toggleRefresh');
  if (isRefreshing) {
    $btn.html('<span class="glyphicon glyphicon-pause"></span> <span>停止刷新</span>');
    $btn.removeClass('btn-success').addClass('btn-default');
  } else {
    $btn.html('<span class="glyphicon glyphicon-play"></span> <span>开始刷新</span>');
    $btn.removeClass('btn-default').addClass('btn-success');
  }
}

// 设置刷新间隔
function setRefreshInterval(interval) {
  refreshInterval = interval * 1000;
  $('#currentInterval').text(interval);
  if (refreshTimer) {
    stopAutoRefresh();
    startAutoRefresh();
  }
}

// 切换刷新状态
function toggleRefresh() {
  if (refreshTimer) {
    stopAutoRefresh();
  } else {
    startAutoRefresh();
  }
}

// 在页面加载完成后启动自动刷新
$(function() {
  // 初始化UI状态
  $('#currentInterval').text(refreshInterval/1000);
  startAutoRefresh();
});
// -------------------------- 自动刷新 --------------------------

/*主机详情*/
var detailHostId = null;
function openHostDetail(host_id,host_name,endTime,addtime,event){
  detailHostId = host_id;
	event && event.preventDefault();
  let host = hostList.find(item => item.host_id == host_id);
  let tabItems = [
    { title: '主机概览', fun: `detailHostSummary('${host_id}', '${host_name}')` },
    { title: '基础监控', fun: `detailBaseMonitor('${host_id}')` },
    { title: '日志监控', fun: `detailLogMonitor('${host_id}')` },
    { title: '系统监控', fun: `detailSysMonitor('${host_name}')` },
    { title: '面板报告', fun: `detailPanelReport('${host_id}')`, hidden: !(host && host.host_info && host.host_info.isJHPanel && host.panel_report) },
  ]

	layer.open({
		type: 1,
		area: '80%',
		title: '主机详情['+host_name+']',
		closeBtn: 1,
		shift: 0,
		content: `<div class='bt-form'>
			<div class='bt-w-menu pull-left' style='height: 565px;'>
				${tabItems.map((item, index) => `<p class="${index == 0? 'bgw': ''}" onclick="${item.fun}" ${item.hidden? 'hidden': ''} title="${item.title}">${item.title}</p>`).join('')}
      </div>
			<div id='hostdetail-con' class='bt-w-con hostdetail-con pd15' style='height: 565px;overflow: scroll;background: #fcf8f8;'></div>
		</div>`,
		success:function(){

			//切换
			$(".bt-w-menu p").click(function(){
				$(this).addClass("bgw").siblings().removeClass("bgw");
			});

			detailHostSummary(host_id,host_name);
		}
	});	
}

// 弹框内容 Start ==========================>

/**
 * 主机概览
 * @param {Int} host_id 网站ID
 */
let getDetailHostSummaryDataTask = null;
function detailHostSummary(host_id, name, msg, status) {
  if (getDetailHostSummaryDataTask) {
    clearInterval(getDetailHostSummaryDataTask);
  }
  var bodyHtml = `

    <!-- 主机信息 -->
    <div class="detailHostSummary server bgw mb15">
      <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">主机信息</h3>
      </div>
      <div class="p-5">
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">主机名称: </span><span class="hostName"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">IP地址:</span><span class="ip"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">操作系统:</span><span class="platform"></span></div>
              <div hidden class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">运行天数:</span><span class="runDay"></span></div>
          </div>
          <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-2">
              <div hidden class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">被控版本:</span><span class="jhMonitorVersion"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32" title="modelName">CPU型号:</span><span class="modelName"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">平均负载:</span><span class="loadAvg"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">已不间断运行:</span><span class="upTime"></span></div>
          </div>
      </div>
    </div>

    <div class="grid lg:grid-cols-2 gap-5 mt-2">
      <div>
        <!-- 系统状态 -->
        <div class="server bgw">
          <div class="title c6 f16 plr15">
              <h3 class="c6 f16 pull-left">系统状态</h3>
          </div>
          <div class="mx-auto server-circle">
              <ul class="grid sm:grid-cols-2 md:grid-cols-3 2xl:grid-cols-4" id="systemInfoList">
                  <li class="mtb20 circle-box text-center" id="LoadList">
                      <h3 class="c5 f15">负载状态<a href="https://github.com/jianghujs/jh-panel/wiki#负载简述" target="_blank" class="bt-ico-ask" style="cursor: pointer;">?</a></h3>
                      <div class="circle" style="cursor: pointer;">
                          <div class="pie_left">
                              <div class="left"></div>
                          </div>
                          <div class="pie_right">
                              <div class="right"></div>
                          </div>
                          <div class="mask"><span id="Load">0</span>%</div>
                      </div>
                      <h4 id="LoadState" class="c5 f15">获取中...</h4>
                  </li>
                  <li class="mtb20 circle-box text-center" id="cpuChart">
                      <h3 class="c5 f15">CPU使用率</h3>
                      <div class="circle">
                          <div class="pie_left">
                              <div class="left"></div>
                          </div>
                          <div class="pie_right">
                              <div class="right"></div>
                          </div>
                          <div class="mask"><span id="cpu">0</span>%</div>
                      </div>
                      <h4 id="cpuState" class="c5 f15">获取中...</h4>
                  </li>
                  <li class="mtb20 circle-box text-center">
                      <h3 class="c5 f15">内存使用率</h3>
                      <div class="circle">
                          <div class="pie_left">
                              <div class="left"></div>
                          </div>
                          <div class="pie_right">
                              <div class="right"></div>
                          </div>
                          <div class="mask"><span id="memory">0</span>%</div>
                          <div class="mem-re-min" style="display: none;"></div>
                          <div class="mem-re-con" title=""></div>
                      </div>
                      <h4 id="memoryState" class="c5 f15">获取中...</h4>
                  </li>
              </ul>
          </div>
        </div>

        <!-- 进程占用TOP10 -->
        <div class="server bgw mt-5" style="height:600px" hidden>
          <div class="title c6 f16 plr15">
              <h3 class="c6 f16 pull-left">进程占用TOP10</h3>
          </div>
          <div class="mx-auto">
              
            <div class="divtable m-5">
              <div class="tablescroll">
              <table class="table table-hover" style="border: 0 none;">
                <thead>
                  <tr>
                    <th width="40" class="cursor-pointer">进程名</th>
                    <th width="40" class="cursor-pointer">CPU</th>
                    <th width="40" class="cursor-pointer">内存</th>
                    <th width="40" class="cursor-pointer">网络总IO</th>
                    <th width="40" class="cursor-pointer">磁盘总IO</th>
                  </tr>
                </thead>
                <tbody id="processRankBody"></tbody>
              </table>
              </div>
              <div class="dataTables_paginate paging_bootstrap pagination">
                <ul id="webPage" class="page"></ul>
              </div>
            </div>


          </div>
        </div>
      
      </div>

      <div>

        <!-- 网络IO -->
        <div class="bgw relative" style="height:491px">
            <div class="title c6 f16 plr15">流量</div>
            <div class="bw-info">
                <div class="col-sm-6 col-md-3"><p class="c9"><span class="ico-up"></span>上行</p><a id="upSpeed">0</a></div>
                <div class="col-sm-6 col-md-3"><p class="c9"><span class="ico-down"></span>下行</p><a id="downSpeed">0</a></div>
                <div class="col-sm-6 col-md-3"><p class="c9">总发送</p><a id="upAll">0</a></div>
                <div class="col-sm-6 col-md-3"><p class="c9">总接收</p><a id="downAll">0</a></div>
            </div>
            <div id="netImg" style="width: 100%; height:330px;"></div>
        </div>

        
        <!-- 告警事件 -->
        <div class="server bgw mt-5">
          <div class="title c6 f16 plr15">
              <h3 class="c6 f16 pull-left">告警事件</h3>
          </div>
          <div class="mx-auto">
            <div class="divtable m-5">
              <div class="tablescroll">
              <table class="table table-hover" style="border: 0 none;">
                <thead>
                  <tr>
                    <th width="120">告警内容</th>
                    <th width="40">告警时间</th>
                    <th width="40">状态</th>
                    <th width='40' class='text-right border-none'>操作</th>
                  </tr>
                </thead>
                <tbody id="alarmBody"></tbody>
              </table>
              </div>
              <div class="dataTables_paginate paging_bootstrap pagination">
                <ul id="webPage" class="page"></ul>
              </div>
            </div>
          </div>
        </div>

        <!-- 在线的SSH用户 -->
        <div class="server bgw mt-5">
          <div class="title c6 f16 plr15">
              <h3 class="c6 f16 pull-left">在线的SSH用户</h3>
          </div>
          <div class="mx-auto">
            <div class="divtable m-5">
              <div class="tablescroll">
              <table class="table table-hover" style="border: 0 none;">
                <thead>
                  <tr>
                    <th width="120">用户名</th>
                    <th width="40">虚拟终端</th>
                    <th width="40">登录时间</th>
                    <th width="40">登录IP</th>
                  </tr>
                </thead>
                <tbody id="sshUserBody"></tbody>
              </table>
              </div>
              <div class="dataTables_paginate paging_bootstrap pagination">
                <ul id="webPage" class="page"></ul>
              </div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  `;


  $("#hostdetail-con").html(bodyHtml);
  initDetailHostSummaryNetChart();
  
  getDetailHostSummaryData(host_id);
  getDetailHostSummaryDataTask =  setInterval(function() {
    getDetailHostSummaryData(host_id);
  }, 30000);

}

/**
 * 基础监控
 * @param {Int} host_id 网站ID
 */
let updateDetailHostBaseMonitorTask = null;
function detailBaseMonitor(host_id, name, msg, status) {
  if (updateDetailHostBaseMonitorTask) {
    clearInterval(updateDetailHostBaseMonitorTask);
  }
  var bodyHtml = `
    <div class="control">
      <div class="col-xs-12 col-sm-12 col-md-12 pull-left pd0 view0">
        <div class="mb15">
          <div class="bgw pb15">
            <div class="title c6 plr15 mb15">
              <h3 class="c-tit f16">平均负载</h3>
              <div class="searcTime pull-right">
                <span class="tit">区间检索：</span>
                <span class="gt" onclick="Wday(1,'getload')">昨天</span>
                <span class="gt on" onclick="Wday(0,'getload')">今天</span>
                <span class="gt" onclick="Wday(7,'getload')">最近7天</span>
                <span class="gt" onclick="Wday(30,'getload')">最近30天</span>
                <div class="ss">
                  <span class="st">自定义时间</span>
                  <div class="time">
                    <span class="bt">开始时间<input class="btime" type="text" value="2017/1/10 00:00:00"></span>
                    <span class="et">结束时间<input class="etime" type="text" value="2017/1/13 00:00:00"></span>
                    <div class="sbtn loadbtn">提交</div>
                  </div>
                </div>
              </div>
            </div>
            <div id="avgloadview" style="width:100%; height:330px"></div>
          </div>
        </div>
      </div>
      <div class="col-xs-12 col-sm-12 col-md-6 pull-left pd0 view1">
        <div class="pr8">
          <div class="bgw pb15">
            <div class="title c6 plr15">
              <h3 class="c-tit f16">CPU</h3>
              <div class="searcTime pull-right"><span class="tit">区间检索：</span><span class="gt" onclick="Wday(1,'cpu')">昨天</span><span class="gt on" onclick="Wday(0,'cpu')">今天</span><span class="gt" onclick="Wday(7,'cpu')">最近7天</span><span class="gt" onclick="Wday(30,'cpu')">最近30天</span>
                <div class="ss">
                  <span class="st">自定义时间</span>
                  <div class="time">
                    <span class="bt">开始时间<input class="btime" type="text" value="2017/1/10 00:00:00"></span>
                    <span class="et">结束时间<input class="etime" type="text" value="2017/1/13 00:00:00"></span>
                    <div class="sbtn cpubtn">提交</div>
                  </div>
                </div>
              </div>
            </div>
            <div id="cupview" style="width:100%; height:330px"></div>
          </div>
        </div>
      </div>
      <div class="col-xs-12 col-sm-12 col-md-6 pull-left pd0 view2">
        <div class="pl7">
          <div class="bgw pb15">
            <div class="title c6 plr15">
              <h3 class="c-tit f16">内存</h3>
              <div class="searcTime pull-right"><span class="tit">区间检索：</span><span class="gt" onclick="Wday(1,'mem')">昨天</span><span class="gt on" onclick="Wday(0,'mem')">今天</span><span class="gt" onclick="Wday(7,'mem')">最近7天</span><span class="gt" onclick="Wday(30,'mem')">最近30天</span>
                <div class="ss">
                  <span class="st">自定义时间</span>
                  <div class="time">
                    <span class="bt">开始时间<input class="btime" type="text" value="2017/1/10 00:00:00"></span>
                    <span class="et">结束时间<input class="etime" type="text" value="2017/1/13 00:00:00"></span>
                    <div class="sbtn membtn">提交</div>
                  </div>
                </div>
              </div>
            </div>
            <div id="memview" style="width:100%; height:330px"></div>
          </div>
        </div>
      </div>
      <div class="col-xs-12 col-sm-12 col-md-6 pull-left pd0 view1">
        <div class="pr8">
          <div class="bgw pb15">
            <div class="title c6 plr15 mb15">
              <h3 class="c-tit f16">磁盘IO</h3>
              <div class="searcTime pull-right"><span class="tit">$data['lan']['S1']</span><span class="gt" onclick="Wday(1,'disk')">昨天</span><span class="gt on" onclick="Wday(0,'disk')">今天</span><span class="gt" onclick="Wday(7,'disk')">最近7天</span><span class="gt" onclick="Wday(30,'disk')">最近30天</span>
                <div class="ss">
                  <span class="st">自定义时间</span>
                  <div class="time">
                    <span class="bt">开始时间<input class="btime" type="text" value="2017/1/10 00:00:00"></span>
                    <span class="et">结束时间<input class="etime" type="text" value="2017/1/13 00:00:00"></span>
                    <div class="sbtn diskbtn">提交</div>
                  </div>
                </div>
              </div>
            </div>
            <div id="diskview" style="width:100%; height:330px"></div>
          </div>
        </div>
      </div>
      <div class="col-xs-12 col-sm-12 col-md-6 pull-left pd0 view2">
        <div class="pl7">
          <div class="bgw pb15">
            <div class="title c6 plr15 mb15">
              <h3 class="c-tit f16">网络IO</h3>
              <div class="searcTime pull-right"><span class="tit">$data['lan']['S1']</span><span class="gt" onclick="Wday(1,'network')">昨天</span><span class="gt on" onclick="Wday(0,'network')">今天</span><span class="gt" onclick="Wday(7,'network')">最近7天</span><span class="gt" onclick="Wday(30,'network')">最近30天</span>
                <div class="ss">
                  <span class="st">自定义时间</span>
                  <div class="time">
                    <span class="bt">开始时间<input class="btime" type="text" value="2017/1/10 00:00:00"></span>
                    <span class="et">结束时间<input class="etime" type="text" value="2017/1/13 00:00:00"></span>
                    <div class="sbtn networkbtn">提交</div>
                  </div>
                </div>
              </div>
            </div>
            <div id="network" style="width:100%; height:330px"></div>
          </div>
        </div>
      </div>
    </div>
  `;

  $("#hostdetail-con").html(bodyHtml);

  initDetailHostBaseMonitorChart();
  setTimeout(() => {
    updateDetailHostBaseMonitorChartData();
  }, 0);
}

/**
 * 日志监控
 * @param {Int} host_id 网站ID
 */
function detailLogMonitor(host_id, name, msg, status) {
  
  var bodyHtml = `
    <div class="flex flex-wrap">
      <!-- 日志路径列表 --> 
      <div class="bgw" style="width: 30%;height: 500px;">
        <div class="server mb15">
          <div class="title c6 f16 plr15">
              <h3 class="c6 f16 pull-left">日志路径列表</h3>
          </div>
          <div class=" overflow-y-auto" style="height:460px">
              <ul id="logFileBody" class="log-path-list" style="line-height: 35px;">
                  <span>加载中...</span>
              </ul>
          </div>
        </div>
      </div>
      <div style="width:68%;" id="logFileDetail">
        <div class="mx-5 mb-5 p-5 bg-white">
          <div class="title mt-2 flex">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">日志路径: </span><span class="path"></span></div>
          </div>
          <div class="mt-2 flex">
              <!-- <div class="mr-5 overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">日志大小:</span><span class="size"></span></div> -->
              <!-- <div class="mr-5 overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">文件权限:</span><span class="permission"></span></div> -->
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">修改时间:</span><span class="modifyTime"></span></div>
          </div>
        </div>
        <div class="mx-5 p-5 bgw content overflow-auto" style="height: 390px;">
          日志内容为空
        </div>
      </div>
    </div>
  `;

  $("#hostdetail-con").html(bodyHtml);

  getDetailHostLogMonitorData(host_id);

}

/**
 * 系统监控
 * @param {Int} host_id 网站ID
 */
function detailSysMonitor(host_id, name, msg, status) {
  var bodyHtml = `

    <!-- 主机SSH登陆信息 -->
    <div class="server bgw mt-5" style="height:200px">
      <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">主机SSH登陆信息</h3>
      </div>
      <div class="mx-auto">
        <div class="divtable m-5">
          <div class="tablescroll">
          <table class="table table-hover" style="border: 0 none;">
            <thead>
              <tr>
                <th width="120">被登录的主机</th>
                <th width="40">用户</th>
                <th width="40">登陆IP</th>
                <th width="40">登陆地址</th>
                <th width="40">登陆状态</th>
                <th width="40">登陆时间</th>
              </tr>
            </thead>
            <tbody id="sshLoginBody"></tbody>
          </table>
          </div>
          <div class="dataTables_paginate paging_bootstrap pagination">
            <ul class="page"></ul>
          </div>
        </div>
      </div>
    </div>

    <!-- SSH命令执行记录 -->
    <div class="server bgw mt-5" style="height:200px">
      <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">SSH命令执行记录</h3>
      </div>
      <div class="mx-auto">
        <div class="divtable m-5">
          <div class="tablescroll">
          <table class="table table-hover" style="border: 0 none;">
            <thead>
              <tr>
                <th width="120">用户名</th>
                <th width="180">执行时间</th>
                <th>命令</th>
              </tr>
            </thead>
            <tbody  id="sshCommandBody"></tbody>
          </table>
          </div>
          <div class="dataTables_paginate paging_bootstrap pagination">
            <ul class="page"></ul>
          </div>
        </div>
      </div>
    </div>
    
  `;

  $("#hostdetail-con").html(bodyHtml);

  getDetailHostSysMonitorData();

}

/**
 * 面板报告
 * @param {*} host_id 
 */
function detailPanelReport(host_id) {
  let host = hostList.find(item => item.host_id == host_id);
  let { panel_report } = host;
  let { title, ip, report_time, start_date, end_date, summary_tips, sysinfo_tips, backup_tips, siteinfo_tips, jianghujsinfo_tips, dockerinfo_tips, mysqlinfo_tips } = panel_report;
  let bodyHtml = '';
  if ( panel_report && panel_report.title) {
    bodyHtml = `
      <div class="panel_report bgw p-5">
        <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">${title}(${ip})-服务器运行报告</h3>
        </div>
        <div class="mx-auto leading-10 plr15">
          <h3 class="pt-5" style="color: #cecece">日期：${start_date}至${end_date}（报告时间：${report_time}）</h3>
          <div class="p-5" style="display: flex; flex-direction: column;align-items: center;">
              <h3 class="text-2xl mb-2">概要信息：</h3>
              <ul>
              ${summary_tips.map(item => `<li>${item}</li>`).join('')}
              </ul>
          </div>
          <div class="m-auto" style="width: 600px;">
            <h3 class="font-bold my-5">系统状态：</h3>
            <table border class="system-table w-full">
            ${sysinfo_tips.map(item => `<tr><td>${item.name}</td><td>${item.desc}</td></tr>`).join('')}
            </table>

            <h3 class="font-bold my-5">备份：</h3>
            <table border class="w-full">
            ${backup_tips.map(item => `<tr><td>${item.name}</td><td>${item.desc}</td></tr>`).join('')}
            </table>

            <h3 class="font-bold my-5">网站：</h3>
            <table border class="w-full">
            ${siteinfo_tips.map(item => `<tr><td>${item.name}</td><td>${item.desc}</td></tr>`).join('')}
            </table>

            <h3 class="font-bold my-5">JianghuJS项目：</h3>
            <table border class="project-table">
            ${jianghujsinfo_tips.map(item => `<tr><td>${item.name}</td><td>${item.desc}</td></tr>`).join('')}
            </table>

            <h3 class="font-bold my-5">Docker项目：</h3>
            <table border class="project-table w-full">
            ${dockerinfo_tips.map(item => `<tr><td>${item.name}</td><td>${item.desc}</td></tr>`).join('')}
            </table>

            <h3 class="font-bold my-5">数据库：</h3>
            <p style="color: #efefef; font-size: 14px;">提示：由于数据库存储的单位是页，MySQL的InnoDB引擎默认页大小是16KB。如果你添加的数据小于这个数值，可能不会立即反映在数据库大小上。</p>
            <table border class="w-full">
            ${mysqlinfo_tips.map(item => `<tr><td>${item.name}</td><td>${item.desc}</td></tr>`).join('')}
            </table>
          </div>
        </div>
      </div>
    `;
  } else {
    bodyHtml = `
      <div class="panel_report bgw p-5">
        <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">服务器运行报告</h3>
        </div>
        <div class="mx-auto leading-10 plr15">
          <div class="text-center mt-5">暂无报告内容</div>
        </div>
      </div>
    `;
  }
  
  $("#hostdetail-con").html(bodyHtml);
}

// <========================== 弹框内容 End 


// 弹框获取数据方法 Start ==========================>

// 获取主机概览数据
function getDetailHostSummaryData(host_id) {
  $.post('/host/detail' ,{host_id:host_id}, function(data) {
    const host_detail = data.data;
    let { ip, host_info, cpu_info, mem_info, net_info, load_avg, process_rank = [], ssh_user_list = [] } = host_detail;
    // 主机信息
    $('.detailHostSummary .hostName').text(host_detail['host_name']);
    $('.detailHostSummary .ip').text(ip);
    $('.detailHostSummary .platform').text(`${host_info['platform']} ${host_info['platformVersion']}`).attr('title', `${host_info['platform']} ${host_info['platformVersion']}`);
    $('.detailHostSummary .runDay').text(host_info['runDay']);
    $('.detailHostSummary .jhMonitorVersion').text(host_info['jhMonitorVersion']);
    $('.detailHostSummary .modelName').text(cpu_info['modelName']).attr('title', cpu_info['modelName']);
    $('.detailHostSummary .loadAvg').text(`${load_avg['1min']} / ${load_avg['5min']} / ${load_avg['15min']}`);
    $('.detailHostSummary .upTime').text(host_info['upTimeStr']);

    // 负载状态 
    var loadColor, occupy, averageText = '';
    let avg = load_avg['1min']
    let max = load_avg['max'] || 1
    occupy = Math.round((avg / max) * 100);
    if (occupy > 100) Occupy = 100;
    if (occupy <= 30) {
        loadColor = '#20a53a';
        averageText = '运行流畅';
    } else if (occupy <= 70) {
        loadColor = '#6ea520';
        averageText = '运行正常';
    } else if (occupy <= 90) {
        loadColor = '#ff9900';
        averageText = '运行缓慢';
    } else {
        loadColor = '#dd2f00';
        averageText = '运行堵塞';
    }
    $("#LoadList").find('.circle').css("background", loadColor);
    $("#LoadList").find('.mask').css({ "color": loadColor });
    $("#LoadList .mask").html("<span id='Load'></span>%");
    $('#Load').html(occupy);
    $('#LoadState').html('<span>' + averageText + '</span>');

    // CPU
    $("#cpu").html(cpu_info.percent);
    $("#cpuState").html(cpu_info.cpuCount + ' 核心');

    // 内存
    $("#memory").html(getPercent(mem_info.used, mem_info.total));
    $("#memoryState").html(parseInt(mem_info.used) + '/' + parseInt(mem_info.total) + ' (MB)');

    setImg();

    // 进程占用TOP10
    // ! 模拟process_rank数据
    process_rank = [
      { name: 'nginx', cpu: '0.1%', mem: '0.1%', net: '0.1%', disk: '0.1%' },
      { name: 'php-fpm', cpu: '0.1%', mem: '0.1%', net: '0.1%', disk: '0.1%' },
      { name: 'mysql', cpu: '0.1%', mem: '0.1%', net: '0.1%', disk: '0.1%' },
      { name: 'redis', cpu: '0.1%', mem: '0.1%', net: '0.1%', disk: '0.1%' },
      { name: 'php-fpm', cpu: '0.1%', mem: '0.1%', net: '0.1%', disk: '0.1%' }
    ]
    let processRankBody = '';
    for(let process_item of process_rank) {
      processRankBody += `
        <tr>
          <td>${process_item.name}</td>
          <td>${process_item.cpu}</td>
          <td>${process_item.mem}</td>
          <td>${process_item.net}</td>
          <td>${process_item.disk}</td>
        </tr>
      `;
    }
    $("#processRankBody").html(processRankBody);

    // 流量图
    updateDetailHostSummaryNetChart(net_info);

    // 告警事件
    // updateDetailHostSummaryAlarm(host_id);

    // 在线的SSH用户
    // ! 模拟sshUser数据
    ssh_user_list = [
      { user: 'root', terminal: 'pts/0', loginTime: '2021-10-10 10:10:10', loginIp: '192.168.3.1'},
      { user: 'user1', terminal: 'pts/1', loginTime: '2021-10-10 10:10:10', loginIp: '192.168.3.2'}
    ]
    let sshUserBody = '';
    for(let ssh_user of ssh_user_list) {
      sshUserBody += `
        <tr>
          <td>${ssh_user.user}</td>
          <td>${ssh_user.terminal}</td>
          <td>${ssh_user.loginTime}</td>
          <td>${ssh_user.loginIp}</td>
        </tr>
      `;
    }
    $("#sshUserBody").html(sshUserBody);
  },'json');
}

/**
 * 图表相关
var netChart = {}
*/
function initDetailHostSummaryNetChart(net_info) {
  netChart = {
    xData: [],
    yData: [],
    zData: [],
    myChartNetwork: echarts.init(document.getElementById('netImg')),
    init() {
      // 默认填充空白图标
      for (var i = 8; i >= 0; i--) {
        var time = (new Date()).getTime();
        this.xData.push(this.format(time - (i * 3 * 1000)));
        this.yData.push(0);
        this.zData.push(0);
      }
      // 指定图表的配置项和数据
      let option = {
          title: {
              text: lan.index.interface_net,
              left: 'center',
              textStyle: {
                  color: '#888888',
                  fontStyle: 'normal',
                  fontFamily: lan.index.net_font,
                  fontSize: 16,
              }
          },
          tooltip: {
              trigger: 'axis'
          },
          legend: {
              data: [lan.index.net_up, lan.index.net_down],
              bottom: '2%'
          },
          grid: {
            left: '2%',
            right: '2%',
            containLabel: true
          },
          xAxis: {
              type: 'category',
              boundaryGap: false,
              data: this.xData,
              axisLine: {
                  lineStyle: {
                      color: "#666"
                  }
              }
          },
          yAxis: {
              name: lan.index.unit + 'KB/s',
              splitLine: {
                  lineStyle: {
                      color: "#eee"
                  }
              },
              axisLine: {
                  lineStyle: {
                      color: "#666"
                  }
              }
          },
          series: [{
              name: lan.index.net_up,
              type: 'line',
              data: this.yData,
              smooth: true,
              showSymbol: false,
              symbol: 'circle',
              symbolSize: 6,
              areaStyle: {
                  normal: {
                      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                          offset: 0,
                          color: 'rgba(255, 140, 0,0.5)'
                      }, {
                          offset: 1,
                          color: 'rgba(255, 140, 0,0.8)'
                      }], false)
                  }
              },
              itemStyle: {
                  normal: {
                      color: '#f7b851'
                  }
              },
              lineStyle: {
                  normal: {
                      width: 1
                  }
              }
          }, {
              name: lan.index.net_down,
              type: 'line',
              data: this.zData,
              smooth: true,
              showSymbol: false,
              symbol: 'circle',
              symbolSize: 6,
              areaStyle: {
                  normal: {
                      color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{
                          offset: 0,
                          color: 'rgba(30, 144, 255,0.5)'
                      }, {
                          offset: 1,
                          color: 'rgba(30, 144, 255,0.8)'
                      }], false)
                  }
              },
              itemStyle: {
                  normal: {
                      color: '#52a9ff'
                  }
              },
              lineStyle: {
                  normal: {
                      width: 1
                  }
              }
          }]
      };
      // 使用刚指定的配置项和数据显示图表。
      this.myChartNetwork.setOption(option);
      window.addEventListener("resize", () => {
          this.myChartNetwork.resize();
      });
    },
    getTime() {
      var now = new Date();
      var hour = now.getHours();
      var minute = now.getMinutes();
      var second = now.getSeconds();
      if (minute < 10) {
          minute = "0" + minute;
      }
      if (second < 10) {
          second = "0" + second;
      }
      var nowdate = hour + ":" + minute + ":" + second;
      return nowdate;
    },
    ts(m) { return m < 10 ? '0' + m : m },
    format(sjc) {
      var time = new Date(sjc);
      var h = time.getHours();
      var mm = time.getMinutes();
      var s = time.getSeconds();
      return this.ts(h) + ':' + this.ts(mm) + ':' + this.ts(s);
    },
    addData(upNet, downNet, shift) {
      this.xData.push(this.getTime());
      this.yData.push(upNet);
      this.zData.push(downNet);
      if (shift) {
          this.xData.shift();
          this.yData.shift();
          this.zData.shift();
      }
    },
    updateOption() {
      this.myChartNetwork.setOption({
          xAxis: {
              data: this.xData
          },
          series: [{
              name: lan.index.net_up,
              data: this.yData
          }, {
              name: lan.index.net_down,
              data: this.zData
          }]
      });
      this.myChartNetwork.resize();
    }
  }
  netChart.init();
}

/**
 * 更新网络图表数据
 * @param {*} net_info 
 */
function updateDetailHostSummaryNetChart(net_info) {
  if (net_info) {
    const { up, down, upTotal, downTotal } = net_info;
    $("#upSpeed").html(up + ' KB');
    $("#downSpeed").html(down + ' KB');
    $("#downAll").html(toSize(downTotal));
    $("#upAll").html(toSize(upTotal));
    netChart.addData(up, down, true);
  }
  netChart.updateOption();
}

/**
 * 更新告警事件
 * @param {*} host_id 
 */
function updateDetailHostSummaryAlarm(host_id) {
  $.post('/host/alarm', {host_id}, function(data) {
    const alarmList = data.data;
    let alarmBody = '';
    for(let alarmItem of alarmList) {
      alarmBody += `
        <tr>
          <td>${alarmItem.alarm_content}</td>
          <td>${alarmItem.addtime}</td>
          <td>${alarmItem.alarm_type}</td>
          <td class='text-right border-none'>
            <a href='javascript:;' class='btlink' onclick='detailAlarmInfo(${alarmItem.id})'>详情</a>
          </td>
        </tr>
      `;
    }
    $("#alarmBody").html(alarmBody);
  }, 'json');
}

function initDetailHostBaseMonitorChart() {
  initDetailHostBaseMonitorAvgLoadChart();
  initDetailHostBaseMonitorCPUChart();
  initDetailHostBaseMonitorMemChart();
  initDetailHostBaseMonitorDiskIoChart();
  initDetailHostBaseMonitorNetIoChart();
  
  $(".st").unbind().hover(function(){
    $(this).next().show();
  },function(){
    $(this).next().hide();
    $(this).next().hover(function(){
      $(this).show();
    },function(){
      $(this).hide();
    })
  })
  $(".searcTime .gt").unbind().click(function(){
    $(this).addClass("on").siblings().removeClass("on");
  })
  $(".loadbtn").click(function(){
    $(this).parents(".searcTime").find("span").removeClass("on");
    $(this).parents(".searcTime").find(".st").addClass("on");
    var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
    var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
    b = Math.round(b);
    e = Math.round(e);
    updateDetailHostBaseMonitorAvgLoadChartData(b,e);
  })
  $(".cpubtn").click(function(){
    $(this).parents(".searcTime").find("span").removeClass("on");
    $(this).parents(".searcTime").find(".st").addClass("on");
    var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
    var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
    b = Math.round(b);
    e = Math.round(e);
    updateDetailHostBaseMonitorCPUChartData(b, e);
  })
  $(".membtn").click(function(){
    $(this).parents(".searcTime").find("span").removeClass("on");
    $(this).parents(".searcTime").find(".st").addClass("on");
    var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
    var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
    b = Math.round(b);
    e = Math.round(e);
    updateDetailHostBaseMonitorMemChartData(b,e);
  })
  $(".diskbtn").click(function(){
    $(this).parents(".searcTime").find("span").removeClass("on");
    $(this).parents(".searcTime").find(".st").addClass("on");
    var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
    var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
    b = Math.round(b);
    e = Math.round(e);
    updateDetailHostBaseMonitorDiskIoChartData(b,e);
  })
  $(".networkbtn").click(function(){
    $(this).parents(".searcTime").find("span").removeClass("on");
    $(this).parents(".searcTime").find(".st").addClass("on");
    var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
    var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
    b = Math.round(b);
    e = Math.round(e);
    updateDetailHostBaseMonitorNetIoChartData(b,e);
  })
}

function updateDetailHostBaseMonitorChartData() {
	Wday(0,'getload');
  Wday(0,'cpu');
  Wday(0,'mem');
  Wday(0,'disk');
  Wday(0,'network');
}

//指定天数
function Wday(day, name){
	var now = (new Date()).getTime();
	if(day==0){
		var s = (new Date(getToday() + " 00:00:01").getTime())/1000;
			s = Math.round(s);
		var e = Math.round(now);
	}
	if(day==1){
		var s = (new Date(getBeforeDate(day) + " 00:00:01").getTime())/1000;
		var e = (new Date(getBeforeDate(day) + " 23:59:59").getTime())/1000;
		s = Math.round(s);
		e = Math.round(e);
	}
	else{
		var s = (new Date(getBeforeDate(day) + " 00:00:01").getTime())/1000;
			s = Math.round(s);
		var e = Math.round(now);
	}
	switch (name){
		case "getload":
			updateDetailHostBaseMonitorAvgLoadChartData(s,e);
			break;
		case "cpu":
			updateDetailHostBaseMonitorCPUChartData(s, e);
			break;
		case "mem":
			updateDetailHostBaseMonitorMemChartData(s,e);
			break;
		case "disk":
			updateDetailHostBaseMonitorDiskIoChartData(s,e);
			break;
		case "network":
			updateDetailHostBaseMonitorNetIoChartData(s,e);
			break;
	}
}


// 平均负载图表
var avgLoadChart = {}
function initDetailHostBaseMonitorAvgLoadChart() {
  let avg_load_history = [
  ]
  avgLoadChart = {
    aData: [],
    bData: [],
    xData: [],
    yData: [],
    zData: [],
    myChart: echarts.init(document.getElementById('avgloadview')),
    init() {
      this.setData(avg_load_history);
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    },
    setData(d) {
      this.xData = [];
      this.yData = [];
      this.zData = [];
      this.aData = [];
      this.bData = [];
      for(var i = 0; i < d.length; i++){
        this.xData.push(d[i].addtime);
        this.yData.push(d[i].pro);
        this.zData.push(d[i].one);
        this.aData.push(d[i].five);
        this.bData.push(d[i].fifteen);
      }
      let option = {
        animation: false,
        tooltip: {
          trigger: 'axis',
          axisPointer: {
                    type: 'cross'
                }
        },
        legend: {
          data:['1分钟','5分钟','15分钟'],
          right:'16%',
          top:'10px'
        },
        axisPointer: {
          link: {xAxisIndex: 'all'},
          lineStyle: {
            color: '#aaaa',
            width: 1
          }
        },
        grid: [{ // 直角坐标系内绘图网格
            top: '60px',
            left: '5%',
            right: '55%',
            width: '40%',
            height: 'auto'
          },
          {
            top: '60px',
            left: '55%',
            width: '40%',
            height: 'auto'
          }
        ],
        xAxis: [
  
          { // 直角坐标系grid的x轴
            type: 'category',
            axisLine: {
              lineStyle: {
                color: '#666'
              }
            },
            data: this.xData
          },
          { // 直角坐标系grid的x轴
            type: 'category',
            gridIndex: 1,
            axisLine: {
              lineStyle: {
                color: '#666'
              }
            },
            data: this.xData
          },
        ],
        yAxis: [{
            scale: true,
            name: lan.public.pre,
            boundaryGap: [0, '100%'],
            min:0,
            max: 100,
            splitLine: { // y轴网格显示
              show: true,
              lineStyle:{
                color:"#ddd"
              }
            },
            axisLine:{
              lineStyle:{
                color:"#666"
              }
            }
          },
          {
            scale: true,
            name: '负载详情',
            gridIndex: 1,
            splitLine: { // y轴网格显示
              show: true,
              lineStyle:{
                color:"#ddd"
              }
            },
            axisLine:{
              lineStyle:{
                color:"#666"
              }
            }
          },
        ],
        dataZoom: [{
          type: 'inside',
          start: 0,
          end: 100,
          zoomLock:true
        }, {
          xAxisIndex: [0, 1],
                type: 'slider',
          start: 0,
          end: 100,
          handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
          handleSize: '80%',
          handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
          }
        }],
        series: [
          {
            name: '资源使用率%',
            type: 'line',
            lineStyle: {
              normal: {
                width: 2,
                color: 'rgb(255, 140, 0)'
              }
            },
            itemStyle: {
              normal: {
                color: 'rgb(255, 140, 0)'
              }
            },
            data: this.yData
          },
          {
            xAxisIndex: 1,
            yAxisIndex: 1,
            name: '1分钟',
            type: 'line',
            lineStyle: {
              normal: {
                width: 2,
                color: 'rgb(30, 144, 255)'
              }
            },
            itemStyle: {
              normal: {
                color: 'rgb(30, 144, 255)'
              }
            },
            data: this.zData
          },
          {
            xAxisIndex: 1,
            yAxisIndex: 1,
            name: '5分钟',
            type: 'line',
            lineStyle: {
              normal: {
                width: 2,
                color: 'rgb(0, 178, 45)'
              }
            },
            itemStyle: {
              normal: {
                color: 'rgb(0, 178, 45)'
              }
            },
            data: this.aData
          },
          {
            xAxisIndex: 1,
            yAxisIndex: 1,
            name: '15分钟',
            type: 'line',
            lineStyle: {
              normal: {
                width: 2,
                color: 'rgb(147, 38, 255)'
              }
            },
            itemStyle: {
              normal: {
                color: 'rgb(147, 38, 255)'
              }
            },
            data: this.bData
          }
        ],
        textStyle: {
          color: '#666',
          fontSize: 12
        }
      };
      this.myChart.setOption(option);
      this.myChart.resize();
    }
  }
  avgLoadChart.init();
}

/**
 * 更新平均负载图表数据
 * @param {*} s 
 * @param {*} e 
 */
function updateDetailHostBaseMonitorAvgLoadChartData(s, e) {
  $.post('/host/get_host_load_average', 'host_id=' + detailHostId + '&start='+s+'&end='+e,function(rdata){
    let avg_load_history = rdata.map(item => {
      let itemLoadAvg = JSON.parse(item['load_avg'] || '{}');
      let itemCpuInfo = JSON.parse(item['cpu_info'] || '{}');
      return {
        id: item.id,
        pro: itemCpuInfo.percent,
        one: itemLoadAvg['1min'],
        five: itemLoadAvg['5min'],
        fifteen: itemLoadAvg['15min'],
        addtime: item.addtime
      }
    });
    avgLoadChart.setData(avg_load_history);
  }, 'json');
}

// CPU图表
var cpuChart = {}
function initDetailHostBaseMonitorCPUChart() {
  let cpu_history = [
  ]

  cpuChart = {
    xData: [],
    yData: [],
    myChart: echarts.init(document.getElementById('cupview')),
    init() {
      this.setData(cpu_history);
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    },
    setData(d) {
      this.xData = [];
      this.yData = [];

      for(var i = 0; i < d.length; i++){
        
        this.xData.push(d[i].addtime);
        this.yData.push(d[i].pro);
      }
      let option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: '{b}<br />{a}: {c}%'
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: this.xData,
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        yAxis: {
          type: 'value',
          name: lan.public.pre,
          boundaryGap: [0, '100%'],
          min:0,
          max: 100,
          splitLine:{
            lineStyle:{
              color:"#ddd"
            }
          },
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        dataZoom: [{
          type: 'inside',
          start: 0,
          end: 100,
          zoomLock:true
        }, {
          start: 0,
          end: 100,
          handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
          handleSize: '80%',
          handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
          }
        }],
        series: [
          {
            name:'CPU',
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
              normal: {
                color: 'rgb(0, 153, 238)'
              }
            },
            data: this.yData
          }
        ]
      };
      this.myChart.setOption(option);
    }
  }
  cpuChart.init();
}

// 更新CPU图表数据
function updateDetailHostBaseMonitorCPUChartData(s, e) {
  $.post('/host/get_host_cpu_io', 'host_id=' + detailHostId + '&start='+s+'&end='+e,function(rdata){
    let cpu_history = rdata.map(item => {
      let itemCpuInfo = JSON.parse(item['cpu_info'] || '{}');
      return {
        id: item.id,
        pro: itemCpuInfo.percent,
        addtime: item.addtime
      }
    });
    cpuChart.setData(cpu_history);
  }, 'json');
}

// 内存图表
var memChart = {}
function initDetailHostBaseMonitorMemChart() {
  let mem_history = [
  ]

  memChart = {
    xData: [],
    zData: [],
    myChart: echarts.init(document.getElementById('memview')),
    init() {
      this.setData(mem_history);
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    },
    setData(d) {
      this.xData = [];
      this.zData = [];

      for(var i = 0; i < d.length; i++){
        this.xData.push(d[i].addtime);
        // this.yData.push(d[i].pro);
        this.zData.push(d[i].mem);
      }
      let option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: '{b}<br />{a}: {c}%'
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: this.xData,
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        yAxis: {
          type: 'value',
          name: lan.public.pre,
          boundaryGap: [0, '100%'],
          min:0,
          max: 100,
          splitLine:{
            lineStyle:{
              color:"#ddd"
            }
          },
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        dataZoom: [{
          type: 'inside',
          start: 0,
          end: 100,
          zoomLock:true
        }, {
          start: 0,
          end: 100,
          handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
          handleSize: '80%',
          handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
          }
        }],
        series: [
          {
            name:lan.index.process_mem,
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
              normal: {
                color: 'rgb(0, 153, 238)'
              }
            },
            data: this.zData
          }
        ]
      };
      this.myChart.setOption(option);
    }
  }
  memChart.init();
}

// 更新内存图表数据
function updateDetailHostBaseMonitorMemChartData(s, e) {
  $.post('/host/get_host_cpu_io', 'host_id=' + detailHostId + '&start='+s+'&end='+e,function(rdata){
    let mem_history = rdata.map(item => {
      let itemMemInfo = JSON.parse(item['mem_info'] || '{}');
      return {
        id: item.id,
        pro: itemMemInfo.percent,
        mem: itemMemInfo.usedPercent,
        addtime: item.addtime
      }
    });
    memChart.setData(mem_history);
  }, 'json');
}

// 磁盘IO图表
var diskIoChart = {}
function initDetailHostBaseMonitorDiskIoChart() {
  let disk_io_history = [
  ]

  diskIoChart = {
    rData: [],
    wData: [],
    xData: [],
    myChart: echarts.init(document.getElementById('diskview')),
    init() {
      this.setData(disk_io_history);
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    },
    setData(d) {
      this.rData = [];
      this.wData = [];
      this.xData = [];
      for(var i = 0; i < d.length; i++){
        this.rData.push((d[i].read_bytes/1024/60).toFixed(3));
        this.wData.push((d[i].write_bytes/1024/60).toFixed(3));
        this.xData.push(d[i].addtime);
      }
      let option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter:"时间：{b0}<br />{a0}: {c0} Kb/s<br />{a1}: {c1} Kb/s", 
        },
        legend: {
          data:['读取字节数','写入字节数']
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: this.xData,
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        yAxis: {
          type: 'value',
          name: '单位:KB/s',
          boundaryGap: [0, '100%'],
          splitLine:{
            lineStyle:{
              color:"#ddd"
            }
          },
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        dataZoom: [{
          type: 'inside',
          start: 0,
          end: 100,
          zoomLock:true
        }, {
          start: 0,
          end: 100,
          handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
          handleSize: '80%',
          handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
          }
        }],
        series: [
          {
            name:'读取字节数',
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
              normal: {
                color: 'rgb(255, 70, 131)'
              }
            },
            data: this.rData
          },
          {
            name:'写入字节数',
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
              normal: {
                color: 'rgba(46, 165, 186, .7)'
              }
            },
            data: this.wData
          }
        ]
      };
      this.myChart.setOption(option);
    }
  }
  diskIoChart.init();
}

// 更新磁盘IO图表数据
function updateDetailHostBaseMonitorDiskIoChartData(s, e) {
  $.post('/host/get_host_disk_io', 'host_id=' + detailHostId + '&start='+s+'&end='+e,function(rdata){
    let disk_io_history = rdata.map(item => {
      let itemDiskInfoList = JSON.parse(item['disk_info'] || '[]');
      let itemDiskInfo = itemDiskInfoList[0] || {};
      return {
        id: item.id,
        read_bytes: itemDiskInfo.readSpeed,
        write_bytes: itemDiskInfo.writeSpeed,
        addtime: item.addtime
      }
    });
    diskIoChart.setData(disk_io_history);
  }, 'json');
}

// 网络IO图表
var netIoChart = {}
function initDetailHostBaseMonitorNetIoChart() {
  // ! 模拟数据
  let net_io_history = [
    {"id": 168905, "up": 74.066, "down": 82.152, "total_up": 810516284, "total_down": 941393246, "down_packets": 3613980, "up_packets": 3192491, "addtime": "11/03 00:00"},
    {"id": 168905, "up": 74.066, "down": 82.152, "total_up": 810516284, "total_down": 941393246, "down_packets": 3613980, "up_packets": 3192491, "addtime": "11/03 00:00"},
    {"id": 168905, "up": 74.066, "down": 82.152, "total_up": 810516284, "total_down": 941393246, "down_packets": 3613980, "up_packets": 3192491, "addtime": "11/03 00:00"}
  ]

  netIoChart = {
    aData: [],
    bData: [],
    cData: [],
    dData: [],
    xData: [],
    yData: [],
    zData: [],
    myChart: echarts.init(document.getElementById('network')),
    init() {
      this.setData(net_io_history);
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    },
    setData(d) {
      this.aData = [];
      this.bData = [];
      this.cData = [];
      this.dData = [];
      this.xData = [];
      this.yData = [];
      this.zData = [];

      for(var i = 0; i < d.length; i++){
        this.aData.push(d[i].total_up);
        this.bData.push(d[i].total_down);
        this.cData.push(d[i].down_packets);
        this.dData.push(d[i].up_packets);
        this.xData.push(d[i].addtime);
        this.yData.push(d[i].up);
        this.zData.push(d[i].down);
      }
      let option = {
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          }
        },
        legend: {
          data:[lan.index.net_up,lan.index.net_down]
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: this.xData,
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        yAxis: {
          type: 'value',
          name: lan.index.unit+':KB/s',
          boundaryGap: [0, '100%'],
          splitLine:{
            lineStyle:{
              color:"#ddd"
            }
          },
          axisLine:{
            lineStyle:{
              color:"#666"
            }
          }
        },
        dataZoom: [{
          type: 'inside',
          start: 0,
          end: 100,
          zoomLock:true
        }, {
          xAxisIndex: [0, 1],
                type: 'slider',
          start: 0,
          end: 100,
          handleIcon: 'M10.7,11.9v-1.3H9.3v1.3c-4.9,0.3-8.8,4.4-8.8,9.4c0,5,3.9,9.1,8.8,9.4v1.3h1.3v-1.3c4.9-0.3,8.8-4.4,8.8-9.4C19.5,16.3,15.6,12.2,10.7,11.9z M13.3,24.4H6.7V23h6.6V24.4z M13.3,19.6H6.7v-1.4h6.6V19.6z',
          handleSize: '80%',
          handleStyle: {
            color: '#fff',
            shadowBlur: 3,
            shadowColor: 'rgba(0, 0, 0, 0.6)',
            shadowOffsetX: 2,
            shadowOffsetY: 2
          }
        }],
        series: [
          {
            name:lan.index.net_up,
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
              normal: {
                color: 'rgb(255, 140, 0)'
              }
            },
            data: this.yData
          },
          {
            name:lan.index.net_down,
            type:'line',
            smooth:true,
            symbol: 'none',
            sampling: 'average',
            itemStyle: {
              normal: {
                color: 'rgb(30, 144, 255)'
              }
            },
            data: this.zData
          }
        ]
      };
      this.myChart.setOption(option);
    }
  }
  netIoChart.init();
}

// 更新网络IO图表数据
function updateDetailHostBaseMonitorNetIoChartData(s, e) {
  $.post('/host/get_host_network_io', 'host_id=' + detailHostId + '&start='+s+'&end='+e,function(rdata){
    let net_io_history = rdata.map(item => {
      let itemNetIoList = JSON.parse(item['net_info'] || '[]');
      let itemNetIo = itemNetIoList[0] || {};
      return {
        id: item.id,
        up: itemNetIo.sent_per_second,
        down: itemNetIo.recv_per_second,
        total_up: itemNetIo.sent,
        total_down: itemNetIo.recv,
        down_packets: itemNetIo.recv_packets,
        up_packets: itemNetIo.sent_packets,
        addtime: item.addtime
      }
    });
    netIoChart.setData(net_io_history);
  }, 'json');
}

// 日志文件列表
function getDetailHostLogMonitorData(host_id) {
  loadT = layer.load();
  bodyHtml = '';

  host = hostList.find(item => item.host_id == host_id);
  if (!host) {
    layer.close(loadT);
    return;
  }
  const { ip } = host;

  $.post('/host/get_log_path_list', 'host_ip=' + ip,function(rdata){
    
    let logFileBody = '';
    if (rdata.length == 0) {
      logFileBody = `
        <li class="log-path-item px-5 log-path cursor-pointer whitespace-nowrap overflow-hidden text-ellipsis">暂无日志文件</li>
      `;
    } else {
      for(let logFile of rdata) {
        logFileBody += `
          <li class="log-path-item px-5 log-path cursor-pointer whitespace-nowrap overflow-hidden text-ellipsis"
            title="${logFile.path}"
          >${logFile.path}</li>  
        `;
      }
    }
    $("#logFileBody").html(logFileBody);
    layer.close(loadT);


    $(".log-path-item").click(function() {
      const logPath = $(this).text();
      $(this).addClass('bg-slate-50 text-green-500').siblings().removeClass('bg-slate-50 text-green-500');
      getDetailHostLogMonitorDetailData(ip, logPath);
    });
    
    // 默认选中第一个
    if ($(".log-path-item").length > 0) {
      $(".log-path-item").eq(0).click();
    }
  }, 'json');
  

}

// 日志详情
function getDetailHostLogMonitorDetailData(host_ip, logPath) {
  loadT = layer.load();
  $.post('/host/get_log_detail', `host_ip=${host_ip}&log_path=${logPath}`,function(rdata){
    let logFileDetail = JSON.parse(rdata);
    $("#logFileDetail .path").text(logPath);
    // $("#logFileDetail .size").text(logFileDetail.size);
    // $("#logFileDetail .permission").text(logFileDetail.permission);
    $("#logFileDetail .modifyTime").text(logFileDetail.last_updated || '暂无');
    $("#logFileDetail .content").html(logFileDetail.log_content.length == 0? '日志内容为空': logFileDetail.log_content.map(item => `
      <p>
        <span class="text-gray-400">${item.create_time} - </span>
        <span>${item.content}</span>
      </p>
      <hr class="my-4">
    `));
    layer.close(loadT);
  });
}

// 主机SSH登陆信息
function getDetailHostSysMonitorData() {
  let ssh_login_list = [
    {id: 1, hostName: 'HOST1', ip: '192.168.1.3', port: 22, username: 'root', address: 'Guangdong', 'login_status': '', login_time: '2021-10-10 10:10:10'},
    {id: 1, hostName: 'HOST1', ip: '192.168.1.3', port: 22, username: 'root', address: 'Guangdong', 'login_status': '', login_time: '2021-10-10 10:10:10'},
    {id: 1, hostName: 'HOST1', ip: '192.168.1.3', port: 22, username: 'root', address: 'Guangdong', 'login_status': '', login_time: '2021-10-10 10:10:10'},
  ]
  let sshLoginBody = '';
  for(let sshLogin of ssh_login_list) {
    sshLoginBody += `
      <tr>
        <td>${sshLogin.hostName}</td>
        <td>${sshLogin.ip}</td>
        <td>${sshLogin.port}</td>
        <td>${sshLogin.username}</td>
        <td>${sshLogin.address}</td>
        <td>${sshLogin.login_time}</td>
      </tr>
    `;
  }
  $("#sshLoginBody").html(sshLoginBody);

  let ssh_command_list = [
    {id: 1, user: 'root', command: 'ls', status: 'success', run_time: '2021-10-10 10:10:10'},
    {id: 2, user: 'root', command: 'ls', status: 'success', run_time: '2021-10-10 10:10:10'},
    {id: 3, user: 'root', command: 'ls', status: 'success', run_time: '2021-10-10 10:10:10'},
  ]
  let sshCommandBody = '';
  for(let sshCommand of ssh_command_list) {
    sshCommandBody += `
      <tr>
        <td>${sshCommand.user}</td>
        <td>${sshCommand.run_time}</td>
        <td>${sshCommand.command}</td>
      </tr>
    `;
  }
  $("#sshCommandBody").html(sshCommandBody);
}
  

// <========================== 弹框获取数据方法 End


// 其他方法 ==========================>

function setImg() {
  $('.circle').each(function(index, el) {
      var num = $(this).find('span').text() * 3.6;
      if (num <= 180) {
          $(this).find('.left').css('transform', "rotate(0deg)");
          $(this).find('.right').css('transform', "rotate(" + num + "deg)");
      } else {
          $(this).find('.right').css('transform', "rotate(180deg)");
          $(this).find('.left').css('transform', "rotate(" + (num - 180) + "deg)");
      };
  });

  $('.diskbox .mask').unbind();
  $('.diskbox .mask').hover(function() {
      layer.closeAll('tips');
      var that = this;
      var conterError = $(this).attr("data");
      layer.tips(conterError, that, { time: 0, tips: [1, '#999'] });
  }, function() {
      layer.closeAll('tips');
  });
}

// <========================== 其他方法 End
