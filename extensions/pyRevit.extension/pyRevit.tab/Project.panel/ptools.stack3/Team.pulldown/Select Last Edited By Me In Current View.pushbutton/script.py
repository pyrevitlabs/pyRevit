'''
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
'''
__doc__ = 'Uses the Worksharing tooltip to find out the element "last edited" by the user in the current view.' \
          'If current view is a sheet, the tools searches all the views placed on this sheet as well.' \
          '"Last Edited" elements are elements last edited by the user, and are different from borrowed elements.' \

__window__.Close()

from Autodesk.Revit.DB import WorksharingUtils, ElementId, FilteredElementCollector, ViewSheet
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI.Selection import ISelectionFilter
from System.Collections.Generic import List


uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

filteredlist = []
viewlist = []

if doc.IsWorkshared:
    currentviewid = uidoc.ActiveGraphicalView.Id
    viewlist.append(currentviewid)
    if isinstance(uidoc.ActiveGraphicalView, ViewSheet):
        vportids = uidoc.ActiveGraphicalView.GetAllViewports()
        for vportid in vportids:
            viewlist.append(doc.GetElement(vportid).ViewId)
    for view in viewlist:
        curviewelements = FilteredElementCollector(doc).OwnedByView(view).WhereElementIsNotElementType().ToElements()
        if len(curviewelements) > 0:
            for el in curviewelements:
                wti = WorksharingUtils.GetWorksharingTooltipInfo(doc, el.Id)
                # wti.Creator, wti.Owner, wti.LastChangedBy
                if wti.LastChangedBy == __revit__.Application.Username:
                    filteredlist.append(el.Id)
            uidoc.Selection.SetElementIds(List[ElementId](filteredlist))
    else:
        pass
else:
    TaskDialog.Show('pyrevit','Model is not workshared.')