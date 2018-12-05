from pyrevit import revit, DB, UI
from pyrevit import forms


__doc__ = 'Run this tool in a sheet view and click on viewports one '\
          'by one and this tool will change the detail number sequencially.'


# verify active view is sheet
curview = revit.activeview
if not isinstance(curview, DB.ViewSheet):
    forms.alert('You must be on a sheet to use this tool.', exit=True)

# collect viewports
viewports = []
for vpId in curview.GetAllViewports():
    viewports.append(revit.doc.GetElement(vpId))

# find max count for viewports
vports = {int(vp.LookupParameter('Detail Number').AsString()): vp
          for vp in viewports if vp.LookupParameter('Detail Number')}
maxNum = max(vports.keys())

# renumber
with revit.Transaction('Re-number Viewports'):
    sel = []
    while len(sel) < len(vports):
        try:
            el = revit.doc.GetElement(
                revit.uidoc.Selection.PickObject(
                    UI.Selection.ObjectType.Element
                    )
                )

            if isinstance(el, DB.Viewport):
                sel.append(revit.doc.GetElement(el.ViewId))
        except Exception:
            break

    for i in range(1, len(sel) + 1):
        try:
            vports[i].LookupParameter('Detail Number').Set(str(maxNum + i))
        except KeyError:
            continue

    for i, el in enumerate(sel):
        el.LookupParameter('Detail Number').Set(str(i + 1))
