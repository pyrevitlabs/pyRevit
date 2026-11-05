---
name: revit-files
description: Revit file types and working with files. Covers what .rvt, .rte, .rfa and .rft files are, where templates and libraries live, and opening documents. Guarded runs cannot save or export documents. Use it for "open this model", "find the mechanical template", and similar tasks.
---

# Revit files

## File types

| Extension | What it is | Open or create it with |
|---|---|---|
| `.rvt` | A project: the building model, its views and sheets. Also used for central and local models of a workshared project; `Name.0001.rvt` files next to it are backups. | `app.OpenDocumentFile(path)`, or `uiapp.OpenAndActivateDocument(path)` to show it to the user |
| `.rte` | A project template: the starting settings, types, views and families of a new project. | `app.NewProjectDocument(path)` |
| `.rfa` | A loadable family: doors, furniture, equipment, fixtures. | `doc.LoadFamily(path)` to load it into a project; `app.OpenDocumentFile(path)` to read it. A family opened from disk cannot be changed or saved in a guarded run. |
| `.rft` | A family template: fixes the new family's category and how it is hosted. | `app.NewFamilyDocument(path)` |

Text files often travel with them: a type catalog (`Door.txt` next to `Door.rfa`) lists the family's types, a shared parameters file defines parameters shared across families and projects (`app.SharedParametersFilename`), and a keynote file holds keynote text.

**`app.OpenDocumentFile` on a `.rte` opens the template itself, not a new project.** Its `PathName` is the template's path, and saving it would overwrite the template. For a new project, always use `app.NewProjectDocument`.

## Where templates and libraries live

Read the paths from Revit instead of guessing them:

```python
import os

family_templates = app.FamilyTemplatePath
default_project_template = app.DefaultProjectTemplate
libraries = dict(app.GetLibraryPaths())
generic_model = os.path.join(family_templates, "English", "Metric Generic Model.rft")
```

- **Family templates** sit in a language folder under `app.FamilyTemplatePath` (`English`, `English-Imperial`, ...). The name tells the category and the hosting: `Metric Generic Model.rft` is unhosted, and there are `... wall based`, `... face based`, `... ceiling based`, `... floor based`, `... line based` variants, plus templates per category (`Metric Door.rft`, `Metric Electrical Fixture wall based.rft`, `Metric Duct Elbow.rft`, ...). List the folder to see what is installed.
- **Project templates** are under `%ProgramData%\Autodesk\RVT <version>\Templates\<language>\`, for example `DefaultMetric.rte`, `Structural Analysis-DefaultMetric.rte`, `Mechanical-Default_Metric.rte`, `Plumbing-Default_Metric.rte`, `Electrical-Default_Metric.rte`, `Default-Multi-Discipline_Metric.rte`. `app.DefaultProjectTemplate` is the one the user's Revit starts new projects from.
- **Family libraries:** `app.GetLibraryPaths()`. Recent Revit versions install only part of the library and download the rest on demand, so a family may simply not be on disk. Say so instead of substituting a different category.

## Saving: what a run can and can't do

- **Guarded runs cannot save documents.** The host blocks `Save` and `SaveAs` for documents that were open, created, or opened from disk during a run. It also closes background documents it created or opened without saving when the run ends. Use a run to inspect or prepare a document, then have the user save it in Revit after the run.
- **The document that was open when the run started can't be saved from a run.** Revit refuses with "Operation is not permitted when there is any open transaction phase started by API client", because the run holds a transaction group on it. Ask the user to save it in Revit.
- **Files written during a dry run stay on disk.** A dry run rolls back model changes, not files.
- **Check cleanup outcomes.** `changes.other_documents` reports `rolled_back` only after a successful transaction-group rollback, and `discarded_on_close` only after a document opened from disk has actually closed. `rollback_incomplete` means changes remain in memory: tell the user to close that document without saving. Check `unclosed_documents` and `warnings` before reporting success.

## Creating files from templates

Pick a family template by category and hosting before creating a family. A family's hosting cannot be changed later, so a light that must sit on a ceiling needs a ceiling-based template. Project templates sit in language folders under one root, and the default template can be in a different one (`English-Imperial` while the metric templates are in `English`).

A guarded run can inspect template paths and make reversible changes to an existing document, but it cannot create a durable `.rfa` or `.rvt`: it blocks both `Save` and `SaveAs`. Have the user create and save a new family or project in Revit, then use a later run to work on that open document.

## Opening a document for the user

```python
try:
    uiapp.OpenAndActivateDocument(inputs["path"])
except Exception as error:
    note = str(error)
result = {"active": uiapp.ActiveUIDocument.Document.Title if uiapp.ActiveUIDocument else None}
```

- **With no document open**, runs still execute with `doc` and `uidoc` set to `None`, and the decision is `no_document`. `OpenAndActivateDocument` returns normally there; open or create the project that way, then continue in the next run.
- **Called from a run while another project is open, `OpenAndActivateDocument` raises "An internal error has occurred" but still opens and activates the file.** The run's transaction group on the open project causes it. Don't treat the exception as failure: check `uiapp.ActiveUIDocument` afterwards, then `get_context`.
- `app.OpenDocumentFile(path)` opens a file in the background, with no window. Use it to read another model, and close it when done. Changing a document that was already open when the run started, or a project or family you opened from a file, fails the run with `other_document_modified`, and it can't be saved.

## Before you report done

- [ ] Every file you wrote exists (`os.path.exists`), and you told the user its full path.
- [ ] No existing file was replaced without the user's agreement.
- [ ] Every document you created or opened in the background is closed: it's no longer in `app.Documents`.
- [ ] A loaded family is found in the project by name, with the types you expected.
- [ ] The document the user sees is the one they expect (`get_context`).
