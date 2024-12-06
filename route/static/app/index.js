// ==================== 初始化事件开始 ====================
setTimeout(() => {
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
  $(".hostbtn").click(function(){
    $(this).parents(".searcTime").find("span").removeClass("on");
    $(this).parents(".searcTime").find(".st").addClass("on");
    var b = (new Date($(this).parent().find(".btime").val()).getTime())/1000;
    var e = (new Date($(this).parent().find(".etime").val()).getTime())/1000;
    b = Math.round(b);
    e = Math.round(e);
    updateHostChartData(b,e);
  })
})

//指定天数
function Wday(day, name){
	var now = (new Date().getTime())/1000;
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
		case "host":
			updateHostChartData(s,e);
	}
}

// ==================== 初始化事件结束 ====================




var loadT = layer.load();
var hostList = [];
function initHostCharts() {
	//取回数据
	$.post('/host/list', '', function(rdata) {
    let data = JSON.parse(rdata);
    hostList = data.data;
		layer.close(loadT);
    for (var i = 0; i < hostList.length; i++) {
      let host = hostList[i];
      createHostChart(host);
    }
    Wday(0,'host');
  });
}

var hostChartMap = {};
// 主机图表
function createHostChart(host) {
  const { host_id, host_name } = host;

  let chartId = 'host-chart-' + host_id;
  // Add button group for curve selection
  $('#hostCharts').append(`
    <div class="chart-container">
      <div id="${chartId}" style="width:100%; height:330px"></div>
    </div>
  `);
  let dom = document.getElementById(chartId);

  let hostChart = {
    xData: [],
    yData: [],
    myChart: echarts.init(dom),
    init() {
      this.setData();
      window.addEventListener("resize",function(){
        this.myChart.resize();
      });
    },
    setData(d = {}) {
      const colors = ['#5470C6', '#91CC75', '#EE6666', '#73C0DE', '#3BA272', '#FC8452', '#9A60B4'];
      const { cpu_history = [], mem_history = [], disk_io_history = [], net_io_history = [], disk_usage_history = [] } = d;
      
      // 数据处理
      const xData = cpu_history.map(item => item.addtime);
      const cpuData = cpu_history.map(item => item.pro);
      const memData = mem_history.map(item => item.mem);
      const diskUsageData = disk_usage_history.map(item => item.usedPercent);
      const readData = disk_io_history.map(item => (item.read_bytes / 1024));
      const writeData = disk_io_history.map(item => (item.write_bytes / 1024));
      const netUpData = net_io_history.map(item => (item.up || 0));
      const netDownData = net_io_history.map(item => (item.down || 0));
      // 获取最大值
      let maxPercent = cpu_history.length == 0? 100:Math.max(...cpuData, ...memData, ...diskUsageData);
      let maxDiskIO = cpu_history.length == 0? 10000: Math.max(...readData, ...writeData);
      let maxNetIO = cpu_history.length == 0? 10000: Math.max(...netUpData, ...netDownData);
      // 配置项
      let option = {
        title: {
          text: `${host_name}`,
          top: '10px',
          left: 'center',
          textStyle: {
            fontSize: 20,
            fontWeight: 'bold',
            color: '#333'
          }
        },
        legend: {
          data: ['CPU', '内存', '磁盘使用率', '磁盘读取', '磁盘写入', '网络上传', '网络下载'],
          top: '50px', // 将图例放在标题下方
          left: 'center',
          width: '80%'
        },
        grid: {
          top: '150px', // 增加顶部间距以避免重叠
          left: '3%',
          right: '15%',
          bottom: '5%',
          containLabel: true
        },
        tooltip: {
          trigger: 'axis',
          axisPointer: {
            type: 'cross'
          },
          formatter: function (params) {
            let tooltipText = params[0].name + '<br/>';
            params.forEach(param => {
              let unit = '';
              switch (param.seriesName) {
                case 'CPU':
                case '内存':
                case '磁盘使用率':
                  unit = '%';
                  break;
                case '磁盘读取':
                case '磁盘写入':
                case '网络上传':
                case '网络下载':
                  unit = ' KB/s';
                  break;
              }
              tooltipText +=  param.seriesName + ': ' + param.value + unit + '<br/>';
            });
            return tooltipText;
          }
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: xData,
          axisLine: {
            lineStyle: {
              color: "#666"
            }
          }
        },
        yAxis: [
          {
            type: 'value',
            name: '百分比 (%)',
            min: 0,
            max: 100,
            position: 'left',
            axisLine: {
              lineStyle: {
                color: 'rgb(0, 153, 238)'
              }
            }
          },
          {
            type: 'value',
            name: 'Disk IO (KB/s)',
            min: 0,
            max: maxDiskIO, // 根据数据适当调整最大值
            position: 'right',
            axisLine: {
              lineStyle: {
                color: 'rgb(255, 70, 131)'
              }
            }
          },
          {
            type: 'value',
            name: 'Net (KB/s)',
            min: 0,
            max: maxNetIO, // 根据数据适当调整最大值
            position: 'right',
            offset: 80,
            axisLine: {
              lineStyle: {
                color: 'rgb(255, 162, 131)'
              }
            }
          }
        ],
        dataZoom: [
          {
            show: true,
            start: 0,
            end: 100
          },
          {
            type: 'inside',
            start: 0,
            end: 100
          },
          {
            show: true,
            yAxisIndex: [0, 1, 2],
            filterMode: 'empty',
            width: 30,
            bottom: 30,
            showDataShadow: false,
            right: 30
          }
        ],
        series: [
          {
            name: 'CPU',
            type: 'line',
            yAxisIndex: 0,
            data: cpuData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[0]
            }
          },
          {
            name: '内存',
            type: 'line',
            yAxisIndex: 0,
            data: memData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[1]
            }
          },
          {
            name: '磁盘使用率',
            type: 'line',
            yAxisIndex: 0,
            data: diskUsageData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[2]
            }
          },
          {
            name: '磁盘读取',
            type: 'line',
            yAxisIndex: 1,
            data: readData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[3]
            }
          },
          {
            name: '磁盘写入',
            type: 'line',
            yAxisIndex: 1,
            data: writeData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[4]
            }
          },
          {
            name: '网络上传',
            type: 'line',
            yAxisIndex: 2,
            data: netUpData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[5]
            }
          },
          {
            name: '网络下载',
            type: 'line',
            yAxisIndex: 2,
            data: netDownData,
            smooth: true,
            showSymbol: false,
            lineStyle: {
              width: 2,
              color: colors[6]
            }
          }
        ]
      };
      this.myChart.setOption(option);
    }
  }
  hostChart.init();
  hostChartMap[host_id] = hostChart;
}

