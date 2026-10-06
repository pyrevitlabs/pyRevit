---
name: family-editing
description: Editing Revit families. Covers opening a family from the project, family parameters, types and formulas, and loading the family back into the project. Use it for "add a parameter to these families", "create door types", "fix family formulas" and similar tasks.
---

# Family editing

Read `revit-scripting` first. Check API names with `lookup_revit_api`.

## Where the family lives

- **Active document is a family** (`get_context.document.is_family` is true): `doc.FamilyManager` is available directly. Change it inside transactions on `doc`, as usual.
- **Family used in a project:** open a family document from the project, edit it, and load it back. `doc.EditFamily` takes a `DB.Family` and returns an in-memory family document; make your edits where this snippet adds a type:

  ```python
  family = doc.GetElement(family_id)
  fam_doc = doc.EditFamily(family)
  try:
      t = DB.Transaction(fam_doc, "Edit family")
      t.Start()
      fam_doc.FamilyManager.NewType("900 x 2100")
      t.Commit()
      from pyrevit.revit.db.create import FamilyLoaderOptionsHandler
      fam_doc.LoadFamily(doc, FamilyLoaderOptionsHandler())
  finally:
      fam_doc.Close(False)
  ```

## What the run guard covers here

The run guard, and the dry-run rollback, cover the **project** document only.

- **In the family document:** transactions are **not** rolled back by a dry run. They're discarded only because the family document is closed without saving.
- **Failures in the family document** are handled like the project's: warnings are removed and reported in `failures`, and an error rolls back that transaction and fails the run with `revit_failure`. Each entry names its `document`.
- **The project change is `LoadFamily`.** It's part of the guarded run, so it's rolled back by a dry run and needs approval under policy `ask`.
- **Close without saving:** always call `fam_doc.Close(False)`, in a `finally`.
- **Reloading replaces the `Family` object.** After `LoadFamily` brings an edited family back, the `Family` you edited is no longer valid (`IsValidObject` is false). Keep its name before editing, and look the family up again by name to read it afterwards.
- **Save only on request:** don't call `fam_doc.Save()` or `SaveAs()` unless the user asked to change the family file on disk. A family from `EditFamily` or `NewFamilyDocument` can be saved; the project open when the run started, and any file you opened with `OpenDocumentFile`, can't.

## Family parameters

```python
fm = fam_doc.FamilyManager
is_instance = False
param = fm.AddParameter("Frame Width", DB.GroupTypeId.Geometry, DB.SpecTypeId.Length, is_instance)
fm.SetFormula(param, "Width / 10")
```

- **Groups and specs** are `ForgeTypeId`s: `DB.GroupTypeId.*` and `DB.SpecTypeId.*`. Look them up with `lookup_revit_api("GroupTypeId")`.
- **Existing parameters:** `fm.get_Parameter("Name")`, or `fm.Parameters`. pyRevit has helpers: `from pyrevit.revit.db import query`, then `query.get_family_parameter(name, fam_doc)` and `query.get_family_parameters(fam_doc)`.
- **Shared parameters:** `fm.AddParameter(external_definition, group, is_instance)` takes a definition from the shared parameter file.

## Types

- **Existing types:** `fm.Types`, and `fm.CurrentType` for the one being edited.
- **New type:** `fm.NewType("900 x 2100")`. It becomes the current type.
- **Set a value** for the current type: `fm.Set(param, value)`. Lengths are in feet.
- **Change several types:** set `fm.CurrentType = family_type` before each `Set`.

## Loading families from disk

- **Easiest:** `from pyrevit.revit.db.create import load_family`, then `load_family(path, doc=doc)`.
- **Direct API:** `doc.LoadFamily(path, FamilyLoaderOptionsHandler())` returns a tuple `(loaded, family)`.
- **Before placing a loaded type**, activate it: `symbol.Activate()`, then `doc.Regenerate()`.

## Before you report done

- [ ] The family's types and parameter values, queried after loading, are the ones asked for.
- [ ] A geometry change was checked on a placed instance or in a view with `capture_view`.
- [ ] Every family document you opened is closed: it's no longer in `app.Documents`.
- [ ] The family file on disk is unchanged unless the user asked to save it.
