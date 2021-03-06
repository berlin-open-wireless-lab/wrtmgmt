#!/usr/bin/env bash


# LDAP install

echo "127.0.1.1 vagrant-ubuntu-trusty-64.OpenWifi.local vagrant-ubuntu-trusty-64" >> /etc/hosts

debconf-set-selections <<< 'slapd slapd/password1 password ldap'
debconf-set-selections <<< 'slapd slapd/password2 password ldap'

apt-get -y install slapd ldap-utils

ldapadd -x -D cn=admin,dc=OpenWifi,dc=local -w ldap -f /vagrant/add_content.ldif

/etc/init.d/slapd restart

# install openwifi
apt-get update
apt-get -y install rabbitmq-server python3-pip git redis-server

pip3 install virtualenv

adduser \
   --system \
   --shell /bin/bash \
   --gecos 'User for managing of openwifi' \
   --group \
   --disabled-password \
   --home /home/openwifi \
   openwifi

cp /vagrant/openwifi-jobserver-beat.conf /etc/init
cp /vagrant/openwifi-jobserver.conf /etc/init

# deploy keys
mkdir /home/openwifi/.ssh
chmod 700 /home/openwifi/.ssh
cp -rv /vagrant/deploy_keys/* /home/openwifi/.ssh/
chown -R openwifi:openwifi /home/openwifi/.ssh
chmod 600 /home/openwifi/.ssh/*

# install openwifi as openwifi user
su openwifi -c "cd ~; git clone git@gitlab.inet.tu-berlin.de:OpenWiFi/Controller.git; cd Controller;mv development.ini devel.bak.ini; sed s/127.0.0.1/0.0.0.0/g devel.bak.ini > development.ini; virtualenv venv; . venv/bin/activate; pip install -r requirements.txt; python setup.py develop; initialize_openwifi_db development.ini;cp /vagrant/openwifi.wsgi ."

#start openwifi
start openwifi-jobserver
start openwifi-jobserver-beat


# Icinga2 Install

wget -O - http://packages.icinga.org/icinga.key | apt-key add -
echo 'deb http://packages.icinga.org/ubuntu icinga-trusty main' > /etc/apt/sources.list.d/icinga-main-trusty.list

apt-get update
apt-get -y install icinga2
debconf-set-selections <<< 'mysql-server mysql-server/root_password password mysql'
debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password mysql'
apt-get -y install mysql-server mysql-client 

debconf-set-selections <<< 'icinga2-ido-mysql icinga2-ido-mysql/enable boolean false'
debconf-set-selections <<< 'dbconfig-common dbconfig-common/dbconfig-install boolean false'
debconf-set-selections <<< 'icinga2-ido-mysql icinga2-ido-mysql/dbconfig-install boolean false'
debconf-set-selections <<< 'dbconfig-common dbconfig-common/upgrade-backup boolean false'
debconf-set-selections <<< 'dbconfig-common dbconfig-common/dbconfig-remove boolean false'
debconf-set-selections <<< 'dbconfig-common dbconfig-common/dbconfig-upgrade boolean false'
debconf-set-selections <<< "icinga2-ido-mysql icinga2-ido-mysql/password-confirm password icinga"
debconf-set-selections <<< "icinga2-ido-mysql icinga2-ido-mysql/app-password-confirm password icinga"
debconf-set-selections <<< "icinga2-ido-mysql icinga2-ido-mysql/mysql/admin-pass password mysql"
debconf-set-selections <<< "icinga2-ido-mysql icinga2-ido-mysql/mysql/app-pass password icinga"
apt-get -y install icinga2-ido-mysql
apt-get -y install icingaweb2

cp -rv /vagrant/icinga/* /

mysql -uroot -pmysql -e "CREATE DATABASE IF NOT EXISTS icinga ; GRANT ALL ON icinga.* TO icinga@localhost IDENTIFIED BY 'icinga';"
mysql -uicinga -picinga icinga < /usr/share/icinga2-ido-mysql/schema/mysql.sql
mysql -uroot -pmysql -e "CREATE DATABASE IF NOT EXISTS icingaweb2 ; GRANT ALL ON icingaweb2.* TO icingaweb2@localhost IDENTIFIED BY 'icingaweb2';"
mysql -uicingaweb2 -picingaweb2 icingaweb2 < /usr/share/icingaweb2/etc/schema/mysql.schema.sql
mysql -uicingaweb2 -picingaweb2 icingaweb2 -e "INSERT INTO icingaweb_user (name, active, password_hash) VALUES ('icingaadmin', 1, '\$1\$iQSrnmO9\$T3NVTu0zBkfuim4lWNRmH.');"

/etc/init.d/mysql restart

#setup apache mod_wsgi

apt-get -y install libapache2-mod-wsgi-py3 

cp /vagrant/openwifi.conf /etc/apache2/conf-available
cd /etc/apache2/conf-enabled
ln -s ../conf-available/openwifi.conf

#rights to the database
chgrp www-data /home/openwifi
chmod 770 /home/openwifi
chgrp www-data /home/openwifi/Controller
chmod 770 /home/openwifi/Controller
chgrp www-data /home/openwifi/Controller/openwifi.sqlite
chmod 660 /home/openwifi/Controller/openwifi.sqlite

# install index site

cp /home/openwifi/Controller/openwifi/static/index.html /var/www/html
cp /home/openwifi/Controller/openwifi/static/sites.json /var/www/html
mkdir /var/www/html/js
mkdir /var/www/html/css
cp /home/openwifi/Controller/openwifi/static/css/bootstrap.min.css /var/www/html/css
cp /home/openwifi/Controller/openwifi/static/css/base_layout.css /var/www/html/css
cp /home/openwifi/Controller/openwifi/static/js/jquery.js /var/www/html/js
cp /home/openwifi/Controller/openwifi/static/js/bootstrap.min.js /var/www/html/js
chgrp -R www-data /var/www/html
chown -R www-data /var/www/html

#cp /vagrant/mpm_prefork.conf /etc/apache2/mods-available/
service apache2 restart


# install avahi
apt-get install -y avahi-daemon
cp /vagrant/openwifi.service /etc/avahi/services/openwifi.service
/etc/init.d/avahi-daemon restart

# use dnsmasq as dhcp server
apt-get install -y dnsmasq
echo "interface=eth1" >> /etc/dnsmasq.conf
echo "bind-interfaces" >> /etc/dnsmasq.conf
echo "dhcp-range=192.168.50.100,192.168.50.254,12h" >> /etc/dnsmasq.conf
/etc/init.d/dnsmasq restart