/**
 * 更新主机图表数据
 * @param {*} s 
 * @param {*} e 
 */
function updateHostChartData(s, e) {
  $.post('/host/get_all_host_chart', '&start='+s+'&end='+e,function(rdata){
    for (let hostIndex in hostList) {
      let host = hostList[hostIndex];
      let {host_id} = host;
      let host_data = rdata[host_id] || [];
      let cpu_history = [];
      let mem_history = [];
      let disk_io_history = [];
      let net_io_history = [];
      let disk_usage_history = [];
      for ( let i = 0; i < host_data.length; i++) {
        let item = host_data[i];
        let itemCpuInfo = JSON.parse(item['cpu_info'] || '{}');
        let itemMemInfo = JSON.parse(item['mem_info'] || '{}');
        let itemDiskIoList = JSON.parse(item['disk_info'] || '[]');
        let itemDiskInfo = itemDiskIoList[0] || {};
        let itemNetIoList = JSON.parse(item['net_info'] || '[]');
        let itemNetIo = itemNetIoList[0] || {};

        cpu_history.push({
          id: item.id,
          pro: itemCpuInfo.percent,
          addtime: item.addtime
        });
        mem_history.push({
          id: item.id,
          mem: itemMemInfo.usedPercent,
          addtime: item.addtime
        });
        disk_io_history.push({
          id: item.id,
          read_bytes: itemDiskInfo.readSpeed,
          write_bytes: itemDiskInfo.writeSpeed,
          addtime: item.addtime
        });
        net_io_history.push({
          id: item.id,
          up: itemNetIo.sent_per_second,
          down: itemNetIo.recv_per_second,
          total_up: itemNetIo.sent,
          total_down: itemNetIo.recv,
          down_packets: itemNetIo.recv_packets,
          up_packets: itemNetIo.sent_packets,
          addtime: item.addtime
        });
        disk_usage_history.push({
          id: item.id,
          usedPercent: itemDiskInfo.usedPercent,
          addtime: item.addtime
        });
      };
      debugger

      hostChartMap[host_id].setData({
        cpu_history,
        mem_history,
        disk_io_history,
        net_io_history,
        disk_usage_history
      });
    }
  }, 'json');
}

