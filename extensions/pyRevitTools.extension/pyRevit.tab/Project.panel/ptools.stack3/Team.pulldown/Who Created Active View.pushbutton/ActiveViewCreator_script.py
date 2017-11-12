"""Shows the creator of the active view.

Copyright (c) 2017 Frederic Beaupere
github.com/frederic-beaupere

--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2017 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""


__author__ = 'Frederic Beaupere'
__contact__ = 'https://github.com/frederic-beaupere'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = """Shows the creator of the active view."""


from pyrevit import revit, DB

active_view = revit.activeview
view_id = active_view.Id.ToString()
view_name = active_view.Name
view_creator = \
    DB.WorksharingUtils.GetWorksharingTooltipInfo(revit.doc,
                                                  active_view.Id).Creator

print("Creator of the current view: " + view_name)
print("with the id: " + view_id)
print("is: " + view_creator)
