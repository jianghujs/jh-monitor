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
      // 格式化json数据
      data.data[i].cpu_info = JSON.parse(data.data[i].cpu_info || '{}');

			//当前主机状态
			if (data.data[i].status == '正在运行' || data.data[i].status == '1') {
				var status = "<a href='javascript:;' title='停用这个主机' onclick=\"webStop(" + data.data[i].id + ",'" + data.data[i].name + "')\" class='btn-defsult'><span style='color:rgb(92, 184, 92)'>运行中</span><span style='color:rgb(92, 184, 92)' class='glyphicon glyphicon-play'></span></a>";
			} else {
				var status = "<a href='javascript:;' title='启用这个主机' onclick=\"webStart(" + data.data[i].id + ",'" + data.data[i].name + "')\" class='btn-defsult'><span style='color:red'>已停止</span><span style='color:rgb(255, 0, 0);' class='glyphicon glyphicon-pause'></span></a>";
			}

			body = "<tr><td><input type='checkbox' name='id' title='"+data.data[i].host_name+"' onclick='checkSelect();' value='" + data.data[i].id + "'></td>\
					<td>\
						<a class='btlink webtips' href='http://"+data.data[i].name+"' onclick=\"webEdit(" + data.data[i].id + ",'" + data.data[i].name + "','" + data.data[i].edate + "','" + data.data[i].addtime + "',event)\" title='"+data.data[i].name+"'>" 
							+ data.data[i].host_name + '/' + data.data[i].ip + "\
            </a>\
          </td>\
					<td>" + status + "</td>\
					<td>" + data.data[i].host_group_name + "</td>\
					<td>" + (data.data[i].cpu_info.percent || '') + "</td>\
					<td>" + "" + "</td>\
					<td>" + "" + "</td>\
					<td>" + "" + "</td>\
					<td>" + "" + "</td>\
					<td>" + "" + "</td>\
					<td>" + "" + "</td>\
					<td style='text-align:right; color:#bbb'>\
					    <a href='javascript:;' class='btlink' onclick=\"openHostDetail(" + data.data[i].id + ",'" + data.data[i].host_name + "','" + data.data[i].edate + "','" + data.data[i].addtime + "')\">详情</a>\
					    | <a href='javascript:;' class='btlink' onclick=\"webEdit(" + data.data[i].id + ",'" + data.data[i].name + "','" + data.data[i].edate + "','" + data.data[i].addtime + "')\">设置</a>\
              | <a href='javascript:;' class='btlink' onclick=\"hostDelete('" + data.data[i].id + "','" + data.data[i].host_name + "')\" title='删除主机'>删除</a>\
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



