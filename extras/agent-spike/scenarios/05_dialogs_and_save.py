"""Show a TaskDialog and try to save the document.

Run with --mode query. Verifies DialogBoxShowing capture and save blocking.
Expected: no dialog stays open in Revit, dialogs[] lists the TaskDialog,
blocked[] lists "save" (for a saved document), and result.save_error holds
the exception raised by the cancelled save.
"""

dialog_result = UI.TaskDialog.Show(
    "pyRevit agent spike", "This dialog should be dismissed automatically."
)

save_error = None
try:
    doc.Save()
except Exception as ex:
    save_error = str(ex)

result = {"dialog_result": str(dialog_result), "save_error": save_error}
