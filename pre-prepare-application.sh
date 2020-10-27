#!/bin/bash
###############################################################################
#
#   Copyright (C) KPN-ITNS / Glashart Media
#   All Rights Reserved
#
#   File:           pre-prepare-application.sh
#   Author:         H.A. Oldenburger
#   Date:           10 April March 2014
#   Purpose:        Deployment script for a CentOS 
#
#   Please Notice:  This script does not deploy the database 
#					because the database is uploaded
#                   from the former production Virtual Machine.
#
###############################################################################

# Disable IPv6
#echo "+-----KPN-ITNS----> Disable IPv6"
#sysctl -w "net.ipv6.conf.all.disable_ipv6=1"
#sysctl -w "net.ipv6.conf.default.disable_ipv6=1"
  
# Copy postgresql definitive configuration files to /var/lib/pgsql/data.  
echo "+-----KPN-ITNS----> copy postgresql definitive configuration files to /var/lib/pgsql/data"  
cp /srv/simplevod/database/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf
cp /srv/simplevod/database/pg_ident.conf /var/lib/pgsql/data/pg_ident.conf

# Restart postgresql service.
echo "+-----KPN-ITNS----> restart postgresql service"
service postgresql restart

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






