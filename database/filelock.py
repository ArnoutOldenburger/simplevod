#!/usr/bin/python
import os
import os.path

import time
import datetime

from datetime import datetime, date, timedelta

ERRNO_EEXIST = 17

#==============================================================================>
# class object    : FileLock
# parameters      : filename
# return value    : 
# description     : 
#==============================================================================>
class FileLock:
    def __init__(self, filename):
        self.filename = filename
        self.fd = None
        self.pid = os.getpid()

    def acquire(self):
        try:
            self.fd = os.open(self.filename, os.O_CREAT|os.O_EXCL|os.O_RDWR)
            os.write(self.fd, "%d" % self.pid)
            return 1  
            
        except OSError as e:
            if e.errno == ERRNO_EEXIST:
                datetime_now = datetime.now()
                delta_time = timedelta(hours=1)
                datetime_threshold = datetime_now - delta_time
                creation_time = os.path.getctime(self.filename)
                creation_timestamp = datetime.fromtimestamp(creation_time)
                if(creation_timestamp < datetime_threshold):
                    os.remove(self.filename)

            self.fd = None
            return 0

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

