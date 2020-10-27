#!/usr/bin/python
#==============================================================================>
# script title    : SimplevodLoadDatabase.py
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
import json
import re 
import httplib
import urllib
import urllib2
import psycopg2
import time
import datetime
import random

from os.path import basename

from feed import Feed
from xml.dom import minidom
from stat import S_ISREG, ST_CTIME, ST_MODE

SIMPLEVOD_JSON_CONFIG = '../cfg/config.json'

CONFIG_LOAD_YES                 = 'yes'
CONFIG_LOAD_NO                  = 'no'

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

SIMPLEVOD_MPG_EXT               = 'mpg'
SIMPLEVOD_MPEG_EXT              = 'mpeg'
SIMPLEVOD_TS_EXT                = 'ts'

SIMPLEVOD_DUMMY_TITLE           = 'video-title'

SIMPLEVOD_XML_EXT               = 'xml'
SIMPLEVOD_FIN_EXT               = '.done'

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
# description     : Read in simplevod json config and linked-data into postgreSQL.
#==============================================================================>
def main():
    print 'Starting application:SimplevodLoadDatabase.'    

    json_cfg_file = SIMPLEVOD_JSON_CONFIG
    json_config = {}
    json_config = read_contents(json_cfg_file)

    con = None

    counting_records = dict()
    counting_records["category"] = 0
    counting_records["tvod"] = 0
    counting_records["partial_count_category"] = 0
    counting_records["partial_count_tvod"] = 0

    print 'Connect to postgreSQL database:simplevod.'    

    try:
        con = psycopg2.connect(host='localhost', port=5432, database='simplevod', user='postgres', password='simplevod') 
        con.autocommit = True
        cursor = con.cursor()
        print 'Fetch cursor database:simplevod.'    

        #==============================================================================>
        # Get max order from table:simplevod_category.
        #==============================================================================>
        cursor.execute("SELECT MAX(\"order\") FROM public.simplevod_category")
        row = cursor.fetchone()            

        if row[0] is not None:
            max_category_order = int(row[0])
        else:
            max_category_order = 0

        counting_records["category"] = max_category_order
        #==============================================================================>
        print 'Get max order from table:simplevod_category. %d' % counting_records["category"]   
        #==============================================================================>

        #==============================================================================>
        # Get max order from table:simplevod_tvod.
        #==============================================================================>
        cursor.execute("SELECT MAX(\"order\") FROM public.simplevod_tvod")

        row = cursor.fetchone()            
        if row[0] is not None:
            max_tvod_order = int(row[0])
        else:
            max_tvod_order = 0

        counting_records["tvod"] = max_tvod_order
        #==============================================================================>
        print 'Get max order from table:simplevod_tvod. %d' % counting_records["category"]   
        #==============================================================================>

        #==============================================================================>
        # Get max oldorder from table:simplevod_category.
        #==============================================================================>
        cursor.execute("SELECT MAX(oldorder) FROM public.simplevod_category")
        row = cursor.fetchone()            

        if row[0] is not None:
            max_category_old_order = int(row[0])
        else:
            max_category_old_order = 0

        counting_records["partial_count_category"] = max_category_old_order
        #==============================================================================>
        print 'Get max oldorder from table:simplevod_category. %d' % counting_records["category"]   
        #==============================================================================>

        #==============================================================================>
        # Get max oldorder from table:simplevod_tvod.
        #==============================================================================>
        cursor.execute("SELECT MAX(oldorder) FROM public.simplevod_tvod")
        row = cursor.fetchone()            

        if row[0] is not None:
            max_tvod_old_order = int(row[0])
        else:
            max_tvod_old_order = 0

        counting_records["partial_count_tvod"] = max_tvod_old_order
        #==============================================================================>
        print 'Get max oldorder from table:simplevod_tvod. %d' % counting_records["category"]   
        #==============================================================================>

        #==============================================================================>
        # TRUNCATE and reset the SERIAL counter (also automatically truncate all tables 
        # that have foreign-key references ).
        #==============================================================================>
        #print 'truncate database:simplevod table:simplevod_feed'    
        #cursor.execute("TRUNCATE public.simplevod_feed RESTART IDENTITY CASCADE;")
        #print 'truncate database:simplevod table:simplevod_category'    
        #cursor.execute("TRUNCATE public.simplevod_category RESTART IDENTITY CASCADE;")
        #print 'truncate database:simplevod table:simplevod_tvod'    
        #cursor.execute("TRUNCATE public.simplevod_tvod RESTART IDENTITY CASCADE;")
        print 'truncate database:simplevod table:simplevod_new'    
        cursor.execute("TRUNCATE public.simplevod_new RESTART IDENTITY CASCADE;")

        print 'truncate database:simplevod table:simplevod_simplevoduser'    
        cursor.execute("TRUNCATE public.simplevod_simplevoduser RESTART IDENTITY CASCADE;")

        #==============================================================================>
        # SET field retrieve to zero for all feeds.
        #print 'SET field retrieve to zero for all feeds.'     
        #==============================================================================>
        #cursor.execute("UPDATE public.simplevod_feed SET retrieve='0'")

        for n, feed_config in enumerate(json_config.get("feeds")):

            if feed_config.has_key("name"):
                feed_config_name = feed_config["name"]
            else:
                print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - name - defined.'
                continue

            if feed_config.has_key("load"):
                feed_config_load = feed_config["load"]
                feed_config_load = feed_config_load.lower()
            else:
                print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - load - defined.'
                continue

            if feed_config_load == CONFIG_LOAD_YES:
                print 'LOAD: feed %s' % feed_config_name   

                cursor.execute("SELECT id FROM public.simplevod_feed WHERE name=%(name)s", {'name': feed_config_name } )

                simplevod_feed_id = 0

                feed_row = cursor.fetchone()
                if feed_row != None:
   
                    simplevod_feed_id = feed_row[0]         

                    #==============================================================================>
                    # Delete all records from table:simplevod_category with this feed.
                    print 'Delete all records from table:simplevod_tvod with this feed. id nr. %d' % simplevod_feed_id     
                    #==============================================================================>
                    cursor.execute("DELETE FROM public.simplevod_tvod WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': simplevod_feed_id } )
             
                    #==============================================================================>
                    # Delete all records from table:simplevod_category with this feed.
                    print 'Delete all records from table:simplevod_category with this feed. id nr. %d' % simplevod_feed_id     
                    #==============================================================================>
                    cursor.execute("DELETE FROM public.simplevod_category WHERE fk_feed_id=%(fk_feed_id)s", {'fk_feed_id': simplevod_feed_id } )
             
                    #==============================================================================>
                    # UPDATE FEED              
                    #==============================================================================>
                    update_feed(con, simplevod_feed_id, feed_config)

                else:
                    #==============================================================================>
                    # INSERT FEED              
                    #==============================================================================>
                    simplevod_feed_id = insert_feed(con, feed_config)

                feed_config_source = feed_config["source"]
                feed_config_source = feed_config_source.lower()

                if feed_config_source == CONFIG_SOURCE_JSON:
                    if feed_config.has_key("url") and feed_config.has_key("name"):
                        counting_records = load_json_data(con, simplevod_feed_id, feed_config, counting_records)
                    
                elif feed_config_source == CONFIG_SOURCE_XML:
                    if feed_config.has_key("dir") and feed_config.has_key("name"):
                        counting_records = load_xml_data(con, simplevod_feed_id, feed_config, counting_records)

                elif feed_config_source == CONFIG_SOURCE_FILE:
                    if feed_config.has_key("dir") and feed_config.has_key("name"):
                        counting_records = load_file_data(con, simplevod_feed_id, feed_config, counting_records)

            elif feed_config_load == CONFIG_LOAD_NO:
                print '!!! PLEASE TAKE NOTICE: feed %s not loaded' % feed_config_name   

    except psycopg2.DatabaseError, e:
        print 'Error %s' % e    
        sys.exit(1)
        
    finally:
        print 'Reconcile records in table:simplevod_new with those in table:simplevod_category.'    
        reconcile_new_items(con, counting_records)
    
        print 'Finishing application:SimplevodLoadDatabase.'    
        if con:
            con.close()

#==============================================================================>
# function object : update_feed
# parameters      : con, simplevod_feed_id, feed_config
# return value    : 
# description     : 
#==============================================================================>
def update_feed(con, simplevod_feed_id, feed_config):
    cursor = con.cursor()

    try:
        #==============================================================================>
        # Update field name in record in table:simplevod_feed.
        print 'Update field title in record in table:simplevod_feed.'     
        #==============================================================================>
        simplevod_title = ""
        if feed_config.has_key("title"):
            simplevod_title = feed_config["title"]
            cursor.execute("UPDATE public.simplevod_feed SET title=%(title)s WHERE id=%(id)s", {'title': simplevod_title, 'id': simplevod_feed_id } )
        else:
            print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - title - defined.'

    except psycopg2.DatabaseError, e:
        print 'Error %s' % e    
        sys.exit(1)

    try:
        #==============================================================================>
        # Update field name in record in table:simplevod_feed.
        print 'Update field style in record in table:simplevod_feed.'     
        #==============================================================================>
        simplevod_style = ""
        if feed_config.has_key("style"):
            simplevod_style = feed_config["style"]
            cursor.execute("UPDATE public.simplevod_feed SET style=%(style)s WHERE id=%(id)s", {'style': simplevod_style, 'id': simplevod_feed_id } )
        else:
            print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - style - defined.'

    except psycopg2.DatabaseError, e:
        print 'Error %s' % e    
        sys.exit(1)

    if feed_config.has_key("source"):
        feed_config_source = feed_config["source"]
        feed_config_source = feed_config_source.lower()

        if feed_config_source == CONFIG_SOURCE_JSON:
            simplevod_retrieve = CONFIG_SOURCE_JSON_ID

            try:
                #==============================================================================>
                # Update field url and retrieve in record in table:simplevod_feed.
                print 'Update field url and retrieve in record in table:simplevod_feed.'     
                #==============================================================================>
                if feed_config.has_key("url"):
                    simplevod_url = feed_config["url"]
                    cursor.execute("UPDATE public.simplevod_feed SET url=%(url)s, retrieve=%(retrieve)s WHERE id=%(id)s", {'url': simplevod_url, 'retrieve': simplevod_retrieve, 'id': simplevod_feed_id } )
                else:
                    print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - url - defined.'

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)
            
        elif feed_config_source == CONFIG_SOURCE_XML:
            simplevod_retrieve = CONFIG_SOURCE_XML_ID
            
            try:
                #==============================================================================>
                # Update field url and retrieve in record in table:simplevod_feed.
                print 'Update field url and retrieve in record in table:simplevod_feed.'     
                #==============================================================================>
                if feed_config.has_key("dir"):
                    simplevod_dir = feed_config["dir"]
                    cursor.execute("UPDATE public.simplevod_feed SET xml=%(xml)s, retrieve=%(retrieve)s WHERE id=%(id)s", {'xml': simplevod_dir, 'retrieve': simplevod_retrieve, 'id': simplevod_feed_id } )
                else:
                    print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - dir - defined.'

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)

        elif feed_config_source == CONFIG_SOURCE_FILE:
            simplevod_retrieve = CONFIG_SOURCE_FILE_ID
            
            try:
                #==============================================================================>
                # Update field url and retrieve in record in table:simplevod_feed.
                print 'Update field url and retrieve in record in table:simplevod_feed.'     
                #==============================================================================>
                if feed_config.has_key("dir"):
                    simplevod_dir = feed_config["dir"]
                    cursor.execute("UPDATE public.simplevod_feed SET xml=%(xml)s, retrieve=%(retrieve)s WHERE id=%(id)s", {'xml': simplevod_dir, 'retrieve': simplevod_retrieve, 'id': simplevod_feed_id } )
                else:
                    print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - dir - defined.'

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)

    else:
        print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - source - defined.'

    if feed_config.has_key("django"):
        feed_config_django = feed_config["django"]
        feed_config_django = feed_config_django.lower()
        
        if feed_config_django == CONFIG_DJANGO_NO:
            try:
                #==============================================================================>
                # Update field is_django in record in table:simplevod_feed.
                print 'Update field is_django in record in table:simplevod_feed.'     
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_feed SET is_django='false' WHERE id=%(id)s", {'id': simplevod_feed_id } )

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)

        elif feed_config_django == CONFIG_DJANGO_YES:
            try:
                #==============================================================================>
                # Update field is_django in record in table:simplevod_feed.
                print 'Update field is_django in record in table:simplevod_feed.'     
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_feed SET is_django='true' WHERE id=%(id)s", {'id': simplevod_feed_id } )

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)

    if feed_config.has_key("category"):
        feed_config_category = feed_config["category"]
        feed_config_category = feed_config_category.lower()
        
        if feed_config_category == CONFIG_CATEGORY_NO:
            try:
                #==============================================================================>
                # Update field use_category in record in table:simplevod_feed.
                print 'Update field use_category in record in table:simplevod_feed.'     
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_feed SET use_category='false' WHERE id=%(id)s", {'id': simplevod_feed_id } )

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)

        elif feed_config_category == CONFIG_CATEGORY_YES:
            try:
                #==============================================================================>
                # Update field is_django and use_category in record in table:simplevod_feed.
                print 'Update field use_category in record in table:simplevod_feed.'     
                #==============================================================================>
                cursor.execute("UPDATE public.simplevod_feed SET use_category='true' WHERE id=%(id)s", {'id': simplevod_feed_id } )

            except psycopg2.DatabaseError, e:
                print 'Error %s' % e    
                sys.exit(1)

