#!/usr/bin/python
import os
import os.path

import time
import datetime

from xmlparse import XmlParse

from lxml import etree

#==============================================================================>
# class object    : XmlParse
# parameters      : filename
# return value    : 
# description     : 
#==============================================================================>
class XmlParse:

    def __init__(self, filename):
        self.filename = filename
        self.fd = None
        self.pid = os.getpid()

    def validate(self):

        try:
            # Get the XML schema to validate against
            schema = lxml.etree.XMLSchema(file = 'http://xmlgw.companieshouse.gov.uk/v2-1/schema/CompanyData-v2-2.xsd')
            # Parse string of XML
            
            xml_doc = lxml.etree.parse(xml)
            # Validate parsed XML against schema returning a readable message on failure
            schema.assertValid(xml_doc)
            # Validate parsed XML against schema returning boolean value indicating success/failure
            print 'schema.validate() returns "%s".' % schema.validate(xml_doc)

        except lxml.etree.XMLSchemaParseError, xspe:
            # Something wrong with the schema (getting from URL/parsing)
            print "XMLSchemaParseError occurred!"
            print xspe

        except lxml.etree.XMLSyntaxError, xse:
            # XML not well formed
            print "XMLSyntaxError occurred!"
            print xse
            
        except lxml.etree.DocumentInvalid, di:
            # XML failed to validate against schema
            print "DocumentInvalid occurred!"

            error = schema.error_log.last_error
            if error:
                # All the error properties (from libxml2) describing what went wrong
                print 'domain_name: ' + error.domain_name
                print 'domain: ' + str(error.domain)
                print 'filename: ' + error.filename # '<string>' cos var is a string of xml
                print 'level: ' + str(error.level)
                print 'level_name: ' + error.level_name # an integer
                print 'line: ' + str(error.line) # a unicode string that identifies the line where the error occurred.
                print 'message: ' + error.message # a unicode string that lists the message.
                print 'type: ' + str(error.type) # an integer
                print 'type_name: ' + error.type_name

    def release(self):
        if not self.fd:
            return 0
        try:
            os.close(self.fd)
            os.remove(self.filename)
            return 1
        except OSError:
            return 0

    def __del__(self):
        self.release()

