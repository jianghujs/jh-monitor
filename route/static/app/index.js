
function getHostCharts() {
  for (let i = 0; i < 6; i++) {
    createHostChart(i);
  }
}


// 主机图表
function createHostChart(host_id) {
  
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
    setData(d) {
      const colors = ['#5470C6', '#91CC75', '#EE6666', ];
      // 模拟数据
      let cpu_history = [
        {id: 168901, pro: 43.7, mem: 53.13726627703006, addtime: "11/03 00:00"},
        {id: 168902, pro: 100, mem: 54.07751697121776, addtime: "11/03 00:01"},
        {id: 168903, pro: 71.6, mem: 60.346975585265625, addtime: "11/03 00:03"},
        {id: 168904, pro: 90.5, mem: 72.29185875221229, addtime: "11/03 00:05"}
      ];

      let disk_io_history = [
        {"id": 168906, "read_bytes": 5439488, "write_bytes": 9777152, "addtime": "11/03 00:00"}, 
        {"id": 168907, "read_bytes": 20480, "write_bytes": 6459392, "addtime": "11/03 00:01"}, 
        {"id": 168908, "read_bytes": 0, "write_bytes": 3047424, "addtime": "11/03 00:03"}, 
        {"id": 168909, "read_bytes": 0, "write_bytes": 3067904, "addtime": "11/03 00:05"}
      ];

      let net_io_history = [
        {"id": 168905, "up": 74.066, "down": 82.152, "addtime": "11/03 00:00"},
        {"id": 168905, "up": 74.066, "down": 82.152, "addtime": "11/03 00:01"},
        {"id": 168905, "up": 74.066, "down": 82.152, "addtime": "11/03 00:03"}
      ];

      // 数据处理
      const xData = cpu_history.map(item => item.addtime);
      const cpuData = cpu_history.map(item => item.pro.toFixed(2));
      const memData = cpu_history.map(item => item.mem.toFixed(2));
      const readData = disk_io_history.map(item => (item.read_bytes / 1024).toFixed(2));
      const writeData = disk_io_history.map(item => (item.write_bytes / 1024).toFixed(2));
      const netUpData = net_io_history.map(item => item.up.toFixed(2));
      const netDownData = net_io_history.map(item => item.down.toFixed(2));

      // 配置项
      let option = {
        title: {
          text: `主机${host_id}`,
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
}
