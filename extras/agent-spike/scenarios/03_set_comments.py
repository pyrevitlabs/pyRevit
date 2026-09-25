"""Modify Comments on the selected elements, or on the first five walls.

Run with --mode dry_run first, then --mode modify.
Expected dry_run: status ok, decision rolled_back, modified ids listed.
Expected modify: approval dialog in Revit with the elements selected;
"Keep" leaves ONE undo entry named "Agent: <title>", "Discard" leaves the
model untouched and returns status rejected.
"""

text = inputs.get("text", "set by pyRevit agent")

targets = [doc.GetElement(element_id) for element_id in uidoc.Selection.GetElementIds()]
if not targets:
    collector = (
        DB.FilteredElementCollector(doc).OfClass(DB.Wall).WhereElementIsNotElementType()
    )
    targets = list(collector.ToElements())[:5]

changed = []
transaction = DB.Transaction(doc, "Set comments")
transaction.Start()
for element in targets:
    comments = element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)
    if comments and not comments.IsReadOnly:
        comments.Set(text)
        changed.append(element.Id)
transaction.Commit()

result = {"changed": changed}
