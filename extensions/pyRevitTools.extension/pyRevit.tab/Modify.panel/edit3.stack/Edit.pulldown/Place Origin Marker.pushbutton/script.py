"""Place a cross marker at the true 0,0,0 origin."""
#pylint: disable=C0103,E0401,C0111,W0703
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


# makr a cross shape
line1 = DB.Line.CreateBound(DB.XYZ(-1, -1, 0), DB.XYZ(1, 1, 0))
line2 = DB.Line.CreateBound(DB.XYZ(1, -1, 0), DB.XYZ(-1, 1, 0))
# place lines on active view
try:
    with revit.Transaction('Place Origin Marker', log_errors=False):
        if revit.doc.IsFamilyDocument:
            revit.doc.FamilyCreate.NewDetailCurve(revit.active_view, line1)
            revit.doc.FamilyCreate.NewDetailCurve(revit.active_view, line2)
        else:
            revit.doc.Create.NewDetailCurve(revit.active_view, line1)
            revit.doc.Create.NewDetailCurve(revit.active_view, line2)
except Exception as ex:
    forms.alert("You are not on a plan view.", sub_msg=str(ex))