// 在文件末尾添加全局曲线控制按钮的HTML
$('#hostCharts').before(`
  <div class="curve-selector" style="margin: 10px 0; text-align: center;">
    <div class="curve-buttons">
      <button class="select-all-btn" onclick="toggleAllCurves(true)">显示全部曲线</button>
      <button class="select-none-btn mr-2" onclick="toggleAllCurves(false)">隐藏全部曲线</button>
      <button class="curve-btn" data-series="CPU">CPU</button>
      <button class="curve-btn" data-series="内存">内存</button>
      <button class="curve-btn" data-series="磁盘使用率">磁盘使用率</button>
      <button class="curve-btn" data-series="磁盘读取">磁盘读取</button>
      <button class="curve-btn" data-series="磁盘写入">磁盘写入</button>
      <button class="curve-btn" data-series="网络上传">网络上传</button>
      <button class="curve-btn" data-series="网络下载">网络下载</button>
    </div>
  </div>
`);

function toggleAllCurves(show) {
  // 遍历所有图表
  Object.values(hostChartMap).forEach(hostChart => {
    const chart = hostChart.myChart;
    const seriesNames = chart.getOption().series.map(s => s.name);
    
    seriesNames.forEach(seriesName => {
      chart.dispatchAction({
        type: show ? 'legendSelect' : 'legendUnSelect',
        name: seriesName
      });
    });
  });
  
  // 更新按钮状态
  $('.curve-btn').toggleClass('active', show);
}

$(document).on('click', '.curve-btn', function() {
  const button = $(this);
  const seriesName = button.data('series');
  const isActive = !button.hasClass('active');
  
  button.toggleClass('active', isActive);
  
  // 对所有图表应用相同的显示/隐藏设置
  Object.values(hostChartMap).forEach(hostChart => {
    const chart = hostChart.myChart;
    chart.dispatchAction({
      type: isActive ? 'legendSelect' : 'legendUnSelect',
      name: seriesName
    });
  });
});

// Initialize all buttons as active
setTimeout(() => {
  $('.curve-btn').addClass('active');
}, 1000);







// 检查更新
// setTimeout(function() {
//     $.get('/system/update_server?type=check', function(rdata) {
//         if (rdata.status == false) return;
//         if (rdata.data != undefined) {
//             $("#toUpdate").html('<a class="btlink" href="javascript:updateMsg();">更新</a>');
//             $('#toUpdate a').html('更新<i style="display: inline-block; color: red; font-size: 40px;position: absolute;top: -35px; font-style: normal; right: -8px;">.</i>');
//             $('#toUpdate a').css("position","relative");
//             return;
//         }
//     },'json').error(function() {
//     });
// }, 3000);


