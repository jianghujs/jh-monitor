FROM debian:10.12-slim

STOPSIGNAL SIGRTMIN+3

RUN rm -f /lib/systemd/system/multi-user.target.wants/* \
  /etc/systemd/system/*.wants/* \
  /lib/systemd/system/local-fs.target.wants/* \
  /lib/systemd/system/sockets.target.wants/*udev* \
  /lib/systemd/system/sockets.target.wants/*initctl* \
  /lib/systemd/system/sysinit.target.wants/systemd-tmpfiles-setup* \
  /lib/systemd/system/systemd-update-utmp*

RUN apt update -y && \
	apt install -y devscripts && \
	apt install -y wget zip unzip && \
    apt-get install -y locales && \
    localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8 && \
    locale-gen en_US.UTF-8 && \
    export LC_ALL=en_US.UTF-8 && \
    export LANG=en_US.UTF-8 && \
    export LANGUAGE=en_US.UTF-8 && \
    localedef -i en_US -f UTF-8 en_US.UTF-8 && \
    mkdir -p /www/server && \
	wget -O /tmp/dev.zip https://github.com/jianghujs/jh-monitor/archive/refs/heads/dev.zip && \
	cd /tmp && unzip /tmp/dev.zip && \
	mv -f /tmp/jh-monitor-dev /www/server/jh-monitor && \
	rm -rf /tmp/dev.zip && \
	rm -rf /tmp/jh-monitor-dev && \
    cd /www/server/jh-monitor && \
    bash scripts/install/debian.sh && \
    cd /www/server/jh-monitor/ && \
    /www/server/jh-monitor/bin/python tools.py username username && \
    cd /www/server/jh-monitor/ && \
    /www/server/jh-monitor/bin/python tools.py panel password

RUN cd /www/server/jh-monitor/plugins/php && \
    bash install.sh install 74 && \
    cd /www/server/jh-monitor/plugins/openresty && \
    bash install.sh install 1.21.4.1 && \
    cd /www/server/jh-monitor/plugins/mysql && \
    bash install.sh install 5.6 && \
    cd /www/server/jh-monitor/plugins/phpmyadmin && \
    bash install.sh install 4.4.15 && \
    systemctl enable openresty && \
    systemctl enable php74 && \
    systemctl enable mysql

RUN rm -rf /www/server/mysql/data

ADD ./start.sh /start.sh
ADD start.service /usr/lib/systemd/system/start.service
#RUN systemctl enable start

CMD [ "/lib/systemd/systemd", "log-level=info", "unit=sysinit.target" ]

EXPOSE 7200 80 443 888

VOLUME [ "/www" ]