#!/usr/bin/python
#==============================================================================>
# script title    : UploadSuperuser.py
# description     : Fills table that couples user to feed with an initial superuser account.
# author          : a.oldenburger
# date            : 27-01-2013
# version         : 0.1
# usage           : Script used with KPN/GHM Simplevod. 
# notes           :
# python_version  : @home v2.7.2
#==============================================================================>
import os
import sys
import time
import datetime

#from datetime import datetime
from django.utils import timezone

PROJECT_DIR = os.path.realpath(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, os.path.dirname(PROJECT_DIR))
sys.path.insert(0, os.path.join(os.path.dirname(PROJECT_DIR), "simplevod"))

from django.core.management import setup_environ
from simplevod import settings
setup_environ(settings)

from django.contrib.auth.hashers import (check_password, make_password, is_password_usable)

from django.db import models
from simplevod.models import AuthUser, AuthUserUserPermissions
 
from getpass import getpass

SIMPLEVOD_ADMIN_SUPER_USER = "simplevod"
SIMPLEVOD_DESCR_SUPER_USER = "this is the - on installation - superuser account"
ASK_SUPER_USER_NAME = "By default the superuser name is 'simplevod'. Do you like to change this ?"
TELL_SUPER_USER_NAME = "Superuser has kept its default name 'simplevod'"

#==============================================================================>
# class object    : User
# parameters      : 
# return value    : 
# description     : 
#==============================================================================>
class User:

    def __init__(self):
        self.name = SIMPLEVOD_ADMIN_SUPER_USER
        self.password = 'simplevod'

    def getSuperUserName(self):
        question = " Enter your name for the superuser: "
        while True:
            sys.stdout.write(question)

            superuser = raw_input()
            superuser = superuser.strip()
            if len(superuser) > 0:
                self.name = superuser
                return 
            else:
                sys.stdout.write("  Superuser name can not be zero length. \n")

    def getSuperUserPassword(self):
        while True:
            _pass = getpass(' Enter your superuser password: ')
            _pass = _pass.strip()
            if len(_pass) > 0:
                self.password = make_password(_pass)
                return 
            else:
                sys.stdout.write("  Superuser password can not be zero length. \n")

    def insertSuperUserAndPermissions(self):
 
        try:
            username = AuthUser.objects.get(username=self.name)
            sys.stdout.write("Username '%s' is already in use.\n" % self.name)
            return 
        except AuthUser.DoesNotExist:
            username = None
        
        new_user = AuthUser()
        new_user.password = self.password
        new_user.last_login = timezone.localtime(timezone.now())    
        new_user.is_superuser = True
        new_user.username = self.name
        new_user.first_name = '' 
        new_user.last_name = ''
        new_user.email = ''
        new_user.is_staff = True
        new_user.is_active = True
        new_user.date_joined = timezone.localtime(timezone.now())
        new_user.save()

        try:
            username = AuthUser.objects.get(username=self.name)
        except AuthUser.DoesNotExist:
            sys.stdout.write("Username '%s' adding permissions failed.\n" % self.name)
            return 
        
        new_permissions = AuthUserUserPermissions()

        try:
            new_id = AuthUserUserPermissions.objects.latest('id').id
        except AuthUserUserPermissions.DoesNotExist:
            new_id = 0

        new_id += 1

        new_permissions.id = new_id 
        new_permissions.user_id = username.id
        new_permissions.permission_id = 7
        new_permissions.save()

        new_permissions = AuthUserUserPermissions()
        new_id += 1
        new_permissions.id = new_id 
        new_permissions.user_id = username.id
        new_permissions.permission_id = 8
        new_permissions.save()

        new_permissions = AuthUserUserPermissions()
        new_id += 1
        new_permissions.id = new_id 
        new_permissions.user_id = username.id
        new_permissions.permission_id = 9
        new_permissions.save()

        sys.stdout.write("Superuser '%s' has been added to the database .\n" % self.name)
        return 

#==============================================================================>
# function object : query_yes_no
# parameters      : none
# return value    : 
# description     : Ask a question
#==============================================================================>
def query_yes_no(question, default="no"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True, "y":True, "ye":True, "no":False, "n":False}

    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")

#==============================================================================>
# function object : main
# parameters      : none
# return value    : none
# description     : xx.
#==============================================================================>
def main():
    print 'Starting script:UploadSuperuser.'    

    settings.DATABASES['default']['HOST'] = 'localhost'

    userObject = User()

    superuser = SIMPLEVOD_ADMIN_SUPER_USER
    if query_yes_no(ASK_SUPER_USER_NAME):
        userObject.getSuperUserName()   
    else:
        print TELL_SUPER_USER_NAME

    userObject.getSuperUserPassword()   
    
    userObject.insertSuperUserAndPermissions()   
    
    settings.DATABASES['default']['HOST'] = ''

#==============================================================================>
# Call main function. 
#==============================================================================>
if __name__ == '__main__':
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simplevod.settings")
    main()