//检查更新
function checkUpdate() {
  var loadT = layer.msg(lan.index.update_get, { icon: 16, time: 0, shade: [0.3, '#000'] });
  $.get('/system/update_server?type=check', function(rdata) {
      layer.close(loadT);

      if (rdata.data == 'download'){
          updateStatus();return;
      }

      if (rdata.status === false) {
          layer.confirm(rdata.msg, { title: lan.index.update_check, icon: 1, closeBtn: 1, btn: [lan.public.know, lan.public.close] });
          return;
      }
      layer.msg(rdata.msg, { icon: 1 });
      if (rdata.data != undefined) updateMsg();
  },'json');
}

async function updateServerCode() {
  await execScriptAndShowLog(`${lan.index.update_server_code}...`, `cd /www/server/jh-monitor/ && git pull`);
  var loadT = layer.msg("正在更新服务器...", { icon: 16, time: 0, shade: [0.3, '#000'] });
  $.get('/system/update_server_code', function(rdata) {
      layer.close(loadT);
      if (rdata.status == true) {
          layer.confirm('即将重启面板服务，继续吗？', { title: '重启面板服务', closeBtn: 1, icon: 3 }, function () {
              var loadT = layer.load();
              $.post('/system/restart','',function (rdata) {
                  layer.close(loadT);
                  layer.msg(rdata.msg);
                  layer.msg('正在重启面板,请稍候...',{icon:16,time:0,shade: [0.3, '#000']});
                  setInterval(function () {
                      $.post('/system/restart_status','',function (rdata) {
                          if (rdata.status) {
                              window.location.reload();
                          }
                      },'json');
                  }, 3000);
                  
              },'json');
          });
      } else {
          layer.msg(rdata.msg, { icon: 1 });
      }
  },'json');
}

function updateMsg(){
  $.get('/system/update_server?type=info',function(rdata){

      if (rdata.data == 'download'){
          updateStatus();return;
      }

      var v = rdata.data.version;
      var v_info = '';
      if (v.split('.').length>3){
          v_info = "<span class='label label-warning'>测试版本</span>";
      } else {
          v_info = "<span class='label label-success arrowed'>正式版本</span>";
      }

      layer.open({
          type:1,
          title:v_info + '<span class="badge badge-inverse">升级到['+rdata.data.version+']</span>',
          area: '400px', 
          shadeClose:false,
          closeBtn:2,
          content:'<div class="setchmod bt-form pd20 pb70">'
                  +'<p style="padding: 0 0 10px;line-height: 24px;">'+rdata.data.content+'</p>'
                  +'<div class="bt-form-submit-btn">'
                  +'<button type="button" class="btn btn-danger btn-sm btn-title" onclick="layer.closeAll()">取消</button>'
                  +'<button type="button" class="btn btn-success btn-sm btn-title" onclick="updateVersion(\''+rdata.data.version+'\')" >立即更新</button>'
                  +'</div>'
                  +'</div>'
      });
  },'json');
}


//开始升级
function updateVersion(version) {
  var loadT = layer.msg('正在升级面板..', { icon: 16, time: 0, shade: [0.3, '#000'] });
  $.get('/system/update_server?type=update&version='+version, function(rdata) {

      layer.closeAll();
      if (rdata.status === false) {
          layer.msg(rdata.msg, { icon: 5, time: 5000 });
          return;
      }
      layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
      if (rdata.status) {
          $("#btversion").html(version);
          $("#toUpdate").html('');
      }
  },'json').error(function() {
      layer.msg('更新失败,请重试!', { icon: 2 });
      setTimeout(function() {
          window.location.reload();
      }, 3000);
  });
}

function pluginIndexService(pname,pfunc, callback){
  $.post('/plugins/run', {name:'openresty', func:pfunc}, function(data) {
      if (!data.status){
          layer.msg(data.msg,{icon:0,time:2000,shade: [0.3, '#000']});
          return;
      }

      if(typeof(callback) == 'function'){
          callback(data);
      }
  },'json'); 
}

