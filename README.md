
### 简介

简单的Debian面板

### 环境

- Debian 11.5

### 安装

##### 国际源

```bash
apt update -y && apt install -y wget && wget -O /tmp/install.sh https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/install.sh && bash /tmp/install.sh
```

##### 中国源

```bash
apt update -y && apt install -y wget && wget -O /tmp/install.sh https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/install.sh && bash /tmp/install.sh cn
```

### 卸载
  
##### 国际源

```bash
wget -O /tmp/uninstall.sh https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/uninstall.sh && bash /tmp/uninstall.sh
```

##### 中国源

```bash
wget -O /tmp/uninstall.sh https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/uninstall.sh && bash /tmp/uninstall.sh
```

### 授权许可

本项目采用 Apache 开源授权许可证，完整的授权说明已放置在 [LICENSE](https://github.com/jianghujs/jh-monitor/blob/master/LICENSE) 文件中。

