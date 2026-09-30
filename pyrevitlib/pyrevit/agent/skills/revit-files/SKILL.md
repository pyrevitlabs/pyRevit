---
name: revit-files
description: Revit file types and working with files. Covers what .rvt, .rte, .rfa and .rft files are, where templates and libraries live, creating a new family from a family template, creating a new project from a project template, opening and saving documents from a run, and loading a family file into the project. Use it for "make a new family", "start a project from the mechanical template", "open this model", "save the family" and similar tasks.
---

# Revit files

## File types

| Extension | What it is | Open or create it with |
|---|---|---|
| `.rvt` | A project: the building model, its views and sheets. Also used for central and local models of a workshared project; `Name.0001.rvt` files next to it are backups. | `app.OpenDocumentFile(path)`, or `uiapp.OpenAndActivateDocument(path)` to show it to the user |
| `.rte` | A project template: the starting settings, types, views and families of a new project. | `app.NewProjectDocument(path)` |
| `.rfa` | A loadable family: doors, furniture, equipment, fixtures. | `doc.LoadFamily(path)` to load it into a project; `app.OpenDocumentFile(path)` to read it. A family opened from disk can't be changed or saved; to change the file, load it, edit it with `EditFamily`, and `SaveAs` its path |
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

- **New documents and families from `EditFamily`** can be saved (`SaveAs`) and closed (`Close(False)`) from the same run. Documents opened from a file with `OpenDocumentFile` or `OpenAndActivateDocument` cannot be saved, even if their `PathName` is empty (for example a detached model).
- **Create, build and save a new document in one run.** When a run ends, the host closes every background document it created or opened, without saving, and lists them in `closed_documents`; a failed run loses whatever it built there. Never keep an unsaved model across runs: a crash or a closed document loses it. `get_context.open_documents` shows what is open.
- **The document that was open when the run started can't be saved from a run.** Revit refuses with "Operation is not permitted when there is any open transaction phase started by API client", because the run holds a transaction group on it. Ask the user to save it in Revit.
- **Files written during a dry run stay on disk.** A dry run rolls back model changes, not files.
- **Check cleanup outcomes.** `changes.other_documents` reports `rolled_back` only after a successful transaction-group rollback, and `discarded_on_close` only after a document opened from disk has actually closed. `rollback_incomplete` means changes remain in memory: tell the user to close that document without saving. Check `unclosed_documents` and `warnings` before reporting success.
- **`SaveAs` fails when the file exists.** Check with `os.path.exists` first and ask the user before replacing a file; overwrite only with `DB.SaveAsOptions()` and `OverwriteExistingFile = True` after they agree.
- **Save only where the user agreed**, and tell them the full path you wrote.

## New family from a family template

1. **Pick the template** by category and hosting. A family's hosting can't be changed later, so a light that must sit on a ceiling needs a ceiling-based template.
2. **Create and build it** in the family document, in its own transaction. Close it in a `finally`, so it never stays open in memory.
3. **Save it** as `.rfa`, then **load it** into the project in a guarded run: `run_modify` with `dry_run=true` first.

```python
import os

MM = 1 / 304.8
template = os.path.join(app.FamilyTemplatePath, "English", "Metric Generic Model.rft")
target = os.path.join(inputs["folder"], "Planter Box.rfa")
if os.path.exists(target):
    raise ValueError("{} exists; ask the user before replacing it.".format(target))

family_doc = app.NewFamilyDocument(template)
try:
    t = DB.Transaction(family_doc, "Build planter box")
    t.Start()
    manager = family_doc.FamilyManager
    manager.NewType("600 x 400")
    width = manager.AddParameter("Width", DB.GroupTypeId.Geometry, DB.SpecTypeId.Length, False)
    manager.Set(width, 600 * MM)
    corners = [DB.XYZ(0, 0, 0), DB.XYZ(600 * MM, 0, 0), DB.XYZ(600 * MM, 400 * MM, 0), DB.XYZ(0, 400 * MM, 0)]
    profile = DB.CurveArray()
    for start, end in zip(corners, corners[1:] + corners[:1]):
        profile.Append(DB.Line.CreateBound(start, end))
    loops = DB.CurveArrArray()
    loops.Append(profile)
    plane = DB.SketchPlane.Create(family_doc, DB.Plane.CreateByNormalAndOrigin(DB.XYZ.BasisZ, DB.XYZ.Zero))
    family_doc.FamilyCreate.NewExtrusion(True, loops, plane, 300 * MM)
    t.Commit()
    family_doc.SaveAs(target)
finally:
    family_doc.Close(False)

t = DB.Transaction(doc, "Load Planter Box")
t.Start()
doc.LoadFamily(target)
t.Commit()
family = [f for f in DB.FilteredElementCollector(doc).OfClass(DB.Family) if f.Name == "Planter Box"]
result = {"saved": target, "loaded": bool(family)}
```

- **Find the loaded family by name.** Depending on the engine, `doc.LoadFamily(path)` returns only `True`, not the `Family`.
- **Parameters:** `AddParameter(name, group, spec, is_instance)` takes `DB.GroupTypeId` and `DB.SpecTypeId` values. A new family has no type until you call `manager.NewType(...)`; set values after that.
- **Load without saving:** when the user doesn't want a file, `family_doc.LoadFamily(doc, options)` loads straight from the family document; see the `family-editing` skill for the options handler.
- **Editing an existing family** is the `family-editing` skill's job.

## New project from a project template

```python
import os

templates_root = os.path.dirname(os.path.dirname(app.DefaultProjectTemplate))
template = os.path.join(templates_root, "English", "Mechanical-Default_Metric.rte")
if not os.path.exists(template):
    raise ValueError("No {}; language folders: {}".format(template, sorted(os.listdir(templates_root))))
target = os.path.join(inputs["folder"], "Office HVAC.rvt")
if os.path.exists(target):
    raise ValueError("{} exists; ask the user before replacing it.".format(target))

project = app.NewProjectDocument(template)
project.SaveAs(target)
project.Close(False)
result = {"saved": target}
```

- `app.NewProjectDocument` creates the project in memory, with no window. Save it, close it, then show it to the user as below.
- Templates sit in language folders under one root, and the default template can be in a different one (`English-Imperial` while the metric templates are in `English`). Name the language folder explicitly, as above.

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
