"""Lists keynotes that have not been used in this model."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


usedkeynotes = set()
keynotes = DB.FilteredElementCollector(revit.doc)\
             .OfCategory(DB.BuiltInCategory.OST_KeynoteTags)\
             .WhereElementIsNotElementType()\
             .ToElements()

for knote in keynotes:
    usedkeynotes.add(knote.TagText)

allkeynotes = set()
kt = DB.KeynoteTable.GetKeynoteTable(revit.doc)
entries = kt.GetKeyBasedTreeEntries()

if not entries:
    forms.alert('There are no keynotes set for this model.')
else:
    for knote in kt.GetKeyBasedTreeEntries():
        allkeynotes.add(knote.Key)

    unusedkeynotes = allkeynotes - usedkeynotes

    for knote in sorted(unusedkeynotes):
        print(knote)
