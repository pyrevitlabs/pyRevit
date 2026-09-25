"""Start a transaction and never close it.

Run with --mode dry_run. Probes an edge case the plan leaves open: what Revit
does when the ExternalEvent callback returns with a transaction still open.
Expected: status error, error.type transaction_left_open. Record whether Revit
shows its own "transaction not closed" message, and confirm the model is unchanged.
"""

transaction = DB.Transaction(doc, "Never closed")
transaction.Start()
doc.GetElement(uidoc.ActiveView.Id).Name
