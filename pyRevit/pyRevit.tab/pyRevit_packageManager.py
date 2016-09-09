"""
Copyright (c) 2014-2016 Gui Talarico
Written for pyRevit
TESTED API: 2015

----------------------------------------------------------------------------
pyRevit Notice
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at
https://github.com/eirannejad/pyRevit
See this link for a copy of the GNU General Public License
protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__doc__ = "Package Manager for pyRevit. You can install other shared extensions using this tool."
__version__ = "0.3.0"
__author__ = 'Gui Talarico | gtalarico@gmail.com'

import os
import sys
import clr
import re
import shutil
import logging
from pprint import pprint
from collections import defaultdict, OrderedDict

#  Without this it can't find module since
#  Add scripts dir to path so it can find package manager module
THIS_DIR = (os.path.dirname(__file__))
sys.path.append(THIS_DIR)
from pkgManager.config import SCRIPTS_DIR, PYREVIT_DIR
from pkgManager.logger import logger
from pkgManager.winforms import PackageManagerForm
from pkgManager.utils import (load_pgks_from_file, load_pgks_from_origin,
                              get_local_folders,
                              get_local_pgk_version, get_remote_pgk_version,
                              get_local_pkg_ref, get_remote_pkg_ref)


# Uncomment to disable DEBUG - should integrate with pyrevit Debug On/Off
# logger.setLevel(logging.DEBUG)
logger.debug('CWD: {}'.format(os.getcwd()))

clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommandLinkId
from Autodesk.Revit.UI import TaskDialogCommonButtons

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

headers = ['Package', 'Repo', 'Local', 'Description', '', '']

# If fails to get remote,
# packages = load_pgks_from_file()
# packages = load_pgks_from_origin()
packages = load_pgks_from_origin() or load_pgks_from_file()
local_folders = get_local_folders()

# Add Test Suite:
# get_local_pgk_version('pyrevitplus')
# get_local_pkg_ref('pyrevitplus')
# get_remote_pkg_ref('https://github.com/gtalarico/pyrevitplus.git')
# get_remote_pgk_version('https://github.com/gtalarico/pyrevitplus.git')



for package in packages:
    name = package['name']

    package['repo_ref'] = get_remote_pkg_ref(package['url'])
    if name in local_folders:
        package['local_ref'] = get_local_pkg_ref(name)
    else:
        package['local_ref'] = ''

if not packages:
    TaskDialog.Show('Error', 'Could not Load Packages List.')
else:
    pass
    form = PackageManagerForm(packages, headers)
    form.ShowDialog()
    # Application.Run(form)
__window__.Close()
