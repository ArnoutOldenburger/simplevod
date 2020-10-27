#!/usr/bin/python
#==============================================================================>
# script title    : views.py
# description     : Functions that take a Web request and return a Web response.
# author          : a.oldenburger
# date            : 20131030
# version         : 0.1
# usage           : django view
# notes           :
# python_version  : @home v2.7.2
#==============================================================================>
import sys
import httplib
import urllib
import urllib2
import json 

# For more information on logging refer to https://docs.djangoproject.com/en/dev/topics/logging/
# Write to logfile with statements like (for debug-level logging):logger.debug("launch site")
import logging
logger = logging.getLogger('svod')

# The next statement will disable all logging calls less severe than ERROR
# Comment this next satement to see more logging.
#logging.disable(logging.ERROR)
logging.disable(logging.DEBUG)

from django.conf import settings
from django.shortcuts import get_object_or_404, render_to_response
from django.http import HttpResponse
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils import simplejson
from django.core.serializers.json import DjangoJSONEncoder
from django.template import RequestContext
from django.utils.translation import gettext as _ 

from models import Feed, Category, Tvod
from django.db.models import Max

SIMPLEVOD_GEEN_CATEGORY = ' -- Geen-- '
SIMPLEVOD_NEW_CATEGORY = 'Nieuw'

#==============================================================================>
# function object : index
# parameters      : request
# return value    :
# description     : This will xx.
#==============================================================================>
def index(request):
    try:
        configuration = Feed.objects.all().order_by('name').exclude(retrieve=0)
        config_count = configuration.count()
        locals_vars = {	"config_count":config_count, "configuration":configuration }
        return render_to_response('index.html', locals_vars)

    except Exception as e:
        log_message = "Failure in procedure 'index' [{1}]".format(str(e))
        logger.exception(log_message)

#==============================================================================>
# function object : browse
# parameters      : request, style, feed_id
# return value    :
# description     : 
#==============================================================================>
def browse(request, feed_name):
    category_listing = []
    
    try:
        feeds = Feed.objects.filter(name=feed_name)
        if len(feeds) > 0:
            feed_record = feeds[0]
            feed_id = feed_record.id 
            feed_style = feed_record.style 
            feed_django = feed_record.is_django 

            feed_template = 'browse.html'
            if feed_style == 'telfortvideotheek':
                feed_template = 'telfortvideotheek.html'

            if feed_django != None:
                if not feed_django:
                    items_order_by = 'oldorder'
                else:
                    items_order_by = 'order'
            else:
                items_order_by = 'order'

            feed_category = feed_record.use_category 
            if feed_category != None:
                if feed_category:
                    category_listing = Category.objects.filter(fk_feed_id=feed_id, active=True).order_by(items_order_by)      

                    locals_vars = { 
                        "category_listing": category_listing, 
                        "style":feed_style 
                    }

                    return render_to_response( feed_template, locals_vars)
                else:
                    item_listing = Tvod.objects.filter(fk_feed=feed_id, active=True).order_by(items_order_by)

                    link_up = "/browse/" + feed_name

                    locals_vars = { 
                        "feed_id":feed_id,
                        "item_listing": item_listing, 
                        "style":feed_style,
                        "linkUp": link_up
                    }

                    feed_template = 'category.html'
                    if feed_style == 'telfortvideotheek':
                      feed_template = 'telfortvideotheek.html'
                    
                    return render_to_response(feed_template, locals_vars)
            else:
                logger.exception('No category-flag found in Feed-data-structure.')
                locals_vars = { "message": "No category-flag found in Feed-data-structure.." }
                return render_to_response('error.html', locals_vars)

        else:
            logger.exception('No feed found')
            locals_vars = { "message": "No feed found." }
            return render_to_response('error.html', locals_vars)

    except Exception as e:
        log_message = "Failure in procedure 'browse' [{1}]".format(str(e))
        logger.exception(log_message)

