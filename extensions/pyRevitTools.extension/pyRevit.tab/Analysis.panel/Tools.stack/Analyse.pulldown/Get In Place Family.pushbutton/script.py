"""Get a total count and types of In Place Family in the current document.
Also isolate them in a new 3Dview called InPlace Families.

Copyright (c) 2021 Jean-Marc Couffin
https://github.com/jmcouffin
"""
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import clr

clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import * #use ElementId
from System.Collections.Generic import * #use LIST
from pyrevit import revit, DB, HOST_APP
from pyrevit import script

output = script.get_output()

# Close other output when launched several times
close_other_output = output.close_others(all_open_outputs=True)

# Collect family instances
familyinstance_collector = DB.FilteredElementCollector(revit.doc)\
                             .OfClass(DB.FamilyInstance)\
                             .WhereElementIsNotElementType()\
                             .ToElements()
                             
# filter inplace families
inplace_families = [
    x for x in familyinstance_collector
    if x.Symbol and x.Symbol.Family and x.Symbol.Family.IsInPlace
    ]

# make a iCollection of inplace families
inplace_families_toIsolate = List[ElementId](i.Id for i in inplace_families)

print('Found {} in-place families'.format(len(inplace_families)))

print('\nCATEGORY & FAMILY NAME')
report = []
for inplace_family in inplace_families:
    inplace_family_type = revit.doc.GetElement(inplace_family.GetTypeId())
    if inplace_family_type:
        category_name = inplace_family_type.Category.Name
        family_name = inplace_family.Symbol.Family.Name
        print(
            '{} category:\"{}\"  name:\"{}\"'.format(
                output.linkify(inplace_family.Id),
                category_name,
                family_name
            ))

# based on isolate function in pyRevit
with revit.TransactionGroup("InPlace Families"):
    with revit.Transaction("Reset temporary hide/isolate"):
        newview = revit.db.create.create_3d_view('InPlace Families')#active_view
        # reset temporary hide/isolate before filtering elements
        newview.DisableTemporaryViewMode(
            DB.TemporaryViewMode.TemporaryHideIsolate
        )
    with revit.Transaction("Isolate"):
        # isolate them in the newly created view
        newview.IsolateElementsTemporary(inplace_families_toIsolate)

#Make newly created view active
HOST_APP.uidoc.RequestViewChange(newview)