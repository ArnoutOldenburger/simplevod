from __future__ import unicode_literals
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.auth.backends import ModelBackend

from django.contrib.auth.models import User, check_password

from simplevod.models import AuthUser

from django.core.exceptions import ValidationError
from django import forms

# For more information on logging refer to https://docs.djangoproject.com/en/dev/topics/logging/
# Write to logfile with statements like (for debug-level logging):logger.debug("launch site")
import logging
logger = logging.getLogger('svod')

# The next statement will disable all logging calls less severe than ERROR
# Comment this next satement to see more logging.
#logging.disable(logging.ERROR)
logging.disable(logging.DEBUG)

class ModelBackend(ModelBackend):

    def authenticate(self, username=None, password=None):
        # Check the username/password and return a User.

        try:
            authUser = AuthUser.objects.get(username=username)
            valid = check_password(password, authUser.password)
            if not valid:
                raise forms.ValidationError("Password Incorrect")
            
        except AuthUser.DoesNotExist:
            log_message = "AuthUser object is not found for the given parameters of the query."
            logger.exception(log_message)
            raise forms.ValidationError("UserProfile was not found")

        authUser.is_staff = True
        authUser.is_superuser = True
        authUser.save()
        return authUser

    def clean_username(self, username):
        """
        Performs any cleaning on the "username" prior to using it to get or
        create the user object.  Returns the cleaned username.

        By default, returns the username unchanged.
        """
        return username

    def configure_user(self, user):
        """
        Configures a user after creation and returns the updated user.

        By default, returns the user unmodified.
        """
        return user