//重启服务器
function reBoot() {
  layer.open({
      type: 1,
      title: '重启服务器或者面板',
      area: '330px',
      closeBtn: 1,
      shadeClose: false,
      content: '<div class="rebt-con"><div class="rebt-li"><a data-id="server" href="javascript:;">重启服务器</a></div><div class="rebt-li"><a data-id="panel" href="javascript:;">重启面板</a></div></div>'
  });


  $('.rebt-con a').click(function () {
      var type = $(this).attr('data-id');
      switch (type) {
          case 'panel':
              layer.confirm('即将重启面板服务，继续吗？', { title: '重启面板服务', closeBtn: 1, icon: 3 }, function () {
                  var loadT = layer.load();
                  $.post('/system/restart','',function (rdata) {
                      layer.close(loadT);
                      layer.msg(rdata.msg);
                      setTimeout(function () { window.location.reload(); }, 3000);
                  },'json');
              });
              break;
          case 'server':
              var rebootbox = layer.open({
                  type: 1,
                  title: '安全重启服务器',
                  area: ['500px', '280px'],
                  closeBtn: 1,
                  shadeClose: false,
                  content: "<div class='bt-form bt-window-restart'>\
                          <div class='pd15'>\
                          <p style='color:red; margin-bottom:10px; font-size:15px;'>注意，若您的服务器是一个容器，请取消。</p>\
                          <div class='SafeRestart' style='line-height:26px'>\
                              <p>安全重启有利于保障文件安全，将执行以下操作：</p>\
                              <p>1.停止Web服务</p>\
                              <p>2.停止MySQL服务</p>\
                              <p>3.开始重启服务器</p>\
                              <p>4.等待服务器启动</p>\
                          </div>\
                          </div>\
                          <div class='bt-form-submit-btn'>\
                              <button type='button' class='btn btn-danger btn-sm btn-reboot'>取消</button>\
                              <button type='button' class='btn btn-success btn-sm WSafeRestart' >确定</button>\
                          </div>\
                      </div>"
              });
              setTimeout(function () {
                  $(".btn-reboot").click(function () {
                      rebootbox.close();
                  })
                  $(".WSafeRestart").click(function () {
                      var body = '<div class="SafeRestartCode pd15" style="line-height:26px"></div>';
                      $(".bt-window-restart").html(body);
                      $(".SafeRestartCode").append("<p>正在停止Web服务</p>");
                      pluginIndexService('openresty', 'stop', function (r1) {
                          $(".SafeRestartCode p").addClass('c9');
                          $(".SafeRestartCode").append("<p>正在停止MySQL服务...</p>");
                          pluginIndexService('mysql','stop', function (r2) {
                              $(".SafeRestartCode p").addClass('c9');
                              $(".SafeRestartCode").append("<p>开始重启服务器...</p>");
                              $.post('/system/restart_server', '',function (rdata) {
                                  $(".SafeRestartCode p").addClass('c9');
                                  $(".SafeRestartCode").append("<p>等待服务器启动...</p>");
                                  var sEver = setInterval(function () {
                                     $.get("/system/system_total", function(info) {
                                          clearInterval(sEver);
                                          $(".SafeRestartCode p").addClass('c9');
                                          $(".SafeRestartCode").append("<p>服务器重启成功!...</p>");
                                          setTimeout(function () {
                                              layer.closeAll();
                                          }, 3000);
                                      })
                                  }, 3000);
                              })
                          })
                      })
                  })
              }, 100);
              break;
      }
  });
}

function reBootPanel() {
  layer.confirm('即将重启面板服务，继续吗？', { title: '重启面板服务', closeBtn: 1, icon: 3 }, function () {
      var loadT = layer.load();
      $.post('/system/restart','',function (rdata) {
          layer.close(loadT);
          layer.msg(rdata.msg);
          layer.msg('正在重启面板,请稍候...',{icon:16,time:0,shade: [0.3, '#000']});
          setInterval(function () {
              $.post('/system/restart_status','',function (rdata) {
                  if (rdata.status) {
                      window.location.reload();
                  }
              },'json');
          }, 3000);
          
      },'json');
  });
}

