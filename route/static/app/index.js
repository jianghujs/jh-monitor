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
  $('#hostCharts').append(`<div id="${chartId}" style="width:100%; height:330px"></div>`);
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
      const colors = ['#5470C6', '#91CC75', '#EE6666', ];
      const { cpu_history = [], mem_history = [], disk_io_history = [], net_io_history = [] } = d;

      // 数据处理
      const xData = cpu_history.map(item => item.addtime);
      const cpuData = cpu_history.map(item => item.pro.toFixed(2));
      const memData = mem_history.map(item => item.mem.toFixed(2));
      const readData = disk_io_history.map(item => (item.read_bytes / 1024).toFixed(2));
      const writeData = disk_io_history.map(item => (item.write_bytes / 1024).toFixed(2));
      const netUpData = net_io_history.map(item => item.up.toFixed(2));
      const netDownData = net_io_history.map(item => item.down.toFixed(2));
      
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
          data: ['CPU', '内存', '磁盘读取', '磁盘写入', '网络上传', '网络下载'],
          top: '50px', // 将图例放在标题下方
          left: 'center',
          width: '80%'
        },
        grid: {
          top: '150px', // 增加顶部间距以避免重叠
          left: '3%',
          right: '4%',
          bottom: '3%',
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
            name: 'IO (KB/s)',
            min: 0,
            max: 10000, // 根据数据适当调整最大值
            position: 'right',
            axisLine: {
              lineStyle: {
                color: 'rgb(255, 70, 131)'
              }
            }
          }
        ],
        series: [
          {
            name: 'CPU',
            type: 'line',
            yAxisIndex: 0,
            data: cpuData,
            smooth: true,
            symbol: 'none',
            itemStyle: {
              color: 'rgb(0, 153, 238)'
            }
          },
          {
            name: '内存',
            type: 'line',
            yAxisIndex: 0,
            data: memData,
            smooth: true,
            symbol: 'none',
            itemStyle: {
              color: 'rgb(255, 165, 0)'
            }
          },
          {
            name: '磁盘读取',
            type: 'line',
            yAxisIndex: 1,
            data: readData,
            smooth: true,
            symbol: 'none',
            itemStyle: {
              color: 'rgb(75, 192, 192)'
            }
          },
          {
            name: '磁盘写入',
            type: 'line',
            yAxisIndex: 1,
            data: writeData,
            smooth: true,
            symbol: 'none',
            itemStyle: {
              color: 'rgb(255, 99, 132)'
            }
          },
          {
            name: '网络上传',
            type: 'line',
            yAxisIndex: 1,
            data: netUpData,
            smooth: true,
            symbol: 'none',
            itemStyle: {
              color: 'rgb(54, 162, 235)'
            }
          },
          {
            name: '网络下载',
            type: 'line',
            yAxisIndex: 1,
            data: netDownData,
            smooth: true,
            symbol: 'none',
            itemStyle: {
              color: 'rgb(153, 102, 255)'
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
      };

      hostChartMap[host_id].setData({
        cpu_history,
        mem_history,
        disk_io_history,
        net_io_history
      });
    }
  }, 'json');
}