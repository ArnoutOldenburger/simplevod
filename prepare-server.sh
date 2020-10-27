#!/bin/bash
###############################################################################
#
#   Copyright (C) KPN-ITNS / Glashart Media
#   All Rights Reserved
#
#   File:        	prepare-server.sh
#   Author:         H.A. Oldenburger
#   Date:           25 March 2014
#   Purpose:        Deployment script for a CentOS 
#
###############################################################################

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

# Start postgresql as a service.
echo "+-----KPN-ITNS----> start postgresql as a service"
service postgresql initdb
service postgresql start

# Make sure postgresql is started on reboot.
echo "+-----KPN-ITNS----> make sure postgresql is started on reboot"
chkconfig postgresql on










