SimpleVoD
=========

SimpleVoD-application for CloudTV.
Branched for Django ( Django is a high-level Python Web framework ).

Installing SimpleVoD on CentOS 6.5. 
-------
This is a clean install without database recovery.
Refer to paragraph - Installing SimpleVoD with maintaining database -
to install Simplevod using an existing database.

### 1.1. Create user and deployment directory

Create user `simplevod` and add the current user to the group:

```
$ sudo useradd -M -d /srv/simplevod simplevod
$ sudo usermod -a -G simplevod "$USER"
```

Logout your current SSH session and login once again to check the umask and id ( take notice: login with _Agent Forwarding_, i.e. to carry a current ssh-key - known to GitHub - to another shell, like for instance `ssh -A -l arnout 82.139.73.36` ): 

Check your user identity with `id` and look for membership of group `simplevod`. It should look like this:
```
$ id
uid=500(vagrant) gid=500(vagrant) groups=500(vagrant),501(simplevod) context=unconfined_u:unconfined_r:unconfined_t:s0-s0:c0.c1023
```

### 1.2. Download application from GitHub

Create the deployment directory:

```
$ sudo mkdir /srv/simplevod
$ sudo chown simplevod:simplevod /srv/simplevod
$ sudo chmod 2775 /srv/simplevod
```

#####Initialize the git repository:
```
$ cd /srv/simplevod
$ git init --shared=group
Initialized empty shared Git repository in /srv/simplevod/.git/

$ git remote add origin git@github.com:zt6/simplevod.git
```
Verify the new ( remote ) repository :
```
$ git remote -v
origin  git@github.com:zt6/simplevod.git (fetch)
origin  git@github.com:zt6/simplevod.git (push)
```

Check access to GitHub.
It should be similar to this:
```
$ ssh-add -l
2048 5e:92:c7:3a:0a:4a:10:57:54:12:8f:1e:a1:13:cf:2b id_rsa (RSA)

$ ssh -T git@github.com
Hi aoldenburger! You've successfully authenticated, but GitHub does not provide shell access.
```

#####Fetch the SimpleVoD application from GitHub:
```
$ cd /srv/simplevod
$ git fetch origin
$ git merge --ff-only origin/arnout
```
It should look like this ( pay attention to the fact that the owner-group for these files is `simplevod` ):
```
$ ls -al

total 84
drwxrwsr-x. 12 simplevod simplevod 4096 Mar 26 13:23 .
drwxr-xr-x.  3 root      root      4096 Mar 26 13:11 ..
drwxrwsr-x.  2 vagrant   simplevod 4096 Mar 26 13:23 admin
drwxrwsr-x.  2 vagrant   simplevod 4096 Mar 26 13:23 apache
drwxrwsr-x.  2 vagrant   simplevod 4096 Mar 26 13:23 cfg
drwxrwsr-x.  2 vagrant   simplevod 4096 Mar 26 13:23 database
-rw-rw-r--.  1 vagrant   simplevod 5865 Mar 26 13:23 deploy-centos.sh
drwxrwsr-x.  8 vagrant   simplevod 4096 Mar 26 13:23 .git
-rw-rw-r--.  1 vagrant   simplevod   19 Mar 26 13:23 .gitignore
-rw-rw-r--.  1 vagrant   simplevod  389 Mar 26 13:23 manage.py
-rw-rw-r--.  1 vagrant   simplevod  396 Mar 26 13:23 manage_syncdb.py
drwxrwsr-x.  2 vagrant   simplevod 4096 Mar 26 13:23 orderedmodel
-rw-rw-r--.  1 vagrant   simplevod 3789 Mar 26 13:23 prepare-application.sh
-rw-rw-r--.  1 vagrant   simplevod 1691 Mar 26 13:23 prepare-server.sh
drwxrwsr-x.  5 vagrant   simplevod 4096 Mar 26 13:23 pyld
-rw-rw-r--.  1 vagrant   simplevod 3329 Mar 26 13:23 README.md
drwxrwsr-x.  2 vagrant   simplevod 4096 Mar 26 13:23 simplevod
drwxrwsr-x.  6 vagrant   simplevod 4096 Mar 26 13:23 static
drwxrwsr-x.  3 vagrant   simplevod 4096 Mar 26 13:23 templates
-rw-rw-r--.  1 vagrant   simplevod  233 Mar 26 13:23 Vagrantfile
```

