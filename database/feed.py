#!/usr/bin/python
import os
import sys

import json
import urllib
import time
import datetime
import urllib
import urllib2

base = "/srv/simplevod/"
sys.path.append(os.path.join(base, 'pyld', 'lib'))

from pyld import jsonld
from pprint import pprint

#==============================================================================>
# class object    : Feed
# parameters      : name, url, style (from json-config file).
# return value    : data object with json-linked-data.
# description     : Loads, parses and updates json-linked-data.
#==============================================================================>
class Feed(object):

    jsonld_ctx = {
        "@context": {                                                                 
            "@vocab": "http://www.ebu.ch/metadata/ontologies/ebucore/ebucore#",         
            "videodb": "http://zt6.nl/2013/videodb#",                                   
            "simplevod": "http://zt6.nl/2013/simplevod#"                                
        }
    }                                                                             

    def __init__(self, feed_meta):
        self.config = feed_meta
        self.title = None
        self.lastUpdate = None
        self.ttl = 20000
        self.categories = []
        self.map = {}
        
        self.fetch()

        ticks = time.time()
        javascript_time = long(ticks * 1000)
        self.lastUpdate = javascript_time

    def fetch(self):
        if 'etag' in self.config.keys():
            self.etag = self.config["etag"]


        if 'url' in self.config.keys():
            self.base = self.config["url"]

            #==============================================================================>
            # Request object that specifies the URL you want to fetch. Calling urlopen with 
            # this Request object returns a response object for the URL requested. 
            #==============================================================================>
            req = urllib2.Request(self.base)

            if hasattr(self, "etag"):
                req.add_header("If-None-Match", self.etag)

            #==============================================================================>
            # Create opener object and add several handlers by default.
            #==============================================================================>
            try:
                opener = urllib2.build_opener(NotModifiedHandler())
                uh = opener.open(req)

            except Exception as e:
                raise Exception(
                    "Could not open URL: '{0}'".format(e))

            if uh.info().get("ETag"):
                self.etag = uh.info().get("ETag")

            if not hasattr(uh, "code") or uh.code != 304:
                self.feed = json.loads(uh.read())
                self.parse()

            uh.close()

    def parse(self):
        try:
            jsonld_flat = jsonld.flatten(
                self.feed,Feed.jsonld_ctx,{"base":self.base}
            )
        except Exception as e:
            raise Exception(
                "Could not flatten JSON-LD for feed: '{0}' [{1}]".format(
                self.base,
                str(e)
                )
            )

        for node in jsonld_flat["@graph"]:
            if self.hasType(node, "simplevod:SimpleVoD"):
                self.title = node["title"]
                if (
                    "hasMemberGroup" in node and
                    "@list" in node["hasMemberGroup"]
                ):
                    for group in node["hasMemberGroup"]["@list"]:
                        self.categories.append(self.get(group["@id"]))
            elif self.hasType(node, "simplevod:SimpleVoDCategory"):
                category = self.get(node["@id"])
                category.update({
                    "isCategory": True,
                    "title": node["title"],
                    "items": []
                })
                if "hasMember" in node and "@list" in node["hasMember"]:
                    for item in node["hasMember"]["@list"]:
                        category["items"].append(self.get(item["@id"]))
            elif self.hasType(node, "TVProgramme"):
                item = self.get(node["@id"])
                item.update({
                    "isItem": True,
                    "title": node["title"],
                    "video": self.get(node["isInstantiatedBy"]["@id"]),
                    "productcode": node["videodb:productcode"]
                })
            elif self.hasType(node, "MediaResource"):
                video = self.get(node["@id"])
                video.update({
                    "videoref": node["videodb:videoref"]
                })

    def get(self, id):
        if (not id in self.map):
            self.map[id] = {"@id" :id}
        return self.map[id]

    def getCategory(self, id):
        for d in self.getCategories():
            if "@id" in d and d["@id"] == id:
                return d
        return {}

    def getCategories(self):
        return(self.categories)

    def getItem(self, id):
        for d in self.getItems():
            if "@id" in d and d["@id"] == id:
                return d
        return {}

    def getItems(self):
        return filter(None, map(
            lambda k: "isItem" in self.map[k] and self.map[k],
            self.map)
        )

    def getTitle(self):
        return(self.title)

    def getURL(self):
        return(self.config["url"])

    def getStyle(self):
        return(self.config["style"])

    def hasType(self, node, type):
        if isinstance(node["@type"], list):
            return(type in node["@type"])
        else:
            return(type == node["@type"])

#==============================================================================>
# class object    : NotModifiedHandler
# parameters      : 
# return value    : 
# description     : 
#==============================================================================>
class NotModifiedHandler(urllib2.BaseHandler):
      
    def http_error_304(self, req, fp, code, message, headers):
        add_info_url = urllib2.addinfourl(fp, headers, req.get_full_url())
        add_info_url.code = code
        return(add_info_url)

