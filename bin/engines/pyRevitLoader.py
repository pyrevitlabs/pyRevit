# -*- coding: utf-8 -*-
#pylint: disable=C0103,W1401,E0401,E0602
"""
   ██▓███▓██   ██▓ ██▀███  ▓█████ ██▒   █▓ ██▓▄▄▄█████▓
  ▓██░  ██▒██  ██▒▓██ ▒ ██▒▓█   ▀▓██░   █▒▓██▒▓  ██▒ ▓▒
  ▓██░ ██▓▒▒██ ██░▓██ ░▄█ ▒▒███   ▓██  █▒░▒██▒▒ ▓██░ ▒░
  ▒██▄█▓▒ ▒░ ▐██▓░▒██▀▀█▄  ▒▓█  ▄  ▒██ █░░░██░░ ▓██▓ ░
  ▒██▒ ░  ░░ ██▒▓░░██▓ ▒██▒░▒████▒  ▒▀█░  ░██░  ▒██▒ ░
  ▒▓▒░ ░  ░ ██▒▒▒ ░ ▒▓ ░▒▓░░░ ▒░ ░  ░ ▐░  ░▓    ▒ ░░
  ░▒ ░    ▓██ ░▒░   ░▒ ░ ▒░ ░ ░  ░  ░ ░░   ▒ ░    ░
  ░░      ▒ ▒ ░░    ░░   ░    ░       ░░   ▒ ░  ░
          ░ ░        ░        ░  ░     ░   ░
          ░ ░                         ░
This is the starting point for pyRevit. At Revit loads the PyRevitLoader.dll
 addon at startup. This dll then creates an ironpython engine and runs
 pyRevitLoader.py (this script). It's the job of this script to setup the
 environment for the pyrevit module (pyrevitlib\pyrevit) and load a new pyRevit
 session. This script needs to add the directory path of the pyrevit lib folder
 so the pyrevit module can be imported and used.
"""

import sys
import os.path as op

# add the library location to the system search paths
repo_path = op.dirname(op.dirname(op.dirname(__file__)))
sys.path.append(op.join(repo_path, 'pyrevitlib'))

# now pyrevit can be imported
from pyrevit.loader import sessionmgr

# ask sessionmgr to start a new session
sessionmgr.load_session()
