"""Raise after writing, to check error rollback and traceback quality.

Run with --mode modify.
Expected: no approval dialog, status error, decision rolled_back,
error.traceback pointing at line 21 of <agent-script> with the source line shown.
"""

wall = (
    DB.FilteredElementCollector(doc)
    .OfClass(DB.Wall)
    .WhereElementIsNotElementType()
    .FirstElement()
)
transaction = DB.Transaction(doc, "Write then fail")
transaction.Start()
wall.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set(
    "should be rolled back"
)
transaction.Commit()
print("about to fail")
raise ValueError("deliberate failure after a committed transaction")