### 1.3. Prepare Server

By the next script the following actions are performed:

#####A. Update packages for CentOS.
#####B. Installation python-setuptools and mod_wsgi.
#####C. Installation httpd and httpd-tools.
#####D. Installation django 1.5.4 with pip. 
#####E. Installation postgresql and postgresql-server.
#####F. Installation python-psycopg2.
Standard python-psycopg2 in CentOS is too old ( it does not have autocommit ). Install from PyPI instead.
#####G. Start postgresql as a service and make sure postgresql is started on reboot.

```
$ cd /srv/simplevod
$ sudo sh ./prepare-server.sh
```

### 1.4. Setup Database

#####On Ubuntu, by default, PostgreSQL has no DB password set for user `postgres`:
```
$ sudo su -
$ sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'simplevod';"
$ exit
```

### 1.5. Prepare Application
By the next script the following actions are performed:

#####A. Create a new PostgreSQL database.
Create model-tables ( based on the specified Django `models`, i.e. the single definitive source of data about data ) in the `simplevod` database with the Django `syncdb` command.

#####B. Run script to load data from json-source to postgreSQL-destination.

<i>
The script uses a configuration file ( look for file `config.json` in directory `/srv/simplevod/cfg` )
to read out data from a range of different data-sources. 

Use this link https://github.com/zt6/simplevod/blob/master/cfg/README.md to read about the configuration file.

( Please be sure you have all your relevant data-sources mentioned in this configuration-file. Consecutive database updates are done based on this initial load. In the directory `/srv/simplevod/cfg` an extra sample configuration-file  `config_with_xml.json` is present. )
</i>

#####C. Upload Apache Basic Authentication - user - as a - superuser - to the SimpleVoD Site Administration database.
The superuser is also present in the group file `.htgroup` and password file `htpasswd` ( see step F. ).

#####D. Connect to the database through UNIX domain sockets.
With UNIX socket connection PostgreSQL uses the peer authentication method with the <i>map</i> configuration option ( allows for mapping between system and database user names ).<br> Therefore the PostgreSQL client-authentication configuration-file `pg_hba.conf` has been modified: 
```
# "local" is for Unix domain socket connections only
local   simplevod   postgres                               ident map=svod

host    simplevod   postgres        ::1/128                md5
```
And in `pg_ident.conf` a line is added that maps the name of the (default) PostgreSQL user `postgres` with the name of the (default) Apache user `apache`.
```
# MAPNAME       SYSTEM-USERNAME         PG-USERNAME
svod            apache                  postgres
```

#####E. Enable logging.
Make seperate directory for `simplevod` logging ( `/var/log/simplevod` ). Logfile named _simplevod.log_ is automatically created by the `simplevod` application in the logging-directory. Logging is done via a socalled _RotatingFileHandler_ which is configured with 5 log files, 5 Mb each. 

