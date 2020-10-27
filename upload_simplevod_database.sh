#!/bin/bash
###############################################################################
#
#   Copyright (C) KPN-ITNS / Glashart Media
#   All Rights Reserved
#
#   File:           upload_simplevod_database.sh
#   Author:         H.A. Oldenburger
#   Date:           10 April 2014
#   Purpose:        Used with switching from production-VM to pre-production-VM 
#
###############################################################################

# Copy postgresql initial configuration files to /var/lib/pgsql/data.  
echo "+-----KPN-ITNS----> copy postgresql dump configuration files to /var/lib/pgsql/data"  
sudo cp /srv/simplevod/database/dump_pg_hba.conf /var/lib/pgsql/data/pg_hba.conf

# Restart postgresql service.
echo "+-----KPN-ITNS----> restart postgresql service"
sudo service postgresql restart

sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'simplevod';"

su postgres

dropdb simplevod

sudo -i -u postgres createdb simplevod

pg_restore --dbname=simplevod --verbose backup_file.tar

# Restore postgresql regular operational configuration files to /var/lib/pgsql/data.  
echo "+-----KPN-ITNS----> Restore postgresql regular operational configuration files to /var/lib/pgsql/data "  
cp /srv/simplevod/database/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf

# Restart postgresql service.
echo "+-----KPN-ITNS----> restart postgresql service"
service postgresql restart


