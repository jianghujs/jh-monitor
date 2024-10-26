
### 简介

简单的Debian面板

### 环境

- Debian 11.5

### 安装

```bash
apt update -y && apt install -y wget && wget -O install.sh https://raw.githubusercontent.com/jianghujs/jh-monitor/master/scripts/install.sh && bash install.sh
```

### 安装（中国源）

```bash
apt update -y && apt install -y wget && wget -O install.sh https://gitee.com/jianghujs/jh-monitor/raw/master/scripts/install.sh && bash install.sh cn
```

### 授权许可

本项目采用 Apache 开源授权许可证，完整的授权说明已放置在 [LICENSE](https://github.com/jianghujs/jh-monitor/blob/master/LICENSE) 文件中。

### FAQ

- 重命名: 
    - `mv /www/server/mdserver-web /www/server/jh-monitor`
    - `cd /www/server/jh-monitor && git pull && bash /www/server/jh-monitor/scripts/update.sh`