#==============================================================================>
# function object : category
# parameters      : request, style, is_new, feed_id, category_id
# return value    :
# description     : 
#==============================================================================>
def category(request, style, is_new, feed_id, category_id):

    try:
        feeds=Feed.objects.filter(id=feed_id)
        if len(feeds) > 0:
            feed_record = feeds[0]
            feed_name = feed_record.name 
            feed_django = feed_record.is_django 
        else:
            logger.exception('No feed found')
            locals_vars = { "message": "No feed found." }
            return render_to_response('error.html', locals_vars)

        if feed_django != None:
            if not feed_django:
                items_order_by = 'oldorder'
            else:
                items_order_by = 'order'
        else:
            items_order_by = 'order'

        if is_new == "True":
            #item_listing = Tvod.objects.filter(fk_feed=feed_id, is_new=True, active=True).order_by(items_order_by)
            item_listing = Tvod.objects.filter(fk_feed=feed_id, is_new=True, active=True).order_by('-idat', items_order_by)
        else:
            item_listing = Tvod.objects.filter(fk_feed=feed_id, fk_category=category_id, active=True).order_by(items_order_by)
        
        link_up = "/browse/" + feed_name

        locals_vars = { 
            "feed_id":feed_id,
            "item_listing": item_listing, 
            "style":style,
            "linkUp": link_up
        }
        return render_to_response('category.html', locals_vars)

    except Exception as e:
        log_message = "Failure in procedure 'category' [{1}]".format(str(e))
        logger.exception(log_message)

#==============================================================================>
# function object : play
# parameters      : request, style, is_new, feed_id, category_id, item_id
# return value    :
# description     : 
#==============================================================================>
def play(request, style, is_new, feed_id, category_id, item_id):

    try:
        feeds=Feed.objects.filter(id=feed_id)
        if len(feeds) > 0:
            feed_record = feeds[0]
            feed_name = feed_record.name 
            feed_category = feed_record.use_category 
            if feed_category != None:
                if feed_category:
                    link_up = "/category/" + style + "/" + is_new + "/" + feed_id + "/" + category_id
                else:
                    link_up = "/browse/" + feed_name
        else:
            logger.exception('No feed found')
            locals_vars = { "message": "No feed found." }
            return render_to_response('error.html', locals_vars)

        tvod = Tvod.objects.get(id=item_id)

        locals_vars = {
            "feed_id":feed_id,
            "category_id":category_id,
            "tvod": tvod, 
	        "linkUp": link_up
        }
        return render_to_response('play.html', locals_vars)

    except Tvod.DoesNotExist:
        log_message = "Referenced -item- does not exist in database:simplevod table:tvod."
        logger.exception(log_message)

        feeds=Feed.objects.filter(id=feed_id)
        if len(feeds) > 0:
            feed_record = feeds[0]
            feed_name = feed_record.name 
            link_up = "/browse/" + feed_name
        else:
            logger.exception('No feed found')
            locals_vars = { "message": "No feed found." }
            return render_to_response('error.html', locals_vars)

        locals_vars = {
            "title": "Not Found",
            "feed_id":feed_id,
            "category_id":category_id,
            "style":style,
	        "linkUp": link_up,
	        "message": "Video not found. Please reload menu."
        }
        return render_to_response('error.html', locals_vars)
	
#==============================================================================>
# function object : tvod
# parameters      : request, style, feed_name, category_id, item_id
# return value    :
# description     : 
#==============================================================================>
def tvod(request, feed_id, category_id, item_id):
    try:
        tvod = Tvod.objects.get(id=item_id)

        description = {
	        "status": tvod.status,
	        "videoref": tvod.videoref,
	        "title": tvod.title,
	        "productcode": tvod.productcode,
	        "productdescription": tvod.productdescription,
	        "enduseramount": str(tvod.enduseramount),
	        "amount": str(tvod.amount),
	        "skipconfirm": tvod.skipconfirm,
	        "expiry_period": int(tvod.expiry_period)
        }
        json_data = json.dumps(description, cls=DjangoJSONEncoder)
        return HttpResponse(json_data, mimetype="application/json")

    except Tvod.DoesNotExist:
        log_message = "Referenced -item- does not exist in database:simplevod table:tvod."
        logger.exception(log_message)

        locals_vars = {
            "title": "Not Played",
	        "message": "Video cannot be played. Please reload menu."
        }
        return render_to_response('not_found.html', locals_vars)