function reBootServer() {
  var rebootbox = layer.open({
      type: 1,
      title: '安全重启服务器',
      area: ['500px', '280px'],
      closeBtn: 1,
      shadeClose: false,
      content: "<div class='bt-form bt-window-restart'>\
              <div class='pd15'>\
              <p style='color:red; margin-bottom:10px; font-size:15px;'>注意，若您的服务器是一个容器，请取消。</p>\
              <div class='SafeRestart' style='line-height:26px'>\
                  <p>安全重启有利于保障文件安全，将执行以下操作：</p>\
                  <p>1.停止Web服务</p>\
                  <p>2.停止MySQL服务</p>\
                  <p>3.开始重启服务器</p>\
                  <p>4.等待服务器启动</p>\
              </div>\
              </div>\
              <div class='bt-form-submit-btn'>\
                  <button type='button' class='btn btn-danger btn-sm btn-reboot'>取消</button>\
                  <button type='button' class='btn btn-success btn-sm WSafeRestart' >确定</button>\
              </div>\
          </div>"
  });
  setTimeout(function () {
      $(".btn-reboot").click(function () {
          rebootbox.close();
      })
      $(".WSafeRestart").click(function () {
          var body = '<div class="SafeRestartCode pd15" style="line-height:26px"></div>';
          $(".bt-window-restart").html(body);
          $(".SafeRestartCode").append("<p>正在停止Web服务</p>");
          pluginIndexService('openresty', 'stop', function (r1) {
              $(".SafeRestartCode p").addClass('c9');
              $(".SafeRestartCode").append("<p>正在停止MySQL服务...</p>");
              pluginIndexService('mysql','stop', function (r2) {
                  $(".SafeRestartCode p").addClass('c9');
                  $(".SafeRestartCode").append("<p>开始重启服务器...</p>");
                  $.post('/system/restart_server', '',function (rdata) {
                      $(".SafeRestartCode p").addClass('c9');
                      $(".SafeRestartCode").append("<p>等待服务器启动...</p>");
                      var sEver = setInterval(function () {
                         $.get("/system/system_total", function(info) {
                              clearInterval(sEver);
                              $(".SafeRestartCode p").addClass('c9');
                              $(".SafeRestartCode").append("<p>服务器重启成功!...</p>");
                              setTimeout(function () {
                                  layer.closeAll();
                              }, 3000);
                          })
                      }, 3000);
                  })
              })
          })
      })
  }, 100);
}

//修复面板
function repPanel() {
  layer.confirm(lan.index.rep_panel_msg, { title: lan.index.rep_panel_title, closeBtn: 1, icon: 3 }, function() {
      var loadT = layer.msg(lan.index.rep_panel_the, { icon: 16, time: 0, shade: [0.3, '#000'] });
      $.get('/system?action=RepPanel', function(rdata) {
          layer.close(loadT);
          layer.msg(lan.index.rep_panel_ok, { icon: 1 });
      }).error(function() {
          layer.close(loadT);
          layer.msg(lan.index.rep_panel_ok, { icon: 1 });
      });
  });
}

//获取警告信息
function getWarning() {
  $.get('/ajax?action=GetWarning', function(wlist) {
      var num = 0;
      for (var i = 0; i < wlist.data.length; i++) {
          if (wlist.data[i].ignore_count >= wlist.data[i].ignore_limit) continue;
          if (wlist.data[i].ignore_time != 0 && (wlist.time - wlist.data[i].ignore_time) < wlist.data[i].ignore_timeout) continue;
          var btns = '';
          for (var n = 0; n < wlist.data[i].btns.length; n++) {
              if (wlist.data[i].btns[n].type == 'javascript') {
                  btns += '<a href="javascript:WarningTo(\'' + wlist.data[i].btns[n].url + '\',' + wlist.data[i].btns[n].reload + ');" class="' + wlist.data[i].btns[n].class + '"> ' + wlist.data[i].btns[n].title + '</a>'
              } else {
                  btns += '<a href="' + wlist.data[i].btns[n].url + '" class="' + wlist.data[i].btns[n].class + '" target="' + wlist.data[i].btns[n].target + '"> ' + wlist.data[i].btns[n].title + '</a>'
              }
          }
          $("#messageError").append('<p><img src="' + wlist.icon[wlist.data[i].icon] + '" style="margin-right:14px;vertical-align:-3px">' + wlist.data[i].body + btns + '</p>');
          num++;
      }
      if (num > 0) $("#messageError").show();
  });
}