#==============================================================================>
# function object : insert_feed
# parameters      : con, feed_config
# return value    : 
# description     : 
#==============================================================================>
def insert_feed(con, feed_config):
    cursor = con.cursor()

    simplevod_name = feed_config["name"]

    simplevod_retrieve = 0
    simplevod_url = ""
    simplevod_dir = ""

    if feed_config.has_key("source"):
        feed_config_source = feed_config["source"]
        feed_config_source = feed_config_source.lower()

        if feed_config_source == CONFIG_SOURCE_JSON:
            simplevod_retrieve = CONFIG_SOURCE_JSON_ID

            if feed_config.has_key("url"):
                simplevod_url = feed_config["url"]

        elif feed_config_source == CONFIG_SOURCE_XML:
            simplevod_retrieve = CONFIG_SOURCE_XML_ID

            if feed_config.has_key("dir"):
                simplevod_dir = feed_config["dir"]

        elif feed_config_source == CONFIG_SOURCE_FILE:
            simplevod_retrieve = CONFIG_SOURCE_FILE_ID

            if feed_config.has_key("dir"):
                simplevod_dir = feed_config["dir"]

    else:
        print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - source - defined.'

    simplevod_style = ""

    if feed_config.has_key("style"):
        simplevod_style = feed_config["style"]
    else:
        print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - style - defined.'

    simplevod_title = ""

    if feed_config.has_key("title"):
        simplevod_title = feed_config["title"]
    else:
        print '!!! PLEASE TAKE NOTICE: feed in configuration file has no - title - defined.'

    simplevod_etag = SIMPLEVOD_DUMMY_ETAG

    feed_django = 'false'
    if feed_config.has_key("django"):
        feed_config_django = feed_config["django"]
        feed_config_django = feed_config_django.lower()
        
        if feed_config_django == CONFIG_DJANGO_NO:
            feed_django = 'false'
        elif feed_config_django == CONFIG_DJANGO_YES:
            feed_django = 'true'

    feed_category = 'false'
    if feed_config.has_key("category"):
        feed_config_category = feed_config["category"]
        feed_config_category = feed_config_category.lower()
        
        if feed_config_category == CONFIG_CATEGORY_NO:
            feed_category = 'false'
        elif feed_config_category == CONFIG_CATEGORY_YES:
            feed_category = 'true'

    #==============================================================================>
    # Insert record into table:simplevod_feed with name, url, style.
    #==============================================================================>
    print 'Insert record into table:simplevod_feed'    

    query = "INSERT INTO public.simplevod_feed(name, url, xml, retrieve, style, title, etag, is_django, use_category) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id;"
    cursor.execute(query, (simplevod_name, simplevod_url, simplevod_dir, simplevod_retrieve, simplevod_style, simplevod_title, simplevod_etag, feed_django, feed_category))

    simplevod_feed_id = cursor.fetchone()[0]
    #print 'simplevod_feed_id %d' % simplevod_feed_id    

    return simplevod_feed_id

