#pylint: disable=C0111,E0401,C0103,W0703
from pyrevit import revit, DB, UI
from pyrevit import forms


__doc__ = 'Run this tool in a sheet view and click on sheet viewports one '\
          'by one and this tool will change the detail number sequentially.'


# verify active view is sheet
curview = revit.active_view
if not isinstance(curview, DB.ViewSheet):
    forms.alert('You must be on a sheet to use this tool.', exitscript=True)

# collect sheet viewports
sheet_vports = []
for vport_id in curview.GetAllViewports():
    sheet_vports.append(revit.doc.GetElement(vport_id))

# find max count for sheet_vports
vports = {}
for vp in sheet_vports:
    detnum_param = vp.Parameter[DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER]
    if detnum_param:
        try:
            detnum = int(detnum_param.AsString())
            vports[detnum] = vp
        except Exception:
            continue

max_num = max(vports.keys())

# renumber
with revit.Transaction('Re-number Viewports'):
    selection = []
    while len(selection) < len(vports):
        try:
            el = revit.doc.GetElement(
                revit.uidoc.Selection.PickObject(
                    UI.Selection.ObjectType.Element
                    )
                )

            if isinstance(el, DB.Viewport):
                selection.append(revit.doc.GetElement(el.ViewId))
        except Exception:
            break

    for i in range(1, len(selection) + 1):
        try:
            vports[i].Parameter[DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER].Set(str(max_num + i))
        except KeyError:
            continue

    for i, el in enumerate(selection):
        el.Parameter[DB.BuiltInParameter.VIEWPORT_DETAIL_NUMBER].Set(str(i + 1))
