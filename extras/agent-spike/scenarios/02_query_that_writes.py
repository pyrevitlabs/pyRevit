"""A query that changes the model anyway.

Run with --mode query. Verifies that DocumentChanged fires for a transaction
committed inside the run's TransactionGroup.
Expected: status error, error.type query_modified_model, changes.modified_count
>= 1, and the wall's Comments unchanged in Revit afterwards.
"""

wall = (
    DB.FilteredElementCollector(doc)
    .OfClass(DB.Wall)
    .WhereElementIsNotElementType()
    .FirstElement()
)
comments = wall.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)

transaction = DB.Transaction(doc, "sneaky write")
transaction.Start()
comments.Set("written by a query")
transaction.Commit()

result = {"wall": wall.Id}