//按钮调用
function warningTo(to_url, def) {
  var loadT = layer.msg(lan.public.the_get, { icon: 16, time: 0, shade: [0.3, '#000'] });
  $.post(to_url, {}, function(rdata) {
      layer.close(loadT);
      layer.msg(rdata.msg, { icon: rdata.status ? 1 : 2 });
      if (rdata.status && def) setTimeout(function() { location.reload(); }, 1000);
  },'json');
}

function setSafeHide() {
  setCookie('safeMsg', '1');
  $("#safeMsg").remove();
}
//查看报告
function showDanger(num, port) {
  var atxt = "因未使用安全隔离登录，所有IP都可以尝试连接，存在较高风险，请立即处理。";
  if (port == "22") {
      atxt = "因未修改SSH默认22端口，且未使用安全隔离登录，所有IP都可以尝试连接，存在较高风险，请立即处理。";
  }
  layer.open({
      type: 1,
      area: ['720px', '410px'],
      title: '安全提醒(如你想放弃任何安全提醒通知，请删除宝塔安全登录插件)',
      closeBtn: 1,
      shift: 5,
      content: '<div class="pd20">\
      <table class="f14 showDanger"><tbody>\
      <tr><td class="text-right" width="150">风险类型：</td><td class="f16" style="color:red">暴力破解 <a href="https://www.bt.cn/bbs/thread-9562-1-1.html" class="btlink f14" style="margin-left:10px" target="_blank">说明</a></td></tr>\
      <tr><td class="text-right">累计遭遇攻击总数：</td><td class="f16" style="color:red">' + num + ' <a href="javascript:showDangerIP();" class="btlink f14" style="margin-left:10px">详细</a><span class="c9 f12" style="margin-left:10px">（数据直接来源本服务器日志）</span></td></tr>\
      <tr><td class="text-right">风险等级：</td><td class="f16" style="color:red">较高风险</td></tr>\
      <tr><td class="text-right" style="vertical-align:top">风险描述：</td><td style="line-height:20px">' + atxt + '</td></tr>\
      <tr><td class="text-right" style="vertical-align:top">可参考解决方案：</td><td><p style="margin-bottom:8px">方案一：修改SSH默认端口，修改SSH验证方式为数字证书，清除近期登陆日志。</p><p>方案二：购买宝塔企业运维版，一键部署安全隔离服务，高效且方便。</p></td></tr>\
      </tbody></table>\
      <div class="mtb20 text-center"><a href="https://www.bt.cn/admin/index.html" target="_blank" class="btn btn-success">立即部署隔离防护</a></div>\
      </div>'
  });
  $(".showDanger td").css("padding", "8px")
}

