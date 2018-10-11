"""Clear tag information from selected elements."""
#pylint: disable=C0111,E0401,C0103,W0613

from pyrevit import revit
from pyrevit import forms
from pyrevit import script

import tagscfg
import tagsmgr


__author__ = '{{author}}'


logger = script.get_logger()


if not forms.check_selection():
    script.exit()

selection = revit.get_selection()
if forms.alert('Are you sure you want to delete tag information from {} '
               'selected elements?'.format(len(selection)),
               yes=True, no=True):
    # make sure tag param is setup correctly
    tagscfg.ensure_tag_param()
    # now cleanup
    with revit.Transaction('Clear tags on selection'):
        tagsmgr.clear_tags(elements=selection)
