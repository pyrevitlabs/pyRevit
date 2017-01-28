"""
This is the starting point for pyRevit. At host startup, host loads the
 PyRevitLoader.dll addon. This dll then creates an ironpython engine and runs
 pyRevitLoader.py (This script). It's the job of this script to setup the
 environment for the pyrevit module (lib\pyrevit) and load a new pyRevit
 session. This script needs to add the directory path of the pyrevit lib folder
 so the lib\pyrevit module can be imported and used.

>>> from pyrevit.loader.sessionmgr import load_session
>>> load_session()     # start loading a new pyRevit session
"""

import sys
import os.path as op

# add the library location to the system search paths
sys.path.append(op.dirname(op.dirname(op.dirname(op.dirname(__file__)))))

# now pyrevit can be imported
from pyrevit.loader.sessionmgr import load_session

# start a new session 
load_session()
