"""Manual test for output.linkify() ctrl+click append-to-selection.

Select a few elements first (optional), then run this script.
In the output window: plain click a link to replace the selection,
ctrl+click a link to add it to the current selection instead.
"""
from pyrevit import revit, script, DB

output = script.get_output()

element_ids = revit.get_selection().element_ids
if not element_ids:
    element_ids = (
        DB.FilteredElementCollector(revit.doc)
        .WhereElementIsNotElementType()
        .WhereElementIsViewIndependent()
        .ToElementIds()
    )

element_ids = list(element_ids)[:10]

if not element_ids:
    print("No elements found to test with. "
          "Select a few elements first, or open a project with some.")
    script.exit()

print("Plain click a link to select only that element.")
print("Ctrl+click a link to add it to the current selection.\n")

for idx, elid in enumerate(element_ids):
    print('{}: {}'.format(idx + 1, output.linkify(elid)))