#==============================================================================>
# function object : read_contents
# parameters      : json config file and path
# return value    : data object with contents json config file
# description     : This will load file contents into memory.
#==============================================================================>
def read_contents(file_path):

    print 'read_contents - file_path %s' % file_path

    try:
        fh = open(file_path,"r")
    except Exception as e:
        raise Exception("Cannot open file: '{0}'".format(file_path))
        sys.exit(1)

    try:
        file_contents = json.load(fh)
    except ValueError, e:
        print 'Error %s' % e    
        sys.exit(1)
    finally:
        fh.close()

    return file_contents

#==============================================================================>
# function object : instantiate_class_feed
# parameters      : 
# return value    : 
# description     : 
#==============================================================================>
def instantiate_class_feed(feed_config):
    try:
		return Feed(feed_config)
        
    except Exception as e:
        raise Exception(
            "Cannot instantiate Feed object for feed '{0}' [{1}]".format(
                feed_config["name"],
                str(e)
            )
        )

#==============================================================================>
# function object : load_json_data
# parameters      : con, simplevod_feed_id, feed_config, counting_records
# return value    : 
# description     : 
#==============================================================================>
def load_json_data(con, simplevod_feed_id, feed_config, counting_records):
    cursor = con.cursor()

    try:
        name = feed_config["name"]
        path = feed_config["url"]
        style = feed_config["style"]
 
        match =  validate_jsonld_url(path)
        if not match:
            print '!!! PLEASE TAKE NOTICE: URL %s - source of JSON data files - does not exist.' % path
            return counting_records

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
        if feed_config.has_key("category"):
            feed_config_category = feed_config["category"]
            feed_config_category = feed_config_category.lower()
            
            if feed_config_category == CONFIG_CATEGORY_NO:
                feed_category = 'false'
            elif feed_config_category == CONFIG_CATEGORY_YES:
                feed_category = 'true'
        
        counting_records_category = counting_records["category"]
        counting_records_tvod = counting_records["tvod"]
           
        partial_counting_records_category = counting_records["partial_count_category"] 
        partial_counting_records_tvod = counting_records["partial_count_tvod"] 
           
        #==============================================================================>
        # Make instance of class Feed and load/parse associated json-linked-data.
        #==============================================================================>
        feed = None
        feed = instantiate_class_feed(feed_config)
        feed_title = feed.title

        try:
            #==============================================================================>
            # Update field title in record in table:simplevod_feed.
            print 'Update field title in record in table:simplevod_feed.'     
            #==============================================================================>
            cursor.execute("UPDATE public.simplevod_feed SET title=%(title)s WHERE id=%(id)s", {'title': feed_title, 'id': simplevod_feed_id } )

        except psycopg2.DatabaseError, e:
            print 'Error %s' % e    
            sys.exit(1)

        counting_records_category += 1

        if old_order:
            partial_counting_records_category += 1
            oldorder_category = partial_counting_records_category
        else:
            oldorder_category = 0

        query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, true, false) RETURNING id;"

        cursor.execute(query, (counting_records_category, oldorder_category, IDAT_RECENT_CATEGORY, SIMPLEVOD_NEW_CATEGORY, simplevod_feed_id))
        new_category_id = cursor.fetchone()[0]

        for category in feed.categories:
            if len(category['items']) == 0:
                continue

            is_new_category = False
            at_id_value = category["@id"]

            title_value = category["title"]
            title_value = title_value.strip()

            if title_value.lower() != SIMPLEVOD_NEW_CATEGORY.lower():
                #==============================================================================>
                # Insert record into table:simplevod_category with title and foreign-key 
                # from table:simplevod_feed.
                #==============================================================================>
                print 'Insert record into table:simplevod_category'   
                    
                counting_records_category += 1
   
                if old_order:
                    partial_counting_records_category += 1
                    oldorder_category = partial_counting_records_category
                else:
                    oldorder_category = 0

                query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, false, true) RETURNING id;"
                cursor.execute(query, (counting_records_category, oldorder_category, at_id_value, title_value, simplevod_feed_id))

                simplevod_category_id = cursor.fetchone()[0]
            else:
                #==============================================================================>
                # Update record in table:simplevod_category.
                #==============================================================================>
                #print 'Update standard record with - category new - in table:simplevod_category'    
                cursor.execute("UPDATE public.simplevod_category SET active='true' WHERE id=%(id)s", {'id': new_category_id } )

                is_new_category = True
                simplevod_category_id = new_category_id

            category_items = category["items"]
            for category_item in category_items:
                videoref_value =category_item["video"]["videoref"]
                #print 'videoref %s' % videoref_value    

                title_value = category_item["title"]
                #print 'title %s' % title_value    

                productcode_value = category_item["productcode"]
                #print 'productcode %s' % productcode_value    

                status_value = "available"
                #print 'status %s' % status_value    

                productdescription_value = feed_title + ": " + category_item["title"]
                #print 'productdescription %s' % productdescription_value    

                if is_new_category:
                    #==============================================================================>
                    # Temporarily insert record into table:simplevod_new with videoref, title, productcode, 
                    # enduseramount, amount, skipconfirm, expiry_period, status and foreign-keys from 
                    # table:simplevod_feed, simplevod_category, simplevod_item.
                    #==============================================================================>
                    query = "INSERT INTO public.simplevod_new(idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_django, is_new, active)" + \
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
                    cursor.execute(query, (category_item["@id"], videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, simplevod_category_id, simplevod_feed_id, feed_django))
                else:
                    #==============================================================================>
                    # Insert record into table:simplevod_tvod with videoref, title, productcode, 
                    # enduseramount, amount, skipconfirm, expiry_period, status and foreign-keys from 
                    # table:simplevod_feed, simplevod_category, simplevod_item.
                    #==============================================================================>
                    # print 'Insert record into table:simplevod_tvod'   
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    
                    counting_records_tvod += 1
        
                    if old_order:
                        partial_counting_records_tvod += 1
                        oldorder_tvod = partial_counting_records_tvod
                    else:
                        oldorder_tvod = 0

                    query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                    " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"
                    
                    cursor.execute(query, (counting_records_tvod, oldorder_tvod, category_item["@id"], videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, simplevod_category_id, simplevod_feed_id))

            sys.stdout.write('\n')

        counting_records["category"] = counting_records_category
        counting_records["tvod"] = counting_records_tvod

        counting_records["partial_count_category"] = partial_counting_records_category
        counting_records["partial_count_tvod"] = partial_counting_records_tvod

    except Exception as e:
        raise Exception("Error in configuration file : '{0}'".format(feed_config))
        sys.exit(1)

    return counting_records

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
# function object : load_xml_data
# parameters      : con, simplevod_feed_id, feed_config, counting_records
# return value    : 
# description     : 
#==============================================================================>
def load_xml_data(con, simplevod_feed_id, feed_config, counting_records):
    cursor = con.cursor()

    try:
        feed_name = feed_config["name"]
        path = feed_config["dir"]
        style = feed_config["style"]
        feed_title = feed_config["title"]

        if not os.path.exists(path):
            print '!!! PLEASE TAKE NOTICE: directory %s - source of XML data files - does not exist.' % path
            return counting_records

        list_of_xml_files = find_xml_files_in_dir(path)
        if len(list_of_xml_files) != 0:
            xml_file = list_of_xml_files[0]
            file_name = os.path.join(path, xml_file)
        else:
            print '!!! PLEASE TAKE NOTICE: directory %s - source of XML data files - is empty.' % path
            return counting_records

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

        counting_records_category = counting_records["category"]
        counting_records_tvod = counting_records["tvod"]

        partial_counting_records_category = counting_records["partial_count_category"] 
        partial_counting_records_tvod = counting_records["partial_count_tvod"] 

        counting_records_category += 1

        if old_order:
            partial_counting_records_category += 1
            oldorder_category = partial_counting_records_category
        else:
            oldorder_category = 0

        if not flat_menu:
            query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, true, false) RETURNING id;"
            cursor.execute(query, (counting_records_category, oldorder_category, IDAT_RECENT_CATEGORY, SIMPLEVOD_NEW_CATEGORY, simplevod_feed_id))
            new_category_id = cursor.fetchone()[0]

        try:
            xmldoc = minidom.parse(file_name)
        except:
            print '!!! PLEASE TAKE NOTICE: could not retrieve XML from file %s.' % file_name
            counting_records["category"] = counting_records_category
            counting_records["tvod"] = counting_records_tvod
            return counting_records

        movieset = xmldoc.getElementsByTagName(SIMPLEVOD_XML_TAG_MAIN)[0]                  
        movie_categories = dict()
        movies = movieset.getElementsByTagName(SIMPLEVOD_XML_TAG_MOVIE)     

        #==============================================================================>
        # Generate random asset-number (with default seed based on system-time).
        #==============================================================================>
        tvod_product_code_end = random.randrange(1,999998+1)
        #==============================================================================>
        #print 'Random with system seed. %d' % tvod_product_code_end     
        #==============================================================================>
        
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

        if not flat_menu:
            category_title = 'Dummy Category'
        else:
            category_title = 'No Category'
        
        for key in movie_categories:
            category_title = key
            #==============================================================================>
            # Insert record into table:simplevod_category with title and foreign-key 
            # from table:simplevod_feed.
            #==============================================================================>
            print 'Insert record into table:simplevod_category'   
                
            counting_records_category += 1
   
            if old_order:
                partial_counting_records_category += 1
                oldorder_category = partial_counting_records_category
            else:
                oldorder_category = 0
             
            query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, false, true) RETURNING id;"
            cursor.execute(query, (counting_records_category, oldorder_category, CATEGORY_ID_AT, category_title, simplevod_feed_id))
            
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
                    print "category %s exists within movie_categories dictionary" % category
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
            sys.stdout.write('.')
            sys.stdout.flush()
            counting_records_tvod += 1

            if old_order:
                partial_counting_records_tvod += 1
                oldorder_tvod = partial_counting_records_tvod
            else:
                oldorder_tvod = 0

            if is_new:
                query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"
            else:
                query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
                " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"

            cursor.execute(query, (counting_records_tvod, oldorder_tvod, idat_value, videoref_value, title_value, productcode_value, enduseramount_value, amount_value, skipconfirm_value, expiry_period_value, status_value, productdescription_value, category_id, simplevod_feed_id))

        sys.stdout.write('\n')
        
        try:
            base = os.path.splitext(file_name)[0]
            os.rename(file_name, base + SIMPLEVOD_FIN_EXT)
        except OSError as e:
            raise Exception(
                "Cannot rename XML data files '{0}' [{1}]".format(
                    file_name,
                    str(e)
                )
            )

        counting_records["category"] = counting_records_category
        counting_records["tvod"] = counting_records_tvod

        counting_records["partial_count_category"] = partial_counting_records_category
        counting_records["partial_count_tvod"] = partial_counting_records_tvod

    except Exception as e:
        raise Exception("Error in configuration file : '{0}'".format(feed_config))
        sys.exit(1)

    return counting_records

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
# function object : find_xml_files_in_dir
# parameters      : path
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
# function object : load_file_data
# parameters      : con, simplevod_feed_id, feed_config, counting_records
# return value    : 
# description     : 
#==============================================================================>
def load_file_data(con, simplevod_feed_id, feed_config, counting_records):
    cursor = con.cursor()

    counting_records_category = counting_records["category"]
    partial_counting_records_category = counting_records["partial_count_category"] 

    old_order = True
    if feed_config.has_key("django"):
        feed_config_django = feed_config["django"]
        feed_config_django = feed_config_django.lower()
        
        if feed_config_django == CONFIG_DJANGO_NO:
            old_order = True
        elif feed_config_django == CONFIG_DJANGO_YES:
            old_order = False

    counting_records_category += 1

    if old_order:
        partial_counting_records_category += 1
        oldorder_category = partial_counting_records_category
    else:
        oldorder_category = 0

    try:
        #==============================================================================>
        # Insert record into table:simplevod_category with title New 
        print 'Insert record into table:simplevod_category with title New'   
        #==============================================================================>
        query = "INSERT INTO public.simplevod_category(\"order\", oldorder, idat, title, fk_feed_id, is_new, active) VALUES (%s, %s, %s, %s, %s, true, false) RETURNING id;"

        cursor.execute(query, (counting_records_category, oldorder_category, IDAT_RECENT_CATEGORY, SIMPLEVOD_NEW_CATEGORY, simplevod_feed_id))
        new_category_id = cursor.fetchone()[0]

    except psycopg2.DatabaseError, e:
        print 'Error %s' % e    
        sys.exit(1)

    path = feed_config["dir"]
    if not os.path.exists(path):
        print '!!! PLEASE TAKE NOTICE: directory %s - source of VIDEO data files - does not exist.' % path
        return counting_records

    list_of_video_files = find_video_files_in_dir(path)
    if len(list_of_video_files) != 0:

        for video_file in list_of_video_files:
            file_name = os.path.join(path, video_file)
            counting_records = load_video_file(con, file_name, simplevod_feed_id, feed_config, counting_records)
    else:
        print '!!! PLEASE TAKE NOTICE: directory %s - source of VIDEO data files - is empty.' % path
        return counting_records

    counting_records["category"] = counting_records_category
    counting_records["partial_count_category"] = partial_counting_records_category
    return counting_records