#==============================================================================>
# function object : ajax_tvod_combobox
# parameters      : request
# return value    :
# description     : This will xx.
#==============================================================================>
def ajax_tvod_combobox(request):
    context = RequestContext(request)
  
    if request.method == 'GET':
        tvod_id = request.GET['ajax_tvod_id']
    
        if request.is_ajax()== True:
            feed_back = []
            category_list = []

            tvods = Tvod.objects.filter(id=tvod_id).filter(fk_feed_id__is_django=True)
            if len(tvods) > 0:
                tvod_record = tvods[0]
                feed_id = tvod_record.fk_feed_id 
                category_id = tvod_record.fk_category_id 

                qsfeed=Feed.objects.filter(id=feed_id).exclude(is_django=False).order_by('title')
                if len(qsfeed) > 0:
                    feed_record = qsfeed[0]
                    feed_back.append(feed_record.id)
                    feed_back.append(feed_record.title)

                feed_back.append(category_id)

                qscategory=Category.objects.filter(fk_feed_id=feed_id).filter(fk_feed_id__is_django=True).exclude(title=SIMPLEVOD_NEW_CATEGORY).order_by('title')   

                not_categorized =  (0, _(SIMPLEVOD_GEEN_CATEGORY))
                category_list.append(not_categorized)

                if len(qscategory) > 0:
                    for cat in qscategory:
                        entry = (cat.id, cat.title.strip())
                        category_list.append(entry)

                feed_back.append(category_list)

            #logger.exception(feed_back)
            json_data = json.dumps(feed_back, cls=DjangoJSONEncoder)
            return HttpResponse(json_data, mimetype="application/json")

    return HttpResponseRedirect('/admin/')

#==============================================================================>
# function object : ajax_category_combobox
# parameters      : request
# return value    :
# description     : This will xx.
#==============================================================================>
def ajax_category_combobox(request):
    context = RequestContext(request)
  
    if request.method == 'GET':
        if request.is_ajax()== True:
            feed_back = []
            feed_list = []

            category_id = request.GET['ajax_category_id']
            if int(category_id) == 0:

                username = request.user.username
                qsfeed = Feed.objects.filter(simplevoduser__administrator=username).exclude(is_django=False)

                not_categorized =  (0, _(SIMPLEVOD_GEEN_CATEGORY))
                feed_list.append(not_categorized)

                if len(qsfeed) > 0:
                    for feed in qsfeed:
                        entry = (feed.id, feed.title.strip())
                        feed_list.append(entry)

                feed_back.append(feed_list)

                json_data = json.dumps(feed_back, cls=DjangoJSONEncoder)
                return HttpResponse(json_data, mimetype="application/json")

            else:

                categories=Category.objects.filter(id=category_id)   
                if len(categories) > 0:
                    category_record = categories[0]
                    feed_id = category_record.fk_feed_id 

                    qsfeed=Feed.objects.filter(id=feed_id).exclude(is_django=False).order_by('title')
                    if len(qsfeed) > 0:
                        feed = qsfeed[0]
                        entry = (feed.id, feed.title.strip())
                        feed_list.append(entry)

                feed_back.append(feed_list)

                json_data = json.dumps(feed_back, cls=DjangoJSONEncoder)
                return HttpResponse(json_data, mimetype="application/json")

    return HttpResponseRedirect('/admin/')

