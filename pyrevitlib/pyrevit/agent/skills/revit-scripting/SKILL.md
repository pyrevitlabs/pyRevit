---
name: revit-scripting
description: Core Revit API scripting rules for the pyRevit agent runtime. Read before every query, dry run, or model change.
---

# Revit scripting through pyRevit

Read the `pyrevit-library` skill first and use `lookup_pyrevit_api` to find a maintained pyrevitlib or rpw function before writing raw Revit API code. Get context first, inspect the Revit API when uncertain, then run a focused script.

## Workflow

1. Call `get_context` before writing a script. It reports the active document, view, selection, Revit version, policy, and Python engine.
2. Use `inspect_elements` and `lookup_revit_api` to verify types, members, and element ids.
3. Use `run_query` to inspect data. Use `run_modify` with `dry_run=true` before an actual change.
4. Use `get_run` when the immediate response is truncated or reports a persistence warning.

## Runtime contract

- Import APIs with `from pyrevit.api import DB, UI`.
- Only the raw Revit API is available. pyRevit's convenience methods on API types are not applied: use `list(collector)` not `.ToList()`, `get_Parameter(...)` and `Parameter.Set(...)` not `SetParameterValue`, and a collector rather than `doc.Walls`. `__revit__` is a plain `UIApplication`.
- Scripts receive `uiapp`, `app`, `uidoc`, and `doc`. A modifying run requires an active `doc`.
- `run_query` and dry runs roll model changes back. A modify run commits only after its configured policy permits it.
- The rollback covers the active project and documents that were already open. A document the script creates, such as `app.NewFamilyDocument(...)`, or a family from `EditFamily` is outside it: changes there are not rolled back, do not fail a `run_query`, and are discarded if the document is closed without saving. `changes.other_documents` reports them with a `scope` instead of `rolled_back`. The host attempts to close new background documents without saving when the run ends. Check `closed_documents`, `unclosed_documents`, and warnings before assuming a document was closed.
- Open a Revit transaction for every model edit, then commit or roll it back before the script ends.
- The active run blocks save, save-as and synchronize-with-central, and cancels `Document.Export` and `Document.ExportImage` targets outside `export_dir`, a temporary folder the host creates for the run. Export there in any mode; the response lists the files in `exports`. Other APIs that write files, such as `ViewSchedule.Export`, are not checked, so point them at `export_dir` too. Do not rely on the other operations. A script that hits one gets Revit's generic exception, for example "Saving failed", and the response adds an `operation_blocked` warning naming the cancelled operation. An operation Revit does not let the guard cancel is neither blocked nor reported.
- The runtime uses the Windows user's permissions. Revit rollback does not undo Python or .NET file, network, or process side effects.
- Timeouts are cooperative. Avoid unbounded loops and blocking calls. When `get_context` shows `agent.reckless: true` there is no timeout at all, and a script that never ends hangs Revit.

## Query example

```python
from pyrevit.api import DB

walls = DB.FilteredElementCollector(doc)
walls = walls.OfCategory(DB.BuiltInCategory.OST_Walls)
walls = walls.WhereElementIsNotElementType()
result = {"wall_count": walls.GetElementCount()}
```

## Modify example

```python
from pyrevit.api import DB

transaction = DB.Transaction(doc, "Set wall comments")
transaction.Start()
for element_id in uidoc.Selection.GetElementIds():
    wall = doc.GetElement(element_id)
    if wall and wall.Category.Id == DB.ElementId(DB.BuiltInCategory.OST_Walls):
        wall.get_Parameter(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS).Set("Checked")
transaction.Commit()
```

## Results and errors

- Set `result` to JSON-compatible data for structured query output.
- Print concise diagnostics. Large results are truncated in the immediate response.
- Fix `revit_busy`, `document_read_only`, `no_active_document`, `query_modified_model`, `transaction_left_open`, and `other_document_modified` before retrying.
- `revit_busy` means the request was not run and will not run later: it is safe to send again once Revit is idle (a modal dialog such as the save reminder blocks every request until the user answers it). The error's `outcome` says what is known. When it is `unknown` (the connection broke after the request was sent), read the run with `get_run` using the error's `request_id` before sending it again.
- `run_hung` means the script is stuck past its `timeout_s` in a call the timeout can't interrupt (a long Revit API call, `Thread.Sleep`, a printer or window waiting for input). Revit stays busy until that call returns. Ask the user to check Revit, then read the run with `get_run` before sending anything that changes the model again.
