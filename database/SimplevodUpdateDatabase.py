#!/usr/bin/env python
#==============================================================================>
# script title    : SimplevodUpdateDatabase.py
# description     : Loads data from json-source to postgreSQL-destination.
# author          : a.oldenburger
# date            : 09-12-2013
# version         : 0.1
# usage           : Script used with KPN/GHM Simplevod. 
# notes           :
# python_version  : @home v2.7.2
#==============================================================================>
import os
import sys
import getopt
import re 
import json 
import httplib
import urllib
import urllib2
import psycopg2
import time
import datetime
import pprint
import logging
import logging.handlers
import random

from os.path import basename

sys.path.append('/srv/simplevod/database')
sys.path.append('/srv/simplevod/pyld')

from xml.dom import minidom
from stat import S_ISREG, ST_CTIME, ST_MODE

from filelock import FileLock
from feed import Feed

CONFIG_CATEGORY_YES             = 'yes'
CONFIG_CATEGORY_NO              = 'no'

CONFIG_DJANGO_YES               = 'yes'
CONFIG_DJANGO_NO                = 'no'

CONFIG_SOURCE_JSON              = 'json'
CONFIG_SOURCE_JSON_ID           = 1
CONFIG_SOURCE_XML               = 'xml'
CONFIG_SOURCE_XML_ID            = 2
CONFIG_SOURCE_FILE              = 'file'
CONFIG_SOURCE_FILE_ID           = 3

SIMPLEVOD_NEW_CATEGORY          = 'Nieuw'
IDAT_RECENT_CATEGORY            = '#recent-category'

SIMPLEVOD_XML_EXT               = 'xml'
SIMPLEVOD_FIN_EXT               = '.done'

SIMPLEVOD_MPG_EXT               = 'mpg'
SIMPLEVOD_MPEG_EXT              = 'mpeg'
SIMPLEVOD_TS_EXT                = 'ts'

SIMPLEVOD_XML_TAG_MAIN          = 'movies'
SIMPLEVOD_XML_TAG_MOVIE         = 'movie'
SIMPLEVOD_XML_TAG_TITLE         = 'title'
SIMPLEVOD_XML_TAG_CATEGORY      = 'category'
SIMPLEVOD_XML_TAG_SUBCATEGORY   = 'subcategory'
SIMPLEVOD_XML_TAG_FILE          = 'file'
SIMPLEVOD_XML_TAG_VIDEOREF      = 'videoref'
SIMPLEVOD_XML_TAG_NEW           = 'new'
SIMPLEVOD_XML_VAL_YES           = 'yes'

CATEGORY_ID_AT                  = '#category-xxx'

TVOD_ID_AT                      = '#asset-000000'
TVOD_PRODUCT_CODE_START         = 'simplevod'
TVOD_PRODUCT_CODE_END           = 'a123456'
TVOD_END_USER_AMOUNT            = '0'
TVOD_END_USER_AMOUNT            = '0'
TVOD_AMOUNT                     = '0'
TVOD_SKIP_CONFIRM               = '1'
TVOD_EXPIRY_PERIOD              = '172800'
TVOD_STATUS                     = 'available'

SIMPLEVOD_DUMMY_ETAG            = '00000-000x-0x00000000x00'

#==============================================================================>
# function object : main
# parameters      : none
# return value    : none
# description     : 
#==============================================================================>
def main(path):
    #==============================================================================>
    # Install logging with RotatingFileHandler which is configured with 5 log files
    #==============================================================================>
    log = make_logger(path)

    #==============================================================================>
    # Read in records of table:feeds
    #==============================================================================>
    read_feeds(log)

#==============================================================================>
# function object : arguments
# parameters      : argv
# return value    : none
# description     : 
#==============================================================================>
def arguments(argv):
    path = ''

    try:
        opts, args = getopt.getopt(argv, 'p:h', ['path=', 'help'])    
    except getopt.GetoptError:
        print 'usage - SimplevodUpdateDatabase.py -p <path_to_logfile>'
        sys.exit(2)

    if not opts:
        print 'usage - SimplevodUpdateDatabase.py -p <path_to_logfile>'
        sys.exit(2)

    for opt, arg in opts:
        if opt == '-h':
            print 'usage - SimplevodUpdateDatabase.py -p <path_to_logfile>'
            sys.exit(2)
        elif opt in ('-p', '--params'):
            path = arg
        else:
            print 'usage - SimplevodUpdateDatabase.py -p <path_to_logfile>'
            sys.exit(2)

    return path

#==============================================================================>
# function object : make_logger
# parameters      : none
# return value    : none
# description     : 
#==============================================================================>
def make_logger(path):
    LOG_FILENAME = path + '/' + 'update_database.log'

    logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)
    handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=1024*1024*5, backupCount=5)

    log = logging.getLogger("SimplevodLogger")
    log.addHandler(handler)
    log.propagate = False

    return log
    
#==============================================================================>
# function object : read_feeds
# parameters      : none
# return value    : none
# description     : Read in simplevod json config and linked-data into postgreSQL.
#==============================================================================>
def read_feeds(log):

    feed_records = {}

    start = time.time()
    log_message_start = "Simplevod Data Updata - Starting: " + time.strftime("%Y-%m-%d %H:%M:%S")  

    record_data = dict()
    record_data["inserted_category"] = 0
    record_data["updated_category"] = 0
    record_data["inserted_tvod"] = 0
    record_data["updated_tvod"] = 0
    record_data["database_connections"] = 0
    record_data["max_category_order"] = 0
    record_data["max_tvod_order"] = 0
    record_data["max_category_old_order"] = 0
    record_data["max_tvod_old_order"] = 0

    record_data["ghm_count_categories"] = 0
    record_data["ghm_count_items"] = 0

    #==============================================================================>
    # Connect to database retrieve contents of table:feeds
    #print 'Connect to postgreSQL database:simplevod - read table:feed.'    
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #cursor.execute("SELECT * FROM public.simplevod_feed ORDER BY id ASC;")
        cursor.execute("SELECT * FROM public.simplevod_feed ORDER BY id DESC;")
        feed_records = cursor.fetchall()

        try:
            cursor.execute("SELECT MAX(\"order\") FROM public.simplevod_category")
            row = cursor.fetchone()            
            if row[0] is not None:
                max_category_order = int(row[0])
            else:
                max_category_order = 0
        except psycopg2.Error as e:
            max_category_order = 0

        record_data["max_category_order"] = max_category_order
        #==============================================================================>
        # Get nr. of rows from table:simplevod_category.
        #print 'Get nr. of rows from table:simplevod_category. nof %d' % record_data["max_category_order"]   
        #==============================================================================>

        try:
            cursor.execute("SELECT MAX(\"order\") FROM public.simplevod_tvod")
            row = cursor.fetchone()            
            if row[0] is not None:
                max_tvod_order = int(row[0])
            else:
                max_tvod_order = 0
        except psycopg2.Error as e:
            max_tvod_order = 0

        record_data["max_tvod_order"] = max_tvod_order
        #==============================================================================>
        # Get nr. of rows from table:simplevod_category.
        #print 'Get nr. of rows from table:simplevod_tvod. nof %d' % record_data["max_tvod_order"]   
        #==============================================================================>

        try:
            cursor.execute("SELECT MAX(oldorder) FROM public.simplevod_category")
            row = cursor.fetchone()            
            if row[0] is not None:
                max_category_old_order = int(row[0])
            else:
                max_category_old_order = 0
        except psycopg2.Error as e:
            max_category_old_order = 0

        record_data["max_category_old_order"] = max_category_old_order
        #==============================================================================>
        # Get nr. of rows from table:simplevod_category.
        #print 'Get nr. of rows from table:simplevod_category. nof %d' % record_data["max_category_old_order"]   
        #==============================================================================>

        try:
            cursor.execute("SELECT MAX(oldorder) FROM public.simplevod_tvod")
            row = cursor.fetchone()            
            if row[0] is not None:
                max_tvod_old_order = int(row[0])
            else:
                max_tvod_old_order = 0
        except psycopg2.Error as e:
            max_tvod_old_order = 0

        record_data["max_tvod_old_order"] = max_tvod_old_order
        #==============================================================================>
        # Get nr. of rows from table:simplevod_category.
        #print 'Get nr. of rows from table:simplevod_tvod. nof %d' % record_data["max_tvod_old_order"]   
        #==============================================================================>

        if conn:
            record_data['database_connections'] += 1
            conn.close()

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)

    #==============================================================================>
    # Loop through the records table:feeds
    #==============================================================================>
    record_data = traverse_feeds(log, feed_records, record_data)

    done = time.time()
    elapsed = done - start

    log_message = log_message_start + " - Ending: " + time.strftime("%Y-%m-%d %H:%M:%S") + \
        " - Duration: %s" % elapsed
    log.info(log_message)
    
    log_message = "table: category - inserted records %d -\t updated records %d" % \
        (record_data['inserted_category'],record_data['updated_category'])
    log.info(log_message)
    
    log_message = "table: tvod     - inserted records %d -\t updated records %d" % \
        (record_data['inserted_tvod'],record_data['updated_tvod'])
    log.info(log_message)
    log_message = "number of database connections was %d" % (record_data['database_connections'])
    log.info(log_message)
              
