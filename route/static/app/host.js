/**
 * 主机数据列表
 * @param {Number} page   当前页
 * @param {String} search 搜索条件
 */
function getWeb(page, search, type_id) {
	search = $("#SearchValue").prop("value");
	page = page == undefined ? '1':page;
	var order = getCookie('order');
	if(order){
		order = '&order=' + order;
	} else {
		order = '';
	}

	var type = '';
	if ( typeof(type_id) == 'undefined' ){
		type = '&type_id=0';
	} else {
		type = '&type_id='+type_id;
	}

	var sUrl = '/host/list';
	var pdata = 'limit=1000&p=' + page + '&search=' + search + order + type;
	var loadT = layer.load();
	//取回数据
	$.post(sUrl, pdata, function(data) {
		layer.close(loadT);
		//构造数据列表
		var body = '';
		$("#webBody").html(body);
		for (var i = 0; i < data.data.length; i++) {

			// 当前主机状态
			if (data.data[i].status == '正在运行' || data.data[i].status == '1') {
				var status = "<a href='javascript:;' title='停用这个主机' onclick=\"webStop(" + data.data[i].id + ",'" + data.data[i].name + "')\" class='btn-defsult'><span style='color:rgb(92, 184, 92)'>运行中</span><span style='color:rgb(92, 184, 92)' class='glyphicon glyphicon-play'></span></a>";
			} else {
				var status = "<a href='javascript:;' title='启用这个主机' onclick=\"webStart(" + data.data[i].id + ",'" + data.data[i].name + "')\" class='btn-defsult'><span style='color:red'>已停止</span><span style='color:rgb(255, 0, 0);' class='glyphicon glyphicon-pause'></span></a>";
			}

      // 流量
      let net_speed = '';
      let net_total = '';
      if (data.data[i].net_info && data.data[i].net_info.length > 0) {
        net_speed += "<div>" + (data.data[i].net_info[0]['sent_per_second'] || '') + "</div>";
        net_speed += "<div>" + (data.data[i].net_info[0]['recv_per_second'] || '') + "</div>";
        net_total += "<div>" + (data.data[i].net_info[0]['sent'] || '') + "</div>";
        net_total += "<div>" + (data.data[i].net_info[0]['recv'] || '') + "</div>";
      }

      // 磁盘
      let disk_speed = '';
      let disk_status = '';
			if (data.data[i].disk_info && data.data[i].disk_info.length > 0) {
        for (let j = 0; j < data.data[i].disk_info.length; j++) {
          disk_speed += "<div>" + (data.data[i].disk_info[j]['read_per_second'] || '') + "</div>";
          disk_speed += "<div>" + (data.data[i].disk_info[j]['write_per_second'] || '') + "</div>";
          if(data.data[i].disk_info[j]['status']) {
            disk_status = "<a href='javascript:;' title='紧张' onclick=\"webStop(" + data.data[i].id + ",'" + data.data[i].name + "')\" class='btn-defsult'><span style='color:rgb(92, 184, 92)'>充裕</span><span style='color:rgb(92, 184, 92)' class='glyphicon glyphicon-play'></span></a>";
          } else {
            disk_status = "<a href='javascript:;' title='充裕' onclick=\"webStart(" + data.data[i].id + ",'" + data.data[i].name + "')\" class='btn-defsult'><span style='color:red'>紧张</span><span style='color:rgb(255, 0, 0);' class='glyphicon glyphicon-pause'></span></a>";
          }
        }
      }

			body = "<tr><td><input type='checkbox' name='id' title='"+data.data[i].host_name+"' onclick='checkSelect();' value='" + data.data[i].id + "'></td>\
					<td>\
						<a class='btlink webtips' href='http://"+data.data[i].name+"' onclick=\"webEdit(" + data.data[i].id + ",'" + data.data[i].name + "','" + data.data[i].edate + "','" + data.data[i].addtime + "',event)\" title='"+data.data[i].name+"'>" 
							+ data.data[i].host_name + '/' + data.data[i].ip + "\
            </a>\
          </td>\
					<td>" + status + "</td>\
					<td>" + (data.data[i]['host_group_name']) + "</td>\
					<td>" + (data.data[i]['load_avg']['1min']) + "</td>\
					<td>" + (data.data[i]['cpu_info']['percent']) + "</td>\
					<td>" + (data.data[i]['mem_info']['percent']) + "</td>\
					<td>" + net_speed + "</td>\
					<td>" + net_total + "</td>\
					<td>" + disk_speed + "</td>\
					<td>" + disk_status + "</td>\
					<td style='text-align:right; color:#bbb'>\
					    <a href='javascript:;' class='btlink' onclick=\"openHostDetail('" + data.data[i].host_id + "','" + data.data[i].host_name + "','" + data.data[i].edate + "','" + data.data[i].addtime + "')\">详情</a>\
					    | <a href='javascript:;' class='btlink' onclick=\"hostDelete('" + data.data[i].host_id + "','" + data.data[i].host_name + "')\" title='删除主机'>删除</a>\
					</td></tr>"
			
			$("#webBody").append(body);
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
		// $("#webPage").html('<div class="site_type"><span>主机分类:</span><select class="bt-input-text mr5" style="width:100px"><option value="-1">全部分类</option><option value="0">默认分类</option></select></div>');
		
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
          <div class="mb-4">
            <label class="block font-medium mb-4">被控内网安装命令</label>
            <div class="flex items-center bg-gray-200 p-5 rounded">
              <div class="flex-1 overflow-x-auto">curl -sSO http://www.btkaixin.net/install/btmonitoragent.sh && bash btmonitoragent.sh https://192.168.3.62:806 e3359d2264ecc6ea29663f34dbc69a6a</div>
              <button class="ml-2 bg-green-600 hover:bg-green-700 text-white py-1 px-3 rounded">复制</button>
            </div>
          </div>
          <div class="mb-4">
            <label class="block font-medium mb-4">被控公网安装命令</label>
            <div class="flex items-center bg-gray-200 p-5 rounded">
              <div class="flex-1 overflow-x-auto">curl -sSO http://www.btkaixin.net/install/btmonitoragent.sh && bash btmonitoragent.sh https://240e:3b1:44a1:f3b0:a00:27ff:fe54:e15e:806 e3359d2264ecc6ea29663f34dbc69a6a</div>
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

  var placeholder = "<div class='placeholder c9' style='top:10px;left:10px'>"+lan.site.domain_help+"</div>";
  $('#mainDomain').after(placeholder);
  $(".placeholder").click(function(){
    $(this).hide();
    $('#mainDomain').focus();
  })
  $('#mainDomain').focus(function() {
      $(".placeholder").hide();
  });
  
  $('#mainDomain').blur(function() {
    if($(this).val().length==0){
      $(".placeholder").show();
    }  
  });

  //获取当前时间时间戳，截取后6位
  var timestamp = new Date().getTime().toString();
  var dtpw = timestamp.substring(7);
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



/*主机详情*/
function openHostDetail(host_id,host_name,endTime,addtime,event){
	event && event.preventDefault();

	layer.open({
		type: 1,
		area: '80%',
		title: '主机详情['+host_name+']',
		closeBtn: 1,
		shift: 0,
		content: `<div class='bt-form'>
			<div class='bt-w-menu pull-left' style='height: 565px;'>
				<p class='bgw' onclick="detailHostSummary('${host_id}')" title='主机概览'>主机概览</p>
				<p onclick="detailBaseMonitor('${host_id}')" title='基础监控'>基础监控</p>
				<p onclick="detailLogMonitor('${host_id}')" title='日志监控'>日志监控</p>
				<p onclick="detailSysMonitor('${host_name}')" title='系统监控'>系统监控</p>
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
function detailHostSummary(host_id, name, msg, status) {

  var bodyHtml = `

    <!-- 主机信息 -->
    <div class="detailHostSummary server bgw mb15">
      <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">主机信息</h3>
      </div>
      <div class="p-5">
          <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-2">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">主机名称: </span><span class="hostName"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">IP地址:</span><span class="ip"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">操作系统:</span><span class="platform"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">运行天数:</span><span class="runDay"></span></div>
          </div>
          <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-2">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">被控版本:</span><span class="jhMonitorVersion"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">CPU型号:</span><span class="modelName"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">平均负载:</span><span class="loadAvg"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">上次启动时间:</span><span class="upTime"></span></div>
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
        <div class="server bgw mt-5" style="height:600px">
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
  setInterval(function() {
    getDetailHostSummaryData(host_id);
  }, 3000);

}


/**
 * 基础监控
 * @param {Int} host_id 网站ID
 */
function detailBaseMonitor(host_id, name, msg, status) {
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

  getDetailHostBaseMonitorData();
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
          <div>
              <ul id="logFileBody" class="log-path-list" style="line-height: 35px;">
                  <li class="log-path-item px-5 log-path cursor-pointer bg-green-200 text-green-500">/www/wwwlogs</li>
                  <li class="log-path-item px-5 log-path cursor-pointer">/www/wwwlogs</li>
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
              <div class="mr-5 overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">日志大小:</span><span class="size"></span></div>
              <div class="mr-5 overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">文件权限:</span><span class="permission"></span></div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">修改时间:</span><span class="modifyTime"></span></div>
          </div>
        </div>
        <div class="mx-5 p-5 bgw" style="height: 390px;" class="content">
          日志内容为空
        </div>
      </div>
    </div>
  `;

  $("#hostdetail-con").html(bodyHtml);

  getDetailHostLogMonitorData();

  $(".log-path-item").click(function() {
    const logName = $(this).text();
    $(this).addClass('bg-green-200 text-green-500').siblings().removeClass('bg-green-200 text-green-500');
    getDetailHostLogMonitorDetailData(logName);
  });
  
  // 默认选中第一个
  if ($(".log-path-item").length > 0) {
    $(".log-path-item").eq(0).click();
  }
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
    $('.detailHostSummary .platform').text(`${host_info['platform']} ${host_info['platformVersion']}`);
    $('.detailHostSummary .runDay').text(host_info['runDay']);
    $('.detailHostSummary .jhMonitorVersion').text(host_info['jhMonitorVersion']);
    $('.detailHostSummary .modelName').text(cpu_info['modelName']);
    $('.detailHostSummary .loadAvg').text(`${load_avg['1min']} / ${load_avg['5min']} / ${load_avg['15min']}`);
    $('.detailHostSummary .upTime').text(host_info['upTime']);

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
    $("#cpuState").html(cpu_info.logicalCores + ' 核心');

    // 内存
    $("#memory").html(mem_info.usedPercent);
    $("#memoryState").html(toSize(parseInt(mem_info.used)) + '/' + toSize(parseInt(mem_info.total)) + ' (MB)');

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
    updateDetailHostSummaryAlarm(host_id);

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

// 图标相关
var netChart = {}

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

function updateDetailHostSummaryNetChart(net_info) {
  if (net_info && net_info.length > 0) {
    const { sent, recv } = net_info[0];
    netChart.addData(sent, recv, true);
  }
  netChart.updateOption();
}

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

function getDetailHostBaseMonitorData(host_id) {
  initDetailHostBaseMonitorAvgLoadChart();
  initDetailHostBaseMonitorCPUChart();
  initDetailHostBaseMonitorMemChart();
  initDetailHostBaseMonitorDiskIoChart();
  initDetailHostBaseMonitorNetIoChart();
}


// 平均负载图表
var avgLoadChart = {}
function initDetailHostBaseMonitorAvgLoadChart() {
  // ! 模拟数据
  let avg_load_history = [
    {id: 162319, pro: 33.25, one: 1.33, five: 1.55, fifteen: 1.11, addtime: "10/27 00:12"},
    {id: 162323, pro: 75.25, one: 3.01, five: 2.76, fifteen: 1.81, addtime: "10/27 00:21"},
    {id: 162327, pro: 55.5, one: 2.22, five: 2.04, fifteen: 1.91, addtime: "10/27 00:30"},
    {id: 162331, pro: 33.5, one: 1.34, five: 2.02, fifteen: 1.99, addtime: "10/27 00:38"},
  ]

  avgLoadChart = {
    aData: [],
    bData: [],
    xData: [],
    yData: [],
    zData: [],
    myChart: echarts.init(document.getElementById('avgloadview')),
    init() {
      for(var i = 0; i < avg_load_history.length; i++){
        this.xData.push(avg_load_history[i].addtime);
        this.yData.push(avg_load_history[i].pro);
        this.zData.push(avg_load_history[i].one);
        this.aData.push(avg_load_history[i].five);
        this.bData.push(avg_load_history[i].fifteen);
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
            name: '资源使用率%',
            splitLine: { // y轴网格显示
              show: true,
              lineStyle:{
                color:"#ddd"
              }
            },
            nameTextStyle: { // 坐标轴名样式
              color: '#666',
              fontSize: 12,
              align: 'left'
            },
            axisLine:{
              lineStyle:{
                color: '#666',
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
            nameTextStyle: { // 坐标轴名样式
              color: '#666',
              fontSize: 12,
              align: 'left'
            },
            axisLine:{
              lineStyle:{
                color: '#666',
              }
            }
          },
        ],
        dataZoom: [{
          type: 'inside',
          start: 0,
          end: 100,
          xAxisIndex:[0,1],
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
          },
          left:'5%',
          right:'5%'
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
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    }
  }
  avgLoadChart.init();
}

// CPU图表
var memChart = {}
function initDetailHostBaseMonitorCPUChart() {
  // ! 模拟数据
  let cpu_history = [
    {id: 168901, pro: 43.7, mem: 53.13726627703006, addtime: "11/03 00:00"},
    {id: 168902, pro: 100, mem: 54.07751697121776, addtime: "11/03 00:01"},
    {id: 168903, pro: 71.6, mem: 60.346975585265625, addtime: "11/03 00:03"},
    {id: 168904, pro: 90.5, mem: 72.29185875221229, addtime: "11/03 00:05"}
  ]

  cpuChart = {
    xData: [],
    yData: [],
    myChart: echarts.init(document.getElementById('cupview')),
    init() {
      for(var i = 0; i < cpu_history.length; i++){
        
        this.xData.push(cpu_history[i].addtime);
        this.yData.push(cpu_history[i].pro);
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
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    }
  }
  cpuChart.init();
}

// 内存图表
var memChart = {}
function initDetailHostBaseMonitorMemChart() {
  // ! 模拟数据
  let mem_history = [
    {id: 168901, pro: 43.7, mem: 53.13726627703006, addtime: "11/03 00:00"},
    {id: 168902, pro: 100, mem: 54.07751697121776, addtime: "11/03 00:01"},
    {id: 168903, pro: 71.6, mem: 60.346975585265625, addtime: "11/03 00:03"},
    {id: 168904, pro: 90.5, mem: 72.29185875221229, addtime: "11/03 00:05"}
  ]

  memChart = {
    xData: [],
    zData: [],
    myChart: echarts.init(document.getElementById('memview')),
    init() {
      for(var i = 0; i < mem_history.length; i++){
        this.xData.push(mem_history[i].addtime);
        // this.yData.push(mem_history[i].pro);
        this.zData.push(mem_history[i].mem);
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
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    }
  }
  memChart.init();
}

// 磁盘IO图表
var diskIoChart = {}
function initDetailHostBaseMonitorDiskIoChart() {
  // ! 模拟数据
  let disk_io_history = [
    {"id": 168906, "read_count": 386, "write_count": 531, "read_bytes": 5439488, "write_bytes": 9777152, "read_time": 1561, "write_time": 22025, "addtime": "11/03 00:00"}, 
    {"id": 168907, "read_count": 5, "write_count": 625, "read_bytes": 20480, "write_bytes": 6459392, "read_time": 4, "write_time": 20821, "addtime": "11/03 00:01"}, 
    {"id": 168908, "read_count": 0, "write_count": 277, "read_bytes": 0, "write_bytes": 3047424, "read_time": 0, "write_time": 21336, "addtime": "11/03 00:03"}, 
    {"id": 168909, "read_count": 0, "write_count": 254, "read_bytes": 0, "write_bytes": 3067904, "read_time": 0, "write_time": 22231, "addtime": "11/03 00:05"}, 
    {"id": 168910, "read_count": 0, "write_count": 311, "read_bytes": 0, "write_bytes": 4100096, "read_time": 0, "write_time": 637, "addtime": "11/03 00:06"}, 
    {"id": 168911, "read_count": 0, "write_count": 332, "read_bytes": 0, "write_bytes": 3985408, "read_time": 0, "write_time": 97995, "addtime": "11/03 00:08"}, 
    {"id": 168912, "read_count": 3, "write_count": 549, "read_bytes": 217088, "write_bytes": 6299648, "read_time": 1416, "write_time": 105301, "addtime": "11/03 00:10"}, 
    {"id": 168913, "read_count": 0, "write_count": 276, "read_bytes": 0, "write_bytes": 2994176, "read_time": 0, "write_time": 1676, "addtime": "11/03 00:12"}
  ]

  diskIoChart = {
    rData: [],
    wData: [],
    xData: [],
    myChart: echarts.init(document.getElementById('diskview')),
    init() {
      for(var i = 0; i < disk_io_history.length; i++){
        this.rData.push((disk_io_history[i].read_bytes/1024/60).toFixed(3));
        this.wData.push((disk_io_history[i].write_bytes/1024/60).toFixed(3));
        this.xData.push(disk_io_history[i].addtime);
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
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    }
  }
  diskIoChart.init();
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
      for(var i = 0; i < net_io_history.length; i++){
        this.aData.push(net_io_history[i].total_up);
        this.bData.push(net_io_history[i].total_down);
        this.cData.push(net_io_history[i].down_packets);
        this.dData.push(net_io_history[i].up_packets);
        this.xData.push(net_io_history[i].addtime);
        this.yData.push(net_io_history[i].up);
        this.zData.push(net_io_history[i].down);
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
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    }
  }
  netIoChart.init();
}

// 日志文件列表
function getDetailHostLogMonitorData() {
  let log_file_list = [
    {id: 1, name: 'access.log', size: '100M', modifyTime: '2021-10-10 10:10:10'},
    {id: 2, name: 'error.log', size: '200M', modifyTime: '2021-10-10 10:10:10'},
    {id: 3, name: 'info.log', size: '300M', modifyTime: '2021-10-10 10:10:10'},
  ]
  let logFileBody = '';
  for(let logFile of log_file_list) {
    logFileBody += `
      <li class="log-path-item px-5 log-path cursor-pointer">${logFile.name}</li>  
    `;
  }
  $("#logFileBody").html(logFileBody);

}

// 日志详情
function getDetailHostLogMonitorDetailData() {
  
  let logFileDetail = {
    path: '/www/syslog',
    size: 23,
    permission: '--rw-r--r--',
    modifyTime: '2021-10-10 10:10:10',
    content: '测试日志内容'
  }
  $("#logFileDetail .path").text(logFileDetail.path);
  $("#logFileDetail .size").text(logFileDetail.size);
  $("#logFileDetail .permission").text(logFileDetail.permission);
  $("#logFileDetail .modifyTime").text(logFileDetail.modifyTime);
  $("#logFileDetail .content").text(logFileDetail.content);

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