#####F. Install the Simplevod configuration-file with directives for Apache Basic Authentication.
(Possibly) Manage user files for Apache basic authentication before using them ( refer to: http://httpd.apache.org/docs/2.2/programs/htpasswd.html ):

The password file `.htpasswd` contains three test-users accounts and one superuser-account:

 (login)name    | password     | superuser |
| ------------- |:------------:|:---------:|
| simplevod     | simplevod    | yes       |
| art           | helloworld   | no        |
| jane          | helloworld   | no        |
| martin        | helloworld   | no        |

Here is a list of operations to change the content of the `.htpasswd` password file:
- To add another user (james): <i>sudo htpasswd /usr/local/etc/httpd/.htpasswd james</i>
- To change the password of an existing user (james): <i>sudo htpasswd /usr/local/etc/httpd/.htpasswd james</i>
- To delete an existing user (james): <i>sudo htpasswd -D /usr/local/etc/httpd/.htpasswd james</i>

Synchronise the group file `.htgroup` with the alterations you made to `htpasswd`. 
<i>( a group file associates group names with a list of users in that group. The format of this file is pretty simple. It's just a list of the members of the group in a long line separated by spaces )</i>

```
$ cd /srv/simplevod
$ sudo sh ./prepare-application.sh
```

### 1.6. Update Database

#####Copy the update-script to the `/usr/local/bin`-directory so `crontab` may execute it:
```
$ sudo cp /srv/simplevod/database/SimplevodUpdateDatabase.py /usr/local/bin/
```

#####Schedule update-script to load data from json-source to postgreSQL-destination:
```
$ crontab simplevod_crontab
```
Check the crontab command is correctly configured:
```
$ crontab -l
```
Output should look like this ( a database update is scheduled every half hour ):
```
*/30 * * * * /usr/local/bin/SimplevodUpdateDatabase.py -p /srv/simplevod/database
```

Logfile named <i>update_database.log</i> is automatically created by the update-script in the  `/srv/simplevod/database`-directory. Logging is done via a socalled _RotatingFileHandler_ which is configured with 5 log files, 5 Mb each. 

### 1.7. Testing SimpleVoD-application for CloudTV
Try the following url for SimpleVoD-application for CloudTV. `<`outbound-ip-address-host`>`/simplevod<br>
Try the following url for SimpleVoD Site Administration. `<`outbound-ip-address-host`>`/admin<br>

###<i>End of Installing SimpleVoD </i>


---

Installing SimpleVoD with maintaining database 
-------
Use this protocol when switching from <i>SimpleVoD production VM</i> to <i>SimpleVoD pre-production VM</i>.

### 2.1. Backup SimpleVoD Database on the source machine

#####Copy postgresql initial configuration files to /var/lib/pgsql/data: 
```
$ sudo cp /srv/simplevod/database/init_pg_hba.conf /var/lib/pgsql/data/pg_hba.conf
```

#####Restart postgresql service:
```
$ sudo service postgresql restart
```

#####Set DB password for user postgres:
```
$ sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'simplevod';"
```

#####Use PostgreSQL utility program pg_dump to compress data and write it to a output file of type tar:
When prompted for a password, give in the password that is just set for user `postgres`.
So Password:`simplevod`
```
$ sudo pg_dump -U postgres -W -F t simplevod > /srv/simplevod/database/simplevod_database.tar
```

#####Restore postgresql regular operational configuration files to /var/lib/pgsql/data:
```
$ sudo cp /srv/simplevod/database/pg_hba.conf /var/lib/pgsql/data/pg_hba.conf
```

#####Restart postgresql service:
```
$ sudo service postgresql restart
```

Check weather `simplevod_database.tar` is made:
```
$ cd /srv/simplevod/database
$ ls -al
```
Output should look like this:
```
total 132
drwxr-sr-x.  2 simplevod simplevod  4096 Apr 10 14:29 .
drwxrwsr-x. 13 simplevod simplevod  4096 Apr 10 14:44 ..
----------------- more ------------------------------------------------
-rw-r--r--.  1 simplevod simplevod     0 Apr 10 14:30 simplevod_database.tar
----------------- more ------------------------------------------------
```

### 2.2. Perform steps 1.1. 1.2. and 1.3 

### 2.3. Transfer tar file

#####Secure copy compressed database file from source to target (virtual) machine.

user@local-machine# ssh user1@source-machine<br>
user1@source-machine# scp /srv/simplevod/database/simplevod_database.tar user2@target-machine:/srv/simplevod/database<br>
user1@source-machine# logout

### 2.5. Restore SimpleVoD Database on the target machine

#####Copy postgresql initial configuration files to /var/lib/pgsql/data: 
```
$ sudo cp /srv/simplevod/database/init_pg_hba.conf /var/lib/pgsql/data/pg_hba.conf
```

#####Restart postgresql service:
```
$ sudo service postgresql restart
```

#####Throw away a possible already exiting database:
```
$ sudo -u postgres dropdb simplevod
```

#####Create a new databse:
```
$ sudo -i -u postgres createdb simplevod
```

#####Use PostgreSQL utility program pg_restore to fill the just created database with data from tar file:
Be sure the tar file with dumped-database resides in directory `/srv/simplevod/database`.
```
$ sudo pg_restore -U postgres --dbname=simplevod --verbose /srv/simplevod/database/simplevod_database.tar
```

### 2.6. Prepare Application without database creation
By the next script the following actions are performed:

#####A. Connect to the database through UNIX domain sockets.

#####B. Enable logging.

#####C. Install the Simplevod configuration-file with directives for Apache Basic Authentication.

```
$ cd /srv/simplevod
$ sudo sh ./pre-prepare-application.sh
```

### 2.7. Perform step 1.6 and 1.7