#==============================================================================>
# function object : traverse_feed
# parameters      : log, records, record_data
# return value    : 
# description     : 
#==============================================================================>
def traverse_feeds(log, records, record_data):

    for record in records:

        feed_config = {}
        feed_config["id"] = record[0]
        feed_config["name"] = record[1]
        feed_config["url"] = record[2]
        feed_config["path"] = record[3]
        feed_config["retrieve"] = record[4]
        feed_config["style"] = record[5]
        feed_config["title"] = record[6]
        feed_config["etag"] = record[7]

        feed_category = record[9]
        if feed_category != None:
            if feed_category:
                feed_config["category"] = CONFIG_CATEGORY_YES
            else:
                feed_config["category"] = CONFIG_CATEGORY_NO
        else:
            feed_config["category"] = 'undefined'

        feed_django = record[8]
        if feed_django != None:
            if feed_django:
                feed_config["django"] = CONFIG_DJANGO_YES
            else:
                feed_config["django"] = CONFIG_DJANGO_NO
        else:
            feed_config["django"] = 'undefined'

        feed_retrieve = feed_config["retrieve"]
        if feed_retrieve == CONFIG_SOURCE_JSON_ID:
            feed_config_django = feed_config["django"]
            if feed_config_django == CONFIG_DJANGO_NO:
                record_data = ghm_update_json_data(log, feed_config, record_data)

            elif feed_config_django == CONFIG_DJANGO_YES:
                record_data = django_update_json_data(log, feed_config, record_data)

        elif feed_retrieve == CONFIG_SOURCE_XML_ID:
            record_data = update_xml_data(log, feed_config, record_data)

        elif feed_retrieve == CONFIG_SOURCE_FILE_ID:
            record_data = update_file_data(log, feed_config, record_data)

    return record_data

#+--------------------------------------------------------------------------------+
#+ ##### BEGIN OF CODE HANDLING SIMPLEVOD DATABASE UPDATING THE OLD WAY ###########
#+--------------------------------------------------------------------------------+
  
#==============================================================================>
# function object : ghm_update_json_data
# parameters      : log, feed_config, record_data
# return value    : 
# description     : 
#==============================================================================>
def ghm_update_json_data(log, feed_config, record_data):
    path = feed_config["url"]
        
    match = validate_jsonld_url(path)
    if not match:
        log_message =  '!!! PLEASE TAKE NOTICE: URL %s - source of XML data files - does not exist.' % path
        log.info(log_message)
        return record_data

    #==============================================================================>
    # Make instance of class Feed and load/parse associated json-linked-data.
    #==============================================================================>
    try:
        feed = instantiate_class_feed(log, feed_config)

        if len(feed.categories) == 0:
            log_message =  'No update - No categories !' 
            log.info(log_message)
            return record_data

    except Exception, exc:
        log.exception(exc)
        sys.exit(1)

    #==============================================================================>
    # Compare etags from database and new feed object.
    #==============================================================================>
    previous_etag = feed_config["etag"] 
    previous_etag = previous_etag.strip() 
    next_etag = feed.etag
    next_etag = next_etag.strip() 

    #==============================================================================>
    #print 'Compare etags - database:%s, json:%s' % (previous_etag, next_etag)    
    #==============================================================================>
    if previous_etag != next_etag: 
        update_etag(log, next_etag, feed_config["id"])

    #==============================================================================>
    # Loop through the json dictionary:category
    #==============================================================================>
    record_data = ghm_traverse_categories(log, feed.categories, feed_config["id"], feed_config["django"], feed.title, record_data)

    #==============================================================================>
    # Reconcile records in table:simplevod_new with those in table:simplevod_category.
    #print 'Reconcile records in table:simplevod_new with those in table:simplevod_category.'    
    #==============================================================================>
    ghm_reconcile_new_items(record_data)

    if feed:
        del feed
    return record_data

