"""Create two identical walls to trigger an overlap warning.

Run with --mode dry_run. Verifies FailuresProcessing capture inside the run.
Expected: failures[] contains a Warning about overlapping walls, no warning
dialog appears in Revit, changes.added_count >= 2, then everything is rolled back.
"""

level = DB.FilteredElementCollector(doc).OfClass(DB.Level).FirstElement()
line = DB.Line.CreateBound(DB.XYZ(0, 0, 0), DB.XYZ(20, 0, 0))

transaction = DB.Transaction(doc, "Overlapping walls")
transaction.Start()
first = DB.Wall.Create(doc, line, level.Id, False)
second = DB.Wall.Create(doc, line, level.Id, False)
status = transaction.Commit()

result = {"walls": [first.Id, second.Id], "commit_status": str(status)}
