#!/bin/bash
###############################################################################
#
#   Copyright (C) KPN-ITNS / Glashart Media
#   All Rights Reserved
#
#   <Module>:=      [deploy-centos.sh]
#   Author:         H.A. Oldenburger
#   Date:           18 March 2014
#   Purpose:        Vagrant deploy-script for a CentOS 6.5 VM
#
#   <Date-Time>:=   [20140318/09:00:00]
#
#   Amendment history:
#   20140318    AO  Initial version
#
###############################################################################

USER=simplevod
USERID=2001

GROUP=simplevod
GROUPID=2001

ROOT=/srv/simplevod

HOME=/srv/simplevod

echo "+-----KPN-ITNS----> I am provisioning..."
date > /etc/vagrant_provisioned_at

umask 002

# Disable IPv6
echo "+-----KPN-ITNS----> Disable IPv6"
sysctl -w "net.ipv6.conf.all.disable_ipv6=1"
sysctl -w "net.ipv6.conf.default.disable_ipv6=1"

# Install dependencies
echo "+-----KPN-ITNS----> Install dependencies"

# Update packages for CentOS ...
echo "+-----KPN-ITNS----> update packages for CentOS ..."
yum update -y

# Installation python-setuptools mod_wsgi.
echo "+-----KPN-ITNS----> installation python-setuptools mod_wsgi"
yum install -y python-setuptools mod_wsgi
 
# Installation httpd httpd-tools.
echo "+-----KPN-ITNS----> installation httpd httpd-tools"
yum install -y httpd httpd-tools
 
# Installation django. 
echo "+-----KPN-ITNS----> installation django" 
#yum install -y Django
yum -y install python-pip
pip install django==1.5.4

# Installation postgresql postgresql-server.
echo "+-----KPN-ITNS----> installation postgresql postgresql-server" 
yum install -y postgresql postgresql-server 

# python-psycopg2 in CentOS is too old, it does not have autocommit;
# install from PyPI instead.
echo "+-----KPN-ITNS----> installation psycopg2 from PyPI" 
yum install -y python-devel postgresql-devel
easy_install psycopg2

# Create symlink /srv/simplevod to /vagrant.
echo "+-----KPN-ITNS----> create symlink /srv/simplevod to /vagrant" 
ln -s /vagrant /srv/simplevod

# Create application user (pre-requisite for correct ownership synced_folder).
#echo "+-----KPN-ITNS----> create application user" 
#groupadd -f -g "${GROUPID}" "${GROUP}"
#if [ ! $(id -u "${USER}" 2>/dev/null) ]; then
#    useradd -d "${HOME}" -m -g "${GROUPID}" -u "${USERID}" -s "${SHELL}" "${USER}"
#fi
#chown -R "${USER}":"${GROUP}" "${ROOT}"

# Start postgresql as a service.
echo "+-----KPN-ITNS----> start postgresql as a service"
service postgresql initdb
service postgresql start

# Make sure postgresql is started on reboot.
echo "+-----KPN-ITNS----> make sure postgresql is started on reboot"
chkconfig postgresql on

# Copy postgresql configuration files to /var/lib/pgsql/data.  
echo "+-----KPN-ITNS----> copy postgresql configuration files to /var/lib/pgsql/data"  
cp /srv/simplevod/database/init_pg_hba.conf /var/lib/pgsql/data/pg_hba.conf

# Restart postgresql service.
echo "+-----KPN-ITNS----> restart postgresql service"
service postgresql restart

# Create simplevod database.
echo "+-----KPN-ITNS----> create simplevod database as default postgresql user postgres"
sudo -i -u postgres createdb simplevod

# Create database tables based on django database models.
echo "+-----KPN-ITNS----> create database tables based on django database models"
cd /srv/simplevod
python manage_syncdb.py syncdb --noinput

# Run script to load data from json-source to postgreSQL-destination.
echo "+-----KPN-ITNS----> run script to load data from json-source to postgreSQL-destination"
cd /srv/simplevod/database
python SimplevodLoadDatabase.py
  
# Make sure the update-script is executable.
echo "+-----KPN-ITNS----> make sure the update-script is executable"
cd /srv/simplevod/database
chmod +x SimplevodUpdateDatabase.py 

# Copy the update-script to the /usr/local/bin-directory so crontab may execute it.
echo "+-----KPN-ITNS----> copy the update-script to the /usr/local/bin-directory so crontab may execute it"
sudo cp /srv/simplevod/database/SimplevodUpdateDatabase.py /usr/local/bin/

# Schedule update-script to load data from json-source to postgreSQL-destination.
echo "+-----KPN-ITNS----> schedule update-script to load data from json-source to postgreSQL-destination"
crontab simplevod_crontab

# Upload Apache Basic Authentication - user - as a - superuser - to the SimpleVoD Site Administration database.
echo "+-----KPN-ITNS----> upload Apache Basic Authentication - user - as a - superuser - to the SimpleVoD Site Administration database"
cd /srv/simplevod/database
python UploadSuperuser.py 
  
# Make logfile directory.
echo "+-----KPN-ITNS----> make logfile directory"
mkdir /var/log/simplevod
chown apache:apache /var/log/simplevod 

# Symlink Django-admin static files from share to simplevod static file directory.
echo "+-----KPN-ITNS----> copy Django-admin static files from python site-packages to simplevod static file directory"
ln -s /usr/lib/python2.6/site-packages/django/contrib/admin/static/admin /srv/simplevod/static

# Make seperate directory for authentication files.
echo "+-----KPN-ITNS----> make seperate directory for authentication files"
mkdir /usr/local/etc/httpd

# Copy authentication files to this directory.
echo "+-----KPN-ITNS----> copy authentication files to this directory"
cp /srv/simplevod/apache/.htpasswd /usr/local/etc/httpd/
cp /srv/simplevod/apache/.htgroup /usr/local/etc/httpd/

# Link web server configuration file, remove CentOS welcome page.
echo "+-----KPN-ITNS----> copy web server configuration file, remove CentOS welcome page"
ln -s /srv/simplevod/apache/simplevod.conf.auth /etc/httpd/conf.d/simplevod.conf
rm /etc/httpd/conf.d/welcome.conf
#chown apache.apache /etc/httpd/conf.d/httpd.conf 

# Start web server and make sure it is started at reboot.
echo "+-----KPN-ITNS----> start web server and make sure it is started at reboot"
service httpd start
chkconfig httpd on






