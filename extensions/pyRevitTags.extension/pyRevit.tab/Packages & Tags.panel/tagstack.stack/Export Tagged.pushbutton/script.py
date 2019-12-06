"""Manage sheet packages."""
#pylint: disable=C0111,E0401,C0103,W0613,W0703
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

import tagscfg
import tagsmgr


__author__ = "{{author}}"

logger = script.get_logger()
output = script.get_output()


# make sure doc is not family
forms.check_modeldoc(doc=revit.doc, exitscript=True)

if tagscfg.verify_tags_configs():
    forms.inform_wip()
else:
    forms.alert('Tags tools need to be configured before using. '
                'Click on the Tags Settings button to setup.')
