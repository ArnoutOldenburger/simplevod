#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    # switch between development and production mode by commenting out one
    # of the following statements and effectuating the other.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "simplevod.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