#==============================================================================>
# function object : load_file_data
# parameters      : con, file_name, simplevod_feed_id, feed_config, counting_records
# return value    : 
# description     : 
#==============================================================================>
def load_video_file(con, file_name, simplevod_feed_id, feed_config, counting_records):
    cursor = con.cursor()
 
    try:
        counting_records_tvod = counting_records["tvod"]
        partial_counting_records_tvod = counting_records["partial_count_tvod"] 

        feed_name = feed_config["name"]
        feed_title = feed_config["title"]
    
        #==============================================================================>
        # Generate random asset-number (with default seed based on system-time).
        #==============================================================================>
        tvod_product_code_end = random.randrange(1,999998+1)
        #==============================================================================>
        #print 'Random with system seed. %d' % tvod_product_code_end     
        #==============================================================================>
        category_id = None
        #print 'category_id = %s' % category_id   
        base_name = basename(file_name)
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
        print 'Insert record into table:simplevod_tvod'   

        sys.stdout.write('.')
        sys.stdout.flush()

        counting_records_tvod += 1

        old_order = True
        if feed_config.has_key("django"):
            feed_config_django = feed_config["django"]
            feed_config_django = feed_config_django.lower()
            
            if feed_config_django == CONFIG_DJANGO_NO:
                old_order = True
            elif feed_config_django == CONFIG_DJANGO_YES:
                old_order = False

        if old_order:
            partial_counting_records_tvod += 1
            oldorder_tvod = partial_counting_records_tvod
        else:
            oldorder_tvod = 0

        query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, false, true) RETURNING id;"

        cursor.execute(query, (counting_records_tvod, oldorder_tvod, idat_value, videoref_value, title_value, productcode_value, enduseramount_value, amount_value, skipconfirm_value, expiry_period_value, status_value, productdescription_value, category_id, simplevod_feed_id))

        sys.stdout.write('\n')
        counting_records["tvod"] = counting_records_tvod
        counting_records["partial_count_tvod"] = partial_counting_records_tvod

    except Exception as e:
        raise Exception("Error in configuration file : '{0}'".format(feed_config))
        sys.exit(1)

    return counting_records

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
# function object : reconcile_new_items
# parameters      : 
# return value    : 
# description     : 
#==============================================================================>
def reconcile_new_items(con, counting_records):
    cursor = con.cursor()

    counting_records_tvod = counting_records["tvod"]
    partial_counting_records_tvod = counting_records["partial_count_tvod"] 

    cursor.execute("SELECT * FROM public.simplevod_new;")
    rows = cursor.fetchall()
    for row in rows:
        sys.stdout.write('.')
        sys.stdout.flush()

        idat_value = row[1]
        videoref_value = row[2]
        title_value = row[3]
        productcode_value = row[4]
        status_value = row[9]
        productdescription_value = row[10]
        simplevod_feed_id = row[11]
        simplevod_category_id = None

        feed_django = row[15]
        
        cursor.execute("SELECT id FROM public.simplevod_tvod WHERE idat=%(idat)s AND fk_feed_id=%(fk_feed_id)s", {'idat': idat_value, 'fk_feed_id': simplevod_feed_id } )
        tvod_row = cursor.fetchone()
        if tvod_row != None:
            #==============================================================================>
            # Update record in table:simplevod_tvod.
            #==============================================================================>
            #print 'Update standard record with - category new - in table:simplevod_tvod'    
            cursor.execute("UPDATE public.simplevod_tvod SET is_new='true' WHERE id=%(id)s", {'id': tvod_row[0] } )
        else:
            #==============================================================================>
            # Insert record into table:simplevod_tvod with title and foreign-key 
            # from table:simplevod_tvod.
            #==============================================================================>
            #print 'Insert record into table:simplevod_tvod'    
            counting_records_tvod += 1

            oldorder_tvod = 0
            if feed_django != None:
                if feed_django:
                    oldorder_tvod = 0
                else:
                    partial_counting_records_tvod += 1
                    oldorder_tvod = partial_counting_records_tvod

            query = "INSERT INTO public.simplevod_tvod(\"order\", oldorder, idat, videoref, title, productcode, enduseramount, amount, skipconfirm, expiry_period, status, productdescription, fk_category_id, fk_feed_id, is_new, active)" + \
            " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, true, true) RETURNING id;"

            cursor.execute(query, (counting_records_tvod, oldorder_tvod, idat_value, videoref_value, title_value, productcode_value, "0", "0", "1", "172800", status_value, productdescription_value, simplevod_category_id, simplevod_feed_id))

    sys.stdout.write('\n')

    #==============================================================================>
    # TRUNCATE and reset the SERIAL counter (also automatically truncate all tables 
    # that have foreign-key references ).
    #==============================================================================>
    print 'truncate database:simplevod table:simplevod_new'    
    cursor.execute("TRUNCATE public.simplevod_new RESTART IDENTITY CASCADE;")

#==============================================================================>
# Call main function. 
#==============================================================================>
main()