function pluginInit(){
  $.post('/plugins/init', function(data){
      if (!data.status){
          return false;
      }

      var rdata = data.data;
      var plugin_list = '';

      for (var i = 0; i < rdata.length; i++) {
          var ver = rdata[i]['versions'];
          var select_list = '';
          if (typeof(ver)=='string'){
              select_list = '<option value="' + ver +'">' + rdata[i]['title'] + ' - ' + ver + '</option>';
          } else {
              for (var vi = 0; vi < ver.length; vi++) {

                  if (ver[vi] == rdata[i]['default_ver']){
                      select_list += '<option value="'+ver[vi]+'" selected="selected">'+ rdata[i]['title'] + ' - '+ ver[vi] + '</option>';
                  } else {
                      select_list += '<option value="'+ver[vi]+'">'+ rdata[i]['title'] + ' - '+ ver[vi] + '</option>';
                  }
              }
          }

          var pn_checked = '<input id="data_'+rdata[i]['name']+'" type="checkbox" checked>';
          if (rdata[i]['name'] == 'swap'){
              var pn_checked = '<input id="data_'+rdata[i]['name']+'" type="checkbox" disabled="disabled" checked>';
          }
          
          plugin_list += '<li><span class="ico"><img src="/plugins/file?name='+rdata[i]['name']+'&f=ico.png"></span>\
          <span class="name">\
              <select id="select_'+rdata[i]['name']+'" class="sl-s-info">'+select_list+'</select>\
          </span>\
          <span class="pull-right">'+pn_checked+'</span></li>';
      }

      layer.open({
          type: 1,
          title: '推荐安装',
          area: ["320px", "400px"],
          closeBtn: 2,
          shadeClose: false,
          content:"\
      <div class='rec-install'>\
          <div class='important-title'>\
              <p><span class='glyphicon glyphicon-alert' style='color: #f39c12; margin-right: 10px;'></span>推荐以下一键套件，或在<a href='javascript:jump()' style='color:#20a53a'>软件管理</a>按需选择。</p>\
              <!-- <button style='margin-top: 8px;height: 30px;' type='button' class='btn btn-sm btn-default no-show-rec-btn'>不再显示推荐</button> -->\
          </div>\
          <div class='rec-box'>\
              <h3 style='text-align: center'>经典LNMP</h3>\
              <div class='rec-box-con'>\
                  <ul class='rec-list'>" + plugin_list + "</ul>\
                  <div class='onekey'>一键安装</div>\
              </div>\
          </div>\
      </div>",
          success:function(l,index){
              $('.rec-box-con .onekey').click(function(){
                  var post_data = [];
                  for (var i = 0; i < rdata.length; i++) {
                      var key_ver = '#select_'+rdata[i]['name'];
                      var key_checked = '#data_'+rdata[i]['name'];

                      var val_checked = $(key_checked).prop("checked");
                      if (val_checked){

                          var tmp = {};
                          var val_key = $(key_ver).val();

                          tmp['version'] = val_key;
                          tmp['name'] = rdata[i]['name'];
                          post_data.push(tmp);
                      }
                  }

                  $.post('/plugins/init_install', 'list='+JSON.stringify(post_data), function(data){
                      showMsg(data.msg, function(){
                          if (data.status){
                              layer.closeAll();
                              messageBox();
                              indexSoft();
                          }
                      },{ icon: data.status ? 1 : 2 },2000);
                  },'json');
              });   
          },
          cancel:function(){
              layer.closeAll();
              // layer.confirm('是否不再显示推荐安装套件?', {btn : ['确定', '取消'],title: "不再显示推荐?"}, function() {
              //     $.post('/files/create_dir', 'path=/www/server/php', function(rdata) {
              //         layer.closeAll();
              //     },'json');
              // });
          }
      });
  },'json');
}

function loadKeyDataCount(){
  var plist = ['mysql', 'gogs', 'gitea'];
  for (var i = 0; i < plist.length; i++) {
      pname = plist[i];
      function call(pname){
          $.post('/plugins/run', {name:pname, func:'get_total_statistics'}, function(data) {
              try {
                  var rdata = $.parseJSON(data['data']);
              } catch(e){
                  return;
              }
              if (!rdata['status']){
                  return;
              }
              var html = '<li class="sys-li-box col-xs-3 col-sm-3 col-md-3 col-lg-3">\
                      <p class="name f15 c9">'+pname+'</p>\
                      <div class="val"><a class="btlink" onclick="softMain(\''+pname+'\',\''+pname+'\',\''+rdata['data']['ver']+'\')">'+rdata['data']['count']+'</a></div>\
                  </li>';
              $('#index_overview').append(html);
          },'json');
      }
      call(pname);
  }
}