#==============================================================================>
# function object : ghm_traverse_categories
# parameters      : log, categories, feed_id, feed_django, feed_title, record_data
# return value    : 
# description     : 
#==============================================================================>
def ghm_traverse_categories(log, categories, feed_id, feed_django, feed_title, record_data):

    max_category_order = record_data["max_category_order"]
    max_category_old_order = record_data["max_category_old_order"] 
    ghm_count_categories = record_data["ghm_count_categories"] 

    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # Set is_new flag to false for this feed's categories.
        #==============================================================================>
        cursor.execute("UPDATE public.simplevod_category SET is_new = 'false' WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': feed_id } )

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    record_data['updated_category'] += 1

    for category in categories:
        if len(category['items']) == 0:
            continue

        ghm_count_categories += 1
    
        category_atid = category["@id"]

        category_title = category["title"]
        category_title = category_title.strip()

        category_items = category["items"]
        
        category_items_len = len(category_items)
        
        category_row = None

        if category_title.lower() == SIMPLEVOD_NEW_CATEGORY.lower():
            is_new_category = True
        else:
            is_new_category = False

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM public.simplevod_category WHERE idat=%(idat)s AND fk_feed_id=%(fk_feed_id)s", { 'idat': category_atid, 'fk_feed_id': feed_id } )
            category_row = cursor.fetchone()

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        if category_row != None:
            category_id = category_row[0]
        else:
            category_id = 0

        if category_row == None:
        
            if not(is_new_category):
                max_category_order += 1
                oldorder_category = ghm_count_categories
  
                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    #==============================================================================>
                    # Insert record into table:simplevod_category.
                    #print 'Insert record into table:simplevod_category. order nr. %d' % max_category_order   
                    #==============================================================================>
                    query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, false, true) RETURNING id;"
                    cursor.execute(query, (max_category_order, oldorder_category, category_atid, category["title"], feed_id))
                    
                    record_data['inserted_category'] += 1
                    category_id = cursor.fetchone()[0]

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

            else:
                category_id = 0
        else:
            if not(is_new_category):

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    #==============================================================================>
                    # Set active flag to false for category.
                    #print 'Set active flag to false for this category. id nr. %d' % category_id     
                    #==============================================================================>
                    cursor.execute("UPDATE public.simplevod_category SET active='false' WHERE id=%(id)s", {'id': category_id } )
                    record_data['updated_category'] += 1

                    #==============================================================================>
                    # Set active flag to false for this category and its items.
                    #print 'Set active flag to false for this categories items. id nr. %d' % category_id         
                    #==============================================================================>
                    #cursor.execute("UPDATE public.simplevod_tvod SET active = 'false' WHERE fk_category_id=%(fk_category_id)s", {'fk_category_id': category_id } )
                    cursor.execute("UPDATE public.simplevod_tvod SET is_new = 'false' , active='false' WHERE fk_category_id=%(fk_category_id)s", {'fk_category_id': category_id } )

                    record_data['updated_category'] += 1

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

        #==============================================================================>
        # For categories with one or more items.
        # Loop through the json dictionary:items
        # Raise active flag 
        #==============================================================================>
        if category_items_len != 0:
            record_data = ghm_traverse_items(log, category_items, feed_id, category_id, category_items_len, feed_title, is_new_category, record_data)

            oldorder_category = ghm_count_categories

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                #==============================================================================>
                # Update ordering and title for category.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_category SET oldorder=%(oldorder)s, title=%(title)s WHERE id=%(id)s", {'oldorder': oldorder_category, 'title': category["title"], 'id': category_id } )
                if not(is_new_category):
                    #==============================================================================>
                    # Set active flag to true for category.
                    #print 'Set active flag to true for this category. id nr. %d' % category_id     
                    #==============================================================================>
                    cursor.execute("UPDATE public.simplevod_category SET active='true' WHERE id=%(id)s", {'id': category_id } )
                    record_data['updated_category'] += 1
                else:
                    #==============================================================================>
                    # Set active flag and is_new to true for category.
                    #print 'Set active flag and is_new to true for this category. id nr. %d' % category_id     
                    #==============================================================================>
                    cursor.execute("UPDATE public.simplevod_category SET is_new = 'true', active='true' WHERE id=%(id)s", {'id': category_id } )
                    record_data['updated_category'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

    record_data["max_category_order"] = max_category_order
    record_data["max_category_old_order"] = max_category_old_order
    record_data["ghm_count_categories"] = ghm_count_categories
    return record_data

#==============================================================================>
# function object : ghm_traverse_items
# parameters      : log, category_items, feed_id, category_id, category_items_len, feed_title, is_new_category, record_data
# return value    : 
# description     : 
#==============================================================================>
def ghm_traverse_items(log, category_items, feed_id, category_id, category_items_len, feed_title, is_new_category, record_data):

    max_tvod_order = record_data["max_tvod_order"]
    max_tvod_old_order = record_data["max_tvod_old_order"] 
    ghm_count_items = record_data["ghm_count_items"] 
    
    items_to_be_inserted = []

    for category_item in category_items:

        if not(is_new_category):
            ghm_count_items += 1

        category_item_atid = category_item["@id"]

        videoref_value = category_item["video"]["videoref"]
        title_value = category_item["title"]
        productcode_value = category_item["productcode"]
        status_value = "available"
        productdescription_value = feed_title + ": " + title_value

        item_tvod_row = None

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            #==============================================================================>
            # Check vod based on productcode.
            #==============================================================================>
            cursor.execute("SELECT id FROM public.simplevod_tvod WHERE productcode=%(productcode)s AND fk_category_id=%(fk_category_id)s", {'productcode': category_item["productcode"], 'fk_category_id': category_id } )

            item_tvod_row = cursor.fetchone()

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        if item_tvod_row == None:
            if not(is_new_category):
                items_to_be_inserted.append(category_item)
                continue

            else:
                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    feed_django = 'false'

                    #==============================================================================>
                    # Temporarily insert record into table:simplevod_new with videoref, title, productcode, 
                    # enduseramount, amount, skipconfirm, expiry_period, status and foreign-keys from 
                    # table:simplevod_feed, simplevod_category, simplevod_item.
                    #==============================================================================>
                    query = "INSERT INTO public.simplevod_new(idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_django, is_new, active)" + \
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
                    cursor.execute(query, (category_item_atid, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, category_id, feed_id, feed_django))

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

        else:
            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                tvod_id = item_tvod_row[0]

                tvod_oldorder = ghm_count_items    

                #==============================================================================>
                # Update field oldorder in record in table:simplevod_tvod.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET oldorder=%(oldorder)s  WHERE id=%(id)s", {'oldorder': tvod_oldorder, 'id': tvod_id } )

                #==============================================================================>
                # Update field title in record in table:simplevod_tvod.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET title=%(title)s  WHERE id=%(id)s", {'title': title_value, 'id': tvod_id } )

                #==============================================================================>
                # Update field productdescription in record in table:simplevod_tvod.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET productdescription=%(productdescription)s  WHERE id=%(id)s", {'productdescription': productdescription_value, 'id': tvod_id } )

                #==============================================================================>
                # Update record in table:simplevod_tvod.
                #print 'Update record into table:simplevod_tvod. id nr. %d' % tvod_id     
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET active='true' WHERE id=%(id)s", {'id': tvod_id } )
                record_data['updated_tvod'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

    record_data["max_tvod_order"] = max_tvod_order
    record_data["max_tvod_old_order"] = max_tvod_old_order
    record_data["ghm_count_items"] = ghm_count_items
 
    record_data = ghm_insert_items(log, items_to_be_inserted, feed_id, category_id, feed_title, is_new_category, record_data)

    return record_data

#==============================================================================>
# function object : ghm_insert_items
# parameters      : log, items_to_be_inserted, feed_id, category_id, feed_title, is_new_category, record_data
# return value    : 
# description     : 
#==============================================================================>
def ghm_insert_items(log, items_to_be_inserted, feed_id, category_id, feed_title, is_new_category, record_data):

    max_tvod_order = record_data["max_tvod_order"]
    max_tvod_old_order = record_data["max_tvod_old_order"] 
    ghm_count_items = record_data["ghm_count_items"] 

    for category_item in items_to_be_inserted[::-1]:

        ghm_count_items += 1

        category_item_atid = category_item["@id"]

        videoref_value = category_item["video"]["videoref"]
        title_value = category_item["title"]
        productcode_value = category_item["productcode"]
        status_value = "available"
        productdescription_value = feed_title + ": " + title_value

        #==============================================================================>
        # New records are place at the beginning of the ordering.
        # To make this possible add one to order field of existing records.
        #==============================================================================>

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("ALTER TABLE simplevod_tvod DROP CONSTRAINT simplevod_tvod_order_key;")

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            #sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("UPDATE simplevod_tvod SET \"order\" = \"order\" + 1;")
            cursor.execute("UPDATE simplevod_tvod SET oldorder = oldorder + 1 WHERE oldorder != 0;")

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("ALTER TABLE simplevod_tvod ADD CONSTRAINT simplevod_tvod_order_key UNIQUE (\"order\");")

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            latest_tvod_order = 1

            #==============================================================================>
            # Insert record into table:simplevod_tvod.
            #print 'Insert record into table:simplevod_tvod.order nr. %d' % max_tvod_order    
            #==============================================================================>
            query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"
            cursor.execute(query, (latest_tvod_order, latest_tvod_order, category_item_atid, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, category_id, feed_id))

            record_data['inserted_tvod'] += 1

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

    record_data["max_tvod_order"] = max_tvod_order
    record_data["max_tvod_old_order"] = max_tvod_old_order
    record_data["ghm_count_items"] = ghm_count_items
    return record_data

#==============================================================================>
# function object : ghm_reconcile_new_items
# parameters      : record_data
# return value    : 
# description     : 
#==============================================================================>
def ghm_reconcile_new_items(record_data):

    max_tvod_order = record_data["max_tvod_order"]
    max_tvod_old_order = record_data["max_tvod_old_order"]

    rows = []
    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM public.simplevod_new ORDER BY id DESC;")
        #cursor.execute("SELECT * FROM public.simplevod_new ORDER BY idat DESC;")
        
        rows = cursor.fetchall()

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    for row in rows:
        idat_value = row[1]
        videoref_value = row[2]
        title_value = row[3]
        productcode_value = row[4]
        status_value = row[9]
        productdescription_value = row[10]
        simplevod_feed_id = row[11]
        simplevod_category_id = row[12]
        empty_category_id = None

        tvod_row = None

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            #==============================================================================>
            # Update record in table:simplevod_category.
            #print 'Update record into table:simplevod_category. id nr. %d' % simplevod_category_id    
            #==============================================================================>
            cursor.execute("UPDATE public.simplevod_category SET is_new='true' WHERE id=%(id)s", {'id': simplevod_category_id } )
            record_data['updated_category'] += 1

            #==============================================================================>
            # Check vod based on id.
            #==============================================================================>
            cursor.execute("SELECT id FROM public.simplevod_tvod WHERE idat=%(idat)s AND fk_feed_id=%(fk_feed_id)s", {'idat': idat_value, 'fk_feed_id': simplevod_feed_id } )
            
            tvod_row = cursor.fetchone()

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1
        
        if tvod_row != None:

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                tvod_id = tvod_row[0] 

                #==============================================================================>
                # Update field oldorder in record in table:simplevod_tvod.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET title=%(title)s  WHERE id=%(id)s", {'title': title_value, 'id': tvod_id } )

                #==============================================================================>
                # Update field oldorder in record in table:simplevod_tvod.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET productdescription=%(productdescription)s  WHERE id=%(id)s", {'productdescription': productdescription_value, 'id': tvod_id } )

                #==============================================================================>
                # Update field oldorder in record in table:simplevod_tvod.
                #==============================================================================>
                #cursor.execute("UPDATE public.simplevod_tvod SET fk_category_id=%(category_id)s  WHERE id=%(id)s", {'category_id': simplevod_category_id, 'id': tvod_id } )

                #==============================================================================>
                # Update record in table:simplevod_tvod.
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_tvod SET is_new='true' WHERE id=%(id)s", {'id': tvod_id } )
                record_data['updated_tvod'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

        else:
            #==============================================================================>
            # New records are place at the beginning of the ordering.
            # To make this possible add one to order field of existing records.
            #==============================================================================>

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                cursor.execute("ALTER TABLE simplevod_tvod DROP CONSTRAINT simplevod_tvod_order_key;")

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                #sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                cursor.execute("UPDATE simplevod_tvod SET \"order\" = \"order\" + 1;")
                cursor.execute("UPDATE simplevod_tvod SET oldorder = oldorder + 1 WHERE oldorder != 0;")

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                cursor.execute("ALTER TABLE simplevod_tvod ADD CONSTRAINT simplevod_tvod_order_key UNIQUE (\"order\");")

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                #==============================================================================>
                # Insert record into table:simplevod_tvod with title and foreign-key 
                # from table:simplevod_tvod.
                #==============================================================================>
                latest_tvod_order = 1

                query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
                cursor.execute(query, (latest_tvod_order, latest_tvod_order, idat_value, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, empty_category_id, simplevod_feed_id))

                record_data['inserted_tvod'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # TRUNCATE and reset the SERIAL counter (also automatically truncate all tables 
        # that have foreign-key references ).
        #print 'truncate database:simplevod table:simplevod_new'    
        #==============================================================================>
        cursor.execute("TRUNCATE public.simplevod_new RESTART IDENTITY CASCADE;")

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    record_data["max_tvod_order"] = max_tvod_order
    record_data["max_tvod_old_order"] = max_tvod_old_order
    return record_data

#+--------------------------------------------------------------------------------+
#+ ##### END OF CODE HANDLING SIMPLEVOD DATABASE UPDATING THE OLD WAY #############
#+--------------------------------------------------------------------------------+

#+--------------------------------------------------------------------------------+
#+ ##### BEGIN OF CODE HANDLING SIMPLEVOD DATABASE UPDATING THE NEW WAY ###########
#+--------------------------------------------------------------------------------+

#==============================================================================>
# function object : django_update_json_data
# parameters      : log, feed_config, record_data
# return value    : 
# description     : 
#==============================================================================>
def django_update_json_data(log, feed_config, record_data):
    path = feed_config["url"]
        
    match = validate_jsonld_url(path)
    if not match:
        log_message =  '!!! PLEASE TAKE NOTICE: URL %s - source of XML data files - does not exist.' % path
        log.info(log_message)
        return record_data

    #==============================================================================>
    # Make instance of class Feed and load/parse associated json-linked-data.
    #==============================================================================>
    try:
        feed = instantiate_class_feed(log, feed_config)
        if len(feed.categories) == 0:
            log_message =  'No update - No categories !' 
            log.info(log_message)
            return record_data

    except Exception, exc:
        log.exception(exc)
        sys.exit(1)

    #==============================================================================>
    # Compare etags from database and new feed object.
    #==============================================================================>
    previous_etag = feed_config["etag"] 
    previous_etag = previous_etag.strip() 
    next_etag = feed.etag
    next_etag = next_etag.strip() 

    #==============================================================================>
    #print 'Compare etags - database:%s, json:%s' % (previous_etag, next_etag)    
    #==============================================================================>
    if previous_etag != next_etag: 
        update_etag(log, next_etag, feed_config["id"])

    #==============================================================================>
    # Loop through the json dictionary:category
    #==============================================================================>
    record_data = django_traverse_categories(log, feed.categories, feed_config["id"], feed_config["django"], feed.title, record_data)

    #==============================================================================>
    # Reconcile records in table:simplevod_new with those in table:simplevod_category.
    #print 'Reconcile records in table:simplevod_new with those in table:simplevod_category.'    
    #==============================================================================>
    django_reconcile_new_items(record_data)

    if feed:
        del feed
    return record_data

#==============================================================================>
# function object : django_traverse_categories
# parameters      : log, categories, feed_id, feed_django, feed_title, record_data
# return value    : 
# description     : 
#==============================================================================>
def django_traverse_categories(log, categories, feed_id, feed_django, feed_title, record_data):

    max_category_order = record_data["max_category_order"]

    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # Set is_new flag to false for this feed's categories.
        #==============================================================================>
        cursor.execute("UPDATE public.simplevod_category SET is_new = 'false' WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': feed_id } )

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    record_data['updated_category'] += 1

    for category in categories:
        if len(category['items']) == 0:
            continue
    
        category_atid = category["@id"]

        category_title = category["title"]
        category_title = category_title.strip()

        category_items = category["items"]
        category_items_len = len(category_items)

        category_row = None

        if category_title.lower() == SIMPLEVOD_NEW_CATEGORY.lower():
            is_new_category = True
        else:
            is_new_category = False

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("SELECT id FROM public.simplevod_category WHERE idat=%(idat)s AND fk_feed_id=%(fk_feed_id)s", { 'idat': category_atid, 'fk_feed_id': feed_id } )
            category_row = cursor.fetchone()

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        if category_row != None:
            category_id = category_row[0]
        else:
            category_id = 0

        if category_row is None:
        
            if not(is_new_category):
                max_category_order += 1
                oldorder_category = 0

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    #==============================================================================>
                    # Insert record into table:simplevod_category.
                    #print 'Insert record into table:simplevod_category. order nr. %d' % max_category_order   
                    #==============================================================================>
                    query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, false, true) RETURNING id;"
                    cursor.execute(query, (max_category_order, oldorder_category, category_atid, category["title"], feed_id))
                    
                    record_data['inserted_category'] += 1
                    category_id = cursor.fetchone()[0]

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

            else:
                category_id = 0
        else:
            if not(is_new_category):

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    #==============================================================================>
                    # Set active flag to false for category.
                    #print 'Set active flag to false for this category. id nr. %d' % category_id     
                    #==============================================================================>
                    cursor.execute("UPDATE public.simplevod_category SET active='false' WHERE id=%(id)s", {'id': category_id } )
                    record_data['updated_category'] += 1

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

        #==============================================================================>
        # For categories with one or more items.
        # Loop through the json dictionary:items
        # Raise active flag 
        #==============================================================================>
        if category_items_len != 0:
            record_data = django_traverse_items(log, category_items, feed_id, category_id, category_items_len, feed_title, is_new_category, record_data)

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()
                
                if not(is_new_category):
                    #==============================================================================>
                    # Set active flag to true for category.
                    #print 'Set active flag to true for this category. id nr. %d' % category_id     
                    #==============================================================================>
                    cursor.execute("UPDATE public.simplevod_category SET active='true' WHERE id=%(id)s", {'id': category_id } )
                    record_data['updated_category'] += 1
                else:
                    #==============================================================================>
                    # Set active flag and is_new to true for category.
                    #print 'Set active flag and is_new to true for this category. id nr. %d' % category_id     
                    #==============================================================================>
                    cursor.execute("UPDATE public.simplevod_category SET is_new = 'true' , active='true' WHERE id=%(id)s", {'id': category_id } )
                    record_data['updated_category'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

    record_data["max_category_order"] = max_category_order
    return record_data

#==============================================================================>
# function object : django_traverse_items
# parameters      : log, category_items, feed_id, category_id, category_items_len, feed_title, is_new_category, record_data
# return value    : 
# description     : 
#==============================================================================>
def django_traverse_items(log, category_items, feed_id, category_id, category_items_len, feed_title, is_new_category, record_data):

    max_tvod_order = record_data["max_tvod_order"]

    for category_item in category_items:

        category_item_atid = category_item["@id"]

        videoref_value = category_item["video"]["videoref"]
        title_value = category_item["title"]
        productcode_value = category_item["productcode"]
        status_value = "available"
        productdescription_value = feed_title + ": " + title_value

        item_tvod_row = None

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            #==============================================================================>
            # Check vod based on productcode.
            #==============================================================================>
            #cursor.execute("SELECT * FROM public.simplevod_tvod WHERE productcode=%(productcode)s AND fk_category_id=%(fk_category_id)s", {'productcode': category_item["productcode"], 'fk_category_id': category_id } )
            cursor.execute("SELECT * FROM public.simplevod_tvod WHERE productcode=%(productcode)s", {'productcode': category_item["productcode"] } )

            item_tvod_row = cursor.fetchone()

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        if item_tvod_row is None:
            if not(is_new_category):
                #==============================================================================>
                # New records are place at the beginning of the ordering.
                # To make this possible add one to order field of existing records.
                #==============================================================================>

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    cursor.execute("ALTER TABLE simplevod_tvod DROP CONSTRAINT simplevod_tvod_order_key;")

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    #sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    cursor.execute("UPDATE simplevod_tvod SET \"order\" = \"order\" + 1;")

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    cursor.execute("ALTER TABLE simplevod_tvod ADD CONSTRAINT simplevod_tvod_order_key UNIQUE (\"order\");")

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    latest_tvod_order = 1
                    oldorder_tvod = 0

                    #==============================================================================>
                    # Insert record into table:simplevod_tvod.
                    #print 'Insert record into table:simplevod_tvod.order nr. %d' % max_tvod_order    
                    #==============================================================================>
                    query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"
                    cursor.execute(query, (latest_tvod_order, oldorder_tvod, category_item_atid, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, category_id, feed_id))

                    record_data['inserted_tvod'] += 1

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

            else:
                #==============================================================================>
                # Renew connection to database - Start a new Transaction.
                #==============================================================================>
                try:
                    conn = None
                    conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                    cursor = conn.cursor()

                    feed_django = 'true'

                    #==============================================================================>
                    # Temporarily insert record into table:simplevod_new with videoref, title, productcode, 
                    # enduseramount, amount, skipconfirm, expiry_period, status and foreign-keys from 
                    # table:simplevod_feed, simplevod_category, simplevod_item.
                    #==============================================================================>
                    query = "INSERT INTO public.simplevod_new(idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_django, is_new, active)" + \
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
                    cursor.execute(query, (category_item_atid, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, category_id, feed_id, feed_django))

                except psycopg2.DatabaseError, e:
                    log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                    log.exception(log_message)
                    sys.exit(1)
                    
                finally:
                    if conn:
                        #==============================================================================>
                        # Commit Transaction & Close Connection
                        #==============================================================================>
                        conn.commit()
                        conn.close()
                        record_data['database_connections'] += 1

        else:
            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                tvod_id = item_tvod_row[0]
                tvod_active = item_tvod_row[15]
                
                #==============================================================================>
                # Update record in table:simplevod_tvod.
                #print 'Update record into table:simplevod_tvod. id nr. %d' % tvod_id     
                #==============================================================================>
                if tvod_active:
                    cursor.execute("UPDATE public.simplevod_tvod SET active='true' WHERE id=%(id)s", {'id': tvod_id } )
                else:
                    cursor.execute("UPDATE public.simplevod_tvod SET active='false' WHERE id=%(id)s", {'id': tvod_id } )
                
                record_data['updated_tvod'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

    record_data["max_tvod_order"] = max_tvod_order
    return record_data

#==============================================================================>
# function object : django_reconcile_new_items
# parameters      : record_data
# return value    : 
# description     : 
#==============================================================================>
def django_reconcile_new_items(record_data):

    max_tvod_order = record_data["max_tvod_order"]

    rows = []
    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM public.simplevod_new ORDER BY id DESC;")
        rows = cursor.fetchall()

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    for row in rows:
        idat_value = row[1]
        videoref_value = row[2]
        title_value = row[3]
        productcode_value = row[4]
        status_value = row[9]
        productdescription_value = row[10]
        simplevod_feed_id = row[11]
        simplevod_category_id = row[12]
        empty_category_id = None

        tvod_row = None

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            #==============================================================================>
            # Update record in table:simplevod_category.
            #print 'Update record into table:simplevod_category. id nr. %d' % simplevod_category_id    
            #==============================================================================>
            cursor.execute("UPDATE public.simplevod_category SET is_new='true' WHERE id=%(id)s", {'id': simplevod_category_id } )
            record_data['updated_category'] += 1

            #==============================================================================>
            # Check vod based on id.
            #==============================================================================>
            cursor.execute("SELECT id FROM public.simplevod_tvod WHERE idat=%(idat)s AND fk_feed_id=%(fk_feed_id)s", {'idat': idat_value, 'fk_feed_id': simplevod_feed_id } )
            
            tvod_row = cursor.fetchone()

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1
        
        if tvod_row is None:
            #==============================================================================>
            # New records are place at the beginning of the ordering.
            # To make this possible add one to order field of existing records.
            #==============================================================================>

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                cursor.execute("ALTER TABLE simplevod_tvod DROP CONSTRAINT simplevod_tvod_order_key;")

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                #sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                cursor.execute("UPDATE simplevod_tvod SET \"order\" = \"order\" + 1;")

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                cursor.execute("ALTER TABLE simplevod_tvod ADD CONSTRAINT simplevod_tvod_order_key UNIQUE (\"order\");")

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

            #==============================================================================>
            # Renew connection to database - Start a new Transaction.
            #==============================================================================>
            try:
                conn = None
                conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
                cursor = conn.cursor()

                #==============================================================================>
                # Insert record into table:simplevod_tvod with title and foreign-key 
                # from table:simplevod_tvod.
                #==============================================================================>
                latest_tvod_order = 1
                oldorder_tvod = 0

                query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
                cursor.execute(query, (latest_tvod_order, oldorder_tvod, idat_value, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, empty_category_id, simplevod_feed_id))

                record_data['inserted_tvod'] += 1

            except psycopg2.DatabaseError, e:
                log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
                log.exception(log_message)
                sys.exit(1)
                
            finally:
                if conn:
                    #==============================================================================>
                    # Commit Transaction & Close Connection
                    #==============================================================================>
                    conn.commit()
                    conn.close()
                    record_data['database_connections'] += 1

    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # TRUNCATE and reset the SERIAL counter (also automatically truncate all tables 
        # that have foreign-key references ).
        #print 'truncate database:simplevod table:simplevod_new'    
        #==============================================================================>
        cursor.execute("TRUNCATE public.simplevod_new RESTART IDENTITY CASCADE;")

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    record_data["max_tvod_order"] = max_tvod_order
    return record_data

#+--------------------------------------------------------------------------------+
#+ ##### END OF CODE HANDLING SIMPLEVOD DATABASE UPDATING THE NEW WAY #############
#+--------------------------------------------------------------------------------+

#==============================================================================>
# function object : validate_jsonld_url
# parameters      : url
# return value    : 
# description     : 
#==============================================================================>
def validate_jsonld_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
        r'localhost|' #localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    return regex.match(url)
            
#==============================================================================>
# function object : update_etag
# parameters      : log, new_etag, feed_id
# return value    : 
# description     : 
#==============================================================================>
def update_etag(log, new_etag, feed_id):

    #==============================================================================>
    # Ommit etag-checking because it does not work well.
    #==============================================================================>
    feed_etag = SIMPLEVOD_DUMMY_ETAG

    #==============================================================================>
    # Renew connection to database.
    #print 'Connect to postgreSQL database:simplevod - update table:feed.'    
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # Update etag for this feed.
        #print 'Update etag for this feed.'    
        #==============================================================================>
        cursor.execute("UPDATE public.simplevod_feed SET retrieve='1', etag=%(etag)s WHERE id=%(id)s", {'etag': feed_etag, 'id': feed_id } )

        #==============================================================================>
        # Commit Transaction & Close Connection
        #==============================================================================>
        if conn:
            conn.commit()
            conn.close()

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)

#==============================================================================>
# function object : instantiate_class_feed
# parameters      : log, feed_config
# return value    : 
# description     : 
#==============================================================================>
def instantiate_class_feed(log, feed_config):
    try:
		return Feed(feed_config)
        
    except Exception as e:
        log_message = "Cannot instantiate Feed object for feed '{0}' [{1}]".format(feed_config["name"],str(e))
        log.exception(log_message)
        sys.exit(1)

#==============================================================================>
# function object : update_xml_data
# parameters      : log, feed_config, record_data
# return value    : 
# description     : 
#==============================================================================>
def update_xml_data(log, feed_config, record_data):
        
    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #print 'Connect to postgreSQL database:simplevod - read/update table:category.'    
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 

        record_data = load_xml_data(log, conn, feed_config, record_data)

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        conn.commit()

        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    return record_data

#==============================================================================>
# function object : load_xml_data
# parameters      : con, feed_config, record_data 
# return value    : 
# description     : 
#==============================================================================>
def load_xml_data(log, con, feed_config, record_data):
    cursor = con.cursor()

    try:
        feed_id = feed_config["id"]
        feed_name = feed_config["name"]
        path = feed_config["path"]
        style = feed_config["style"]
        feed_title = feed_config["title"]

        if not os.path.exists(path):
            log_message =  '!!! PLEASE TAKE NOTICE: directory %s - source of XML data files - does not exist.' % path
            log.info(log_message)
            return record_data

        list_of_xml_files = find_xml_files_in_dir(path)
        if len(list_of_xml_files) != 0:
            xml_file = list_of_xml_files[0]
            file_name = os.path.join(path, xml_file)
        else:
            return record_data

        feed_django = 'false'
        old_order = True
        if feed_config.has_key("django"):
            feed_config_django = feed_config["django"]
            feed_config_django = feed_config_django.lower()
            
            if feed_config_django == CONFIG_DJANGO_NO:
                feed_django = 'false'
                old_order = True
            elif feed_config_django == CONFIG_DJANGO_YES:
                feed_django = 'true'
                old_order = False

        feed_category = 'false'
        flat_menu = False

        if feed_config.has_key("category"):
            feed_config_category = feed_config["category"]
            feed_config_category = feed_config_category.lower()
            
            if feed_config_category == CONFIG_CATEGORY_YES:
                feed_category = 'true'
                flat_menu = False
            elif feed_config_category == CONFIG_CATEGORY_NO:
                feed_category = 'false'
                flat_menu = True

        max_category_order = record_data["max_category_order"]
        max_category_old_order = record_data["max_category_old_order"]
        max_tvod_order = record_data["max_tvod_order"]
        max_tvod_old_order = record_data["max_tvod_old_order"]
        
        try:
            xmldoc = minidom.parse(file_name)
        except:
            log_message =  '!!! PLEASE TAKE NOTICE: could not retrieve XML from file %s.' % file_name
            log.info(log_message)
            return record_data
        
        #==============================================================================>
        # Delete all records from table:simplevod_category with this feed.
        #print 'Delete all records from table:simplevod_category with this feed. id nr. %d' % feed_id     
        #==============================================================================>
        cursor.execute("DELETE FROM public.simplevod_category WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': feed_id } )

        #==============================================================================>
        # Delete all records from table:simplevod_category with this feed.
        #print 'Delete all records from table:simplevod_category with this feed. id nr. %d' % feed_id     
        #==============================================================================>
        cursor.execute("DELETE FROM public.simplevod_tvod WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': feed_id } )

        max_category_order += 1
        if old_order:
            max_category_old_order += 1
            oldorder_category = max_category_old_order
        else:
            oldorder_category = 0

        #==============================================================================>
        # Generate random asset-number (with default seed based on system-time).
        #==============================================================================>
        tvod_product_code_end = random.randrange(1,999998+1)
        #==============================================================================>
        #print 'Random with system seed. %d' % tvod_product_code_end     
        #==============================================================================>

        if not flat_menu:
            #==============================================================================>
            # Insert record into table:simplevod_category with title and foreign-key 
            # from table:simplevod_feed.
            # Standard new category with is_new flag set to True and active flag set to False.
            #==============================================================================>
            query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, true, false) RETURNING id;"
            cursor.execute(query, (max_category_order, oldorder_category, IDAT_RECENT_CATEGORY, SIMPLEVOD_NEW_CATEGORY, feed_id))

            record_data['inserted_category'] += 1

            new_category_id = cursor.fetchone()[0]
        else:
            new_category_id = 0

        movieset = xmldoc.getElementsByTagName(SIMPLEVOD_XML_TAG_MAIN)[0]                  
        movie_categories = dict()
        movies = movieset.getElementsByTagName(SIMPLEVOD_XML_TAG_MOVIE)     

        has_new_category = False
        for movie in movies:
        
            if not flat_menu:
                category = get_first_node_val(movie, SIMPLEVOD_XML_TAG_CATEGORY)
                movie_categories[category] = 0

            if not flat_menu:
                is_yes = get_first_node_val(movie, SIMPLEVOD_XML_TAG_NEW)
                if is_yes == SIMPLEVOD_XML_VAL_YES:
                    has_new_category = True

        if has_new_category:
            #==============================================================================>
            # Update record in table:simplevod_category.
            #==============================================================================>
            #print 'Update standard record with - category new - in table:simplevod_category'    
            cursor.execute("UPDATE public.simplevod_category SET active='true' WHERE id=%(id)s", {'id': new_category_id } )
            record_data['updated_category'] += 1

        if not flat_menu:
            category_title = 'Dummy Category'
        else:
            category_title = 'No Category'

        for key in movie_categories:
            #==============================================================================>
            # Insert record into table:simplevod_category with title and foreign-key 
            # from table:simplevod_feed.
            #==============================================================================>
            #print 'Insert record into table:simplevod_category'   
            category_title = key

            max_category_order += 1
            if old_order:
                max_category_old_order += 1
                oldorder_category = max_category_old_order
            else:
                oldorder_category = 0
             
            query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, false, true) RETURNING id;"
            cursor.execute(query, (max_category_order, oldorder_category, CATEGORY_ID_AT, category_title, feed_id))

            record_data['inserted_category'] += 1

            simplevod_category_id = cursor.fetchone()[0]
            movie_categories[key] = simplevod_category_id

        for movie in movies:

            category_id = None
            if not flat_menu:
                category = get_first_node_val(movie, SIMPLEVOD_XML_TAG_CATEGORY)
                #print 'category = %s' % category   
                if category in movie_categories.keys():
                    category_id = movie_categories[category]
                else:                    
                    log_message = "category %s does not exist within movie_categories dictionary" % category
                    log.info(log_message)
                    continue

            title = get_first_node_val(movie, SIMPLEVOD_XML_TAG_TITLE)
            #print 'title = %s' % title   
            vod = get_first_node_val(movie, SIMPLEVOD_XML_TAG_FILE)
            #print 'vod = %s' % vod   
            videoref = get_first_node_val(movie, SIMPLEVOD_XML_TAG_VIDEOREF)
            #print 'videoref = %s' % videoref   
            
            is_new = False
            if not flat_menu:
                is_yes = get_first_node_val(movie, SIMPLEVOD_XML_TAG_NEW)
                if is_yes == SIMPLEVOD_XML_VAL_YES:
                    is_new = True
            #print 'is_new = %s' % is_new   

            idat_value                  = TVOD_ID_AT
            #print 'idat_value = %s' % idat_value   
            videoref_value              = videoref
            #print 'videoref_value = %s' % videoref_value   
            title_value                 = title
            #print 'title_value = %s' % title_value   
            #==============================================================================>
            # Generate random asset-number (with default seed based on system-time).
            #==============================================================================>
            str_tvod_product_code_end =  "a%06d" % tvod_product_code_end
            tvod_product_code_end += 1
            #==============================================================================>
            #print 'Random asset-nr. %s' % str_tvod_product_code_end     
            #==============================================================================>
            #productcode_value           = TVOD_PRODUCT_CODE_START + '.' + feed_name + '.' + TVOD_PRODUCT_CODE_END
            productcode_value           = TVOD_PRODUCT_CODE_START + '.' + feed_name + '.' + str_tvod_product_code_end
            #print 'productcode_value = %s' % productcode_value   
            enduseramount_value         = TVOD_END_USER_AMOUNT 
            #print 'enduseramount_value = %s' % enduseramount_value   
            amount_value                = TVOD_AMOUNT 
            #print 'amount_value = %s' % amount_value   
            skipconfirm_value           = TVOD_SKIP_CONFIRM 
            #print 'skipconfirm_value = %s' % skipconfirm_value   
            expiry_period_value         = TVOD_EXPIRY_PERIOD 
            #print 'expiry_period_value = %s' % expiry_period_value   
            status_value                = TVOD_STATUS
            #print 'status_value = %s' % status_value   
            productdescription_value    = feed_title  + ": " + title_value
            #print 'productdescription_value = %s' % productdescription_value   

            #==============================================================================>
            # Insert record into table:simplevod_tvod with videoref, title, productcode, 
            # enduseramount, amount, skipconfirm, expiry_period, status and foreign-keys from 
            # table:simplevod_feed, simplevod_category.
            #==============================================================================>
            # print 'Insert record into table:simplevod_tvod'   

            max_tvod_order += 1
            if old_order:
                max_tvod_old_order += 1
                oldorder_tvod = max_tvod_old_order
            else:
                oldorder_tvod = 0

            if is_new:
                query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
            else:
                query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"

            cursor.execute(query, (max_tvod_order, oldorder_tvod, idat_value, videoref_value, title_value, productcode_value, enduseramount_value, amount_value, skipconfirm_value, expiry_period_value, status_value, productdescription_value, category_id, feed_id))

            record_data['inserted_tvod'] += 1

        try:
            base = os.path.splitext(file_name)[0]
            os.rename(file_name, base + SIMPLEVOD_FIN_EXT)
        except OSError as e:
            log_message = "Cannot rename XML data file '{0}' [{1}]".format(file_name,str(e))
            log.exception(log_message)

    except Exception as e:
        log_message = "Error in configuration file '{0}' [{1}]".format(feed_config,str(e))
        log.exception(log_message)
        sys.exit(1)

    record_data["max_category_order"] = max_category_order
    record_data["max_category_old_order"] = max_category_old_order
    record_data["max_tvod_order"] = max_tvod_order
    record_data["max_tvod_old_order"] = max_tvod_old_order
    return record_data

#==============================================================================>
# function object : get_first_node_val
# parameters      : none
# return value    : none
# description     : 
#==============================================================================>
def get_first_node_val(obj, tag):
    try:
        return obj.getElementsByTagName(tag)[0].childNodes[0].nodeValue
    
    except Exception: 
        return False

#==============================================================================>
# function object : find_latest_xml
# parameters      : 
# return value    : 
# description     : 
#==============================================================================>
def find_xml_files_in_dir(path):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime

    dirlist = list(sorted(os.listdir(path), key=mtime))
    list_of_files = [file for file in dirlist if file.lower().endswith(SIMPLEVOD_XML_EXT)]
    list_of_files.reverse()
    return list_of_files

#==============================================================================>
# function object : update_file_data
# parameters      : log, feed_config, record_data
# return value    : 
# description     : 
#==============================================================================>
def update_file_data(log, feed_config, record_data):

    if feed_config.has_key("id"):
        feed_id = feed_config["id"]
    else:
        log_message =  '!!! PLEASE TAKE NOTICE: feed in configuration file has no - id - defined.'
        log.info(log_message)
        return record_data

    if feed_config.has_key("path"):
        path = feed_config["path"]
    else:
        log_message =  '!!! PLEASE TAKE NOTICE: feed in configuration file has no - path - defined.'
        log.info(log_message)
        return record_data

    if not os.path.exists(path):
        log_message =  '!!! PLEASE TAKE NOTICE: directory %s - source of XML data files - does not exist.' % path
        log.info(log_message)
        return record_data

    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # Update record in table:simplevod_tvod.
        #print 'Update record into table:simplevod_tvod. id nr. %d' % feed_id    
        #==============================================================================>
        cursor.execute("UPDATE public.simplevod_tvod SET active='false' WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': feed_id } )

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1

    list_of_video_files = find_video_files_in_dir(path)
    if len(list_of_video_files) != 0:

        for video_file in list_of_video_files:
            file_name = os.path.join(path, video_file)
            record_data = load_video_file(file_name, feed_config, record_data)
    else:
        log_message = '!!! PLEASE TAKE NOTICE: directory %s - source of VIDEO data files - is empty.' % path
        log.info(log_message)
        return record_data

    return record_data

#==============================================================================>
# function object : load_file_data
# parameters      : con, file_name, feed_config, counting_records
# return value    : 
# description     : 
#==============================================================================>
def load_video_file(file_name, feed_config, record_data):

    if feed_config.has_key("id"):
        feed_id = feed_config["id"]
    else:
        log_message =  '!!! PLEASE TAKE NOTICE: feed in configuration file has no - id - defined.'
        log.info(log_message)
        return record_data

    base_name = basename(file_name)
    base_name = base_name.strip()
 
    #==============================================================================>
    # Renew connection to database - Start a new Transaction.
    #==============================================================================>
    try:
        conn = None
        conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        cursor = conn.cursor()

        #==============================================================================>
        # Check vod based on videoref.
        #==============================================================================>
        cursor.execute("SELECT id FROM public.simplevod_tvod WHERE videoref=%(videoref)s AND fk_feed_id=%(fk_feed_id)s", {'videoref': base_name, 'fk_feed_id': feed_id } )
        item_tvod_row = cursor.fetchone()

    except psycopg2.DatabaseError, e:
        log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
        log.exception(log_message)
        sys.exit(1)
        
    finally:
        if conn:
            #==============================================================================>
            # Commit Transaction & Close Connection
            #==============================================================================>
            conn.commit()
            conn.close()
            record_data['database_connections'] += 1


    if item_tvod_row == None:

        #==============================================================================>
        # New records are place at the beginning of the ordering.
        # To make this possible add one to order field of existing records.
        #==============================================================================>

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("ALTER TABLE simplevod_tvod DROP CONSTRAINT simplevod_tvod_order_key;")

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            #sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("UPDATE simplevod_tvod SET \"order\" = \"order\" + 1;")
            cursor.execute("UPDATE simplevod_tvod SET oldorder = oldorder + 1 WHERE oldorder != 0;")

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            cursor.execute("ALTER TABLE simplevod_tvod ADD CONSTRAINT simplevod_tvod_order_key UNIQUE (\"order\");")

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            latest_tvod_order = 1

            if feed_config.has_key("path"):
                path = feed_config["path"]
            else:
                log_message =  '!!! PLEASE TAKE NOTICE: feed in configuration file has no - path - defined.'
                log.info(log_message)
                return record_data

            if feed_config.has_key("name"):
                feed_name = feed_config["name"]
            else:
                log_message =  '!!! PLEASE TAKE NOTICE: feed in configuration file has no - name - defined.'
                log.info(log_message)
                return record_data

            if feed_config.has_key("title"):
                feed_title = feed_config["title"]
            else:
                log_message =  '!!! PLEASE TAKE NOTICE: feed in configuration file has no - title - defined.'
                log.info(log_message)
                return record_data

            #==============================================================================>
            # Generate random asset-number (with default seed based on system-time).
            #==============================================================================>
            tvod_product_code_end = random.randrange(1,999998+1)

            #==============================================================================>
            #print 'Random with system seed. %d' % tvod_product_code_end     
            #==============================================================================>
            category_id = None
            #print 'category_id = %s' % category_id   
            videoref = base_name
            #print 'videoref = %s' % videoref   
            title = os.path.splitext(base_name)[0]
            #print 'title = %s' % title   
            is_new = False
            #print 'is_new = %s' % is_new   
            idat_value                  = TVOD_ID_AT
            #print 'idat_value = %s' % idat_value   
            videoref_value              = videoref
            #print 'videoref_value = %s' % videoref_value   
            title_value                 = title
            #print 'title_value = %s' % title_value   
            #==============================================================================>
            # Generate random asset-number (with default seed based on system-time).
            #==============================================================================>
            str_tvod_product_code_end =  "a%06d" % tvod_product_code_end
            #==============================================================================>
            #print 'Random asset-nr. %s' % str_tvod_product_code_end     
            #==============================================================================>
            productcode_value           = TVOD_PRODUCT_CODE_START + '.' + feed_name + '.' + str_tvod_product_code_end
            #print 'productcode_value = %s' % productcode_value   
            enduseramount_value         = TVOD_END_USER_AMOUNT 
            #print 'enduseramount_value = %s' % enduseramount_value   
            amount_value                = TVOD_AMOUNT 
            #print 'amount_value = %s' % amount_value   
            skipconfirm_value           = TVOD_SKIP_CONFIRM 
            #print 'skipconfirm_value = %s' % skipconfirm_value   
            expiry_period_value         = TVOD_EXPIRY_PERIOD 
            #print 'expiry_period_value = %s' % expiry_period_value   
            status_value                = TVOD_STATUS
            #print 'status_value = %s' % status_value   
            productdescription_value    = feed_title  + ": " + title_value
            #print 'productdescription_value = %s' % productdescription_value   

            #==============================================================================>
            # Insert record into table:simplevod_tvod with videoref, title, productcode, 
            # enduseramount, amount, skipconfirm, expiry_period, status and foreign-keys from 
            # table:simplevod_feed, simplevod_category.
            #==============================================================================>

            query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"

            cursor.execute(query, (latest_tvod_order, latest_tvod_order, idat_value, videoref_value, title_value, productcode_value, enduseramount_value, amount_value, skipconfirm_value, expiry_period_value, status_value, productdescription_value, category_id, feed_id))

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1
        
    else:
        tvod_id = item_tvod_row[0]
        
        #==============================================================================>
        # Renew connection to database - Start a new Transaction.
        #==============================================================================>
        try:
            conn = None
            conn = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
            cursor = conn.cursor()

            #==============================================================================>
            # Update record in table:simplevod_tvod.
            #print 'Update record into table:simplevod_tvod. id nr. %d' % tvod_id     
            #==============================================================================>
            cursor.execute("UPDATE public.simplevod_tvod SET active='true' WHERE id=%(id)s", {'id': tvod_id } )
            record_data['updated_tvod'] += 1

        except psycopg2.DatabaseError, e:
            log_message = time.strftime("%Y-%m-%d %H:%M:%S") + " Error %s" % e  
            log.exception(log_message)
            sys.exit(1)
            
        finally:
            if conn:
                #==============================================================================>
                # Commit Transaction & Close Connection
                #==============================================================================>
                conn.commit()
                conn.close()
                record_data['database_connections'] += 1

    return record_data

#==============================================================================>
# function object : find_video_files_in_dir
# parameters      : path
# return value    : 
# description     : 
#==============================================================================>
def find_video_files_in_dir(path):
    mtime = lambda f: os.stat(os.path.join(path, f)).st_mtime

    dirlist = list(sorted(os.listdir(path), key=mtime))
    list_of_files = [file for file in dirlist if (file.lower().endswith(SIMPLEVOD_MPG_EXT) or file.lower().endswith(SIMPLEVOD_MPEG_EXT) or file.lower().endswith(SIMPLEVOD_TS_EXT))]
    #list_of_files.reverse()
    return list_of_files

#==============================================================================>
# Call main function. 
#==============================================================================>
if __name__ == "__main__":
    path = arguments(sys.argv[1:])
    
    lock_file = path + '/' + 'lock.file'
    lock = FileLock(lock_file)
    
    if lock.acquire():
        main(path)
        lock.release()

              

