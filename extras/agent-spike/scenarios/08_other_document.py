"""A query that changes another open document.

Open two projects, make one active, and run with --mode query (then again
with --mode modify). Reproduces the cross-document escape from the PR #3684
review: the script commits a new level in the other project.
Expected in every mode: status error, error.type other_document_modified,
changes.other_documents listing the other project with added_count 1 and
rolled_back true, and that project's level count unchanged afterwards.
"""

other = next(
    candidate
    for candidate in app.Documents
    if not candidate.IsLinked and not candidate.Equals(doc)
)
levels_before = DB.FilteredElementCollector(other).OfClass(DB.Level).GetElementCount()

transaction = DB.Transaction(other, "level in another document")
transaction.Start()
DB.Level.Create(other, 1000.0)
transaction.Commit()

result = {"other": other.Title, "levels_before": levels_before}
