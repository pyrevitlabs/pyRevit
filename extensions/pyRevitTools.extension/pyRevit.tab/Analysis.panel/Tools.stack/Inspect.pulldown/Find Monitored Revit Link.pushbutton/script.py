"""List Revit link that is being monitored by selected element(s)."""

from pyrevit import revit, DB
from pyrevit import script


__context__ = 'selection'


output = script.get_output()

for element in revit.get_selection():
    linkels = element.GetMonitoredLinkElementIds()
    if linkels:
        for linkelid in linkels:
            linkel = revit.doc.GetElement(linkelid)
            if isinstance(linkel, DB.RevitLinkInstance):
                clink = output.linkify(element.Id)
                print('{} : {}'.format(clink, linkel.Name))
