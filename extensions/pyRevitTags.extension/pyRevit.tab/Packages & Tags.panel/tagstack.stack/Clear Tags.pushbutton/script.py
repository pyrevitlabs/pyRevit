"""Clear tag information from selected elements."""
#pylint: disable=C0111,E0401,C0103,W0613

from pyrevit import revit
from pyrevit import forms
from pyrevit import script

import tagscfg
import tagsmgr


__author__ = '{{author}}'


logger = script.get_logger()


# make sure doc is not family
forms.check_modeldoc(doc=revit.doc, exitscript=True)

if tagscfg.verify_tags_configs():
    if not forms.check_selection():
        script.exit()

    selection = revit.get_selection()
    if forms.alert('Are you sure you want to delete tag information from {} '
                   'selected elements?'.format(len(selection)),
                   yes=True, no=True):
        # cleanup
        with revit.Transaction('Clear tags on selection'):
            tagsmgr.clear_tags(elements=selection)
else:
    forms.alert('Tags tools need to be configured before using. '
                'Click on the Tags Settings button to setup.')