//添加主机
function openHostAdd() {
  layer.open({
    type: 1,
    skin: 'demo-class',
    area: '640px',
    title: '添加主机',
    closeBtn: 1,
    shift: 0,
    shadeClose: false,
    content: "<form class='bt-form pd20 pb70' id='addhost'>\
        <div class='line'>\
          <span class='tname'>主机名</span>\
          <div class='info-r c4'>\
            <input id='hostName' class='bt-input-text' type='text' name='host_name' placeholder='主机名' style='width:458px' />\
          </div>\
        </div>\
        <div class='line'>\
          <span class='tname'>IP</span>\
          <div class='info-r c4'>\
            <input id='ip' class='bt-input-text' type='text' name='ip' placeholder='IP地址' style='width:458px' />\
          </div>\
        </div>\
        <div class='line'>\
          <span class='tname'>SSH公钥</span>\
          <div class='info-r c4'>\
            <input id='sshPkey' class='bt-input-text' type='text' name='ssh_pkey' placeholder='SSH公钥' style='width:458px' />\
          </div>\
        </div>\
        <div class='bt-form-submit-btn'>\
          <button type='button' class='btn btn-danger btn-sm btn-title' onclick='layer.closeAll()'>取消</button>\
          <button type='button' class='btn btn-success btn-sm btn-title' onclick=\"hostAdd()\">提交</button>\
        </div>\
    </form>",
  });

  $(function() {
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
  });
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
 * @param {Number} id 主机ID
 * @param {String} name 主机名称
 */
function hostDelete(id, name){
	safeMessage("确认", "确定要删除主机"+"["+name+"]吗？", function(){
		var loadT = layer.msg('正在处理,请稍候...',{icon:16,time:10000,shade: [0.3, '#000']});
		$.post("/host/delete","id=" + id, function(ret){
			layer.closeAll();
			layer.msg(ret.msg,{icon:ret.status?1:2})
			getWeb(1);
		},'json');
	});
}



/*主机详情*/
function openHostDetail(id,host_name,endTime,addtime,event){
	event && event.preventDefault();
	
	layer.open({
		type: 1,
		area: '80%',
		title: '主机详情['+host_name+']',
		closeBtn: 1,
		shift: 0,
		content: "<div class='bt-form'>\
			<div class='bt-w-menu pull-left' style='height: 565px;'>\
				<p class='bgw' onclick='detailHostSummary("+id+")' title='主机概览'>主机概览</p>\
				<p onclick='detailBaseMonitor("+id+")' title='基础监控'>基础监控</p>\
				<p onclick='detailLogMonitor("+id+")' title='日志监控'>日志监控</p>\
				<p onclick=\"detailSysMonitor('"+host_name+"')\" title='系统监控'>系统监控</p>\
			</div>\
			<div id='hostdetail-con' class='bt-w-con hostdetail-con pd15' style='height: 565px;overflow: scroll;background: #fcf8f8;'></div>\
		</div>",
		success:function(){

			//切换
			$(".bt-w-menu p").click(function(){
				$(this).addClass("bgw").siblings().removeClass("bgw");
			});

			detailHostSummary(id,host_name);
		}
	});	
}


/**
 * 主机概览
 * @param {Int} id 网站ID
 */
function detailHostSummary(id, name, msg, status) {
  var bodyHtml = `

    <!-- 主机信息 -->
    <div class="server bgw mb15">
      <div class="title c6 f16 plr15">
          <h3 class="c6 f16 pull-left">主机信息</h3>
      </div>
      <div class="p-5">
          <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-2">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">主机名称: </span>debian</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">IP地址:</span>192.168.3.6</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">操作系统:</span>debian 11.6</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">运行天数:</span>0.8 天</div>
          </div>
          <div class="grid md:grid-cols-2 lg:grid-cols-4 gap-4 mt-2">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">被控版本:</span>4.4</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">CPU型号:</span>Intel(R) Core(TM) i7-8700 CPU @ 3.2...</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">平均负载:</span>0.19 / 0.31 / 0.3</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">上次启动时间:</span>2024-10-30 19:46:49</div>
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
                          <div class="mask"><span id="state">0</span>%</div>
                      </div>
                      <h4 id="core" class="c5 f15">获取中...</h4>
                  </li>
                  <li class="mtb20 circle-box text-center">
                      <h3 class="c5 f15">内存使用率</h3>
                      <div class="circle mem-release">
                          <div class="pie_left">
                              <div class="left"></div>
                          </div>
                          <div class="pie_right">
                              <div class="right"></div>
                          </div>
                          <div class="mask"><span id="left">0</span>%</div>
                          <div class="mem-re-min" style="display: none;"></div>
                          <div class="mem-re-con" title=""></div>
                      </div>
                      <h4 id="memory" class="c5 f15">获取中...</h4>
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
                    <th width="40" onclick="listOrder('load','host',this)" class="cursor-pointer">进程名<span class="glyphicon glyphicon-triangle-top" style="margin-left:5px;color:#bbb"></span></th>
                    <th width="40" onclick="listOrder('load','host',this)" class="cursor-pointer">CPU<span class="glyphicon glyphicon-triangle-top" style="margin-left:5px;color:#bbb"></span></th>
                    <th width="40" onclick="listOrder('load','host',this)" class="cursor-pointer">内存<span class="glyphicon glyphicon-triangle-top" style="margin-left:5px;color:#bbb"></span></th>
                    <th width="40" onclick="listOrder('cpu','host',this)" class="cursor-pointer">网络总IO<span class="glyphicon glyphicon-triangle-top" style="margin-left:5px;color:#bbb"></span></th>
                    <th width="40" onclick="listOrder('cpu','host',this)" class="cursor-pointer">磁盘总IO<span class="glyphicon glyphicon-triangle-top" style="margin-left:5px;color:#bbb"></span></th>
                    <th width='40' class='text-right'>操作</th>
                  </tr>
                </thead>
                <tbody id="webBody"></tbody>
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
        <div class="bgw" style="height:491px">
            <div class="title c6 f16 plr15">流量</div>
            <div class="bw-info">
                <div class="col-sm-6 col-md-3"><p class="c9"><span class="ico-up"></span>上行</p><a id="upSpeed">0</a></div>
                <div class="col-sm-6 col-md-3"><p class="c9"><span class="ico-down"></span>下行</p><a id="downSpeed">0</a></div>
                <div class="col-sm-6 col-md-3"><p class="c9">总发送</p><a id="upAll">0</a></div>
                <div class="col-sm-6 col-md-3"><p class="c9">总接收</p><a id="downAll">0</a></div>
            </div>
            <div id="netImg" style="width:100%;height:330px;"></div>
        </div>

        
        <!-- 告警事件 -->
        <div class="server bgw mt-5" style="height:200px">
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
                <tbody id="webBody"></tbody>
              </table>
              </div>
              <div class="dataTables_paginate paging_bootstrap pagination">
                <ul id="webPage" class="page"></ul>
              </div>
            </div>
          </div>
        </div>

        <!-- 在线的SSH用户 -->
        <div class="server bgw mt-5" style="height:200px">
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
                    <th width='40' class='text-right border-none'>操作</th>
                  </tr>
                </thead>
                <tbody id="webBody"></tbody>
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

}


/**
 * 基础监控
 * @param {Int} id 网站ID
 */
function detailBaseMonitor(id, name, msg, status) {
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
            <div id="getloadview" style="width:100%; height:330px"></div>
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

}

/**
 * 日志监控
 * @param {Int} id 网站ID
 */
function detailLogMonitor(id, name, msg, status) {
  var bodyHtml = `
    <div class="flex flex-wrap">
      <!-- 日志路径列表 --> 
      <div class="bgw" style="width: 30%;height: 500px;">
        <div class="server mb15">
          <div class="title c6 f16 plr15">
              <h3 class="c6 f16 pull-left">日志路径列表</h3>
          </div>
          <div>
              <ul class="log-path-list" style="line-height: 35px;">
                  <li class="log-path-item">
                      <div class="px-5 log-path cursor-pointer bg-green-200 text-green-500">/www/wwwlogs</div>
                      <div class="px-5 log-path cursor-pointer">/www/wwwlogs</div>
                      <div class="px-5 log-path cursor-pointer">/www/wwwlogs</div>
                      <div class="px-5 log-path cursor-pointer">/www/wwwlogs</div>
                  </li>
              </ul>
          </div>
        </div>
      </div>
      <div style="width:68%;">
        <div class="mx-5 mb-5 p-5 bg-white">
          <div class="title mt-2 flex">
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">日志路径: </span>/var/log/syslog</div>
          </div>
          <div class="mt-2 flex">
              <div class="mr-5 overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">日志大小:</span>0B</div>
              <div class="mr-5 overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">文件权限:</span>-rw-r--r--</div>
              <div class="overflow-hidden whitespace-nowrap text-ellipsis"><span class="text-gray-400 inline-block w-32">修改时间:</span>2024-10-30 19:46:49</div>
          </div>
        </div>
        <div class="mx-5 p-5 bgw" style="height: 390px;">
          日志内容为空
        </div>
      </div>
    </div>
  `;

  $("#hostdetail-con").html(bodyHtml);

}

/**
 * 系统监控
 * @param {Int} id 网站ID
 */
function detailSysMonitor(id, name, msg, status) {
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
            <tbody id="webBody"></tbody>
          </table>
          </div>
          <div class="dataTables_paginate paging_bootstrap pagination">
            <ul id="webPage" class="page"></ul>
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
            <tbody id="webBody"></tbody>
          </table>
          </div>
          <div class="dataTables_paginate paging_bootstrap pagination">
            <ul id="webPage" class="page"></ul>
          </div>
        </div>
      </div>
    </div>
    
  `;

  $("#hostdetail-con").html(bodyHtml);

}



















