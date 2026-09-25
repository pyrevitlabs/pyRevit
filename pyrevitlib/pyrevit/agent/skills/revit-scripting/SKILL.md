---
name: revit-scripting
description: Core rules for every pyRevit agent task. Covers the script contract, engines, transactions, units, result shapes, the Revit API mistakes agents make most often, and how to recover from errors. Read this before your first script.
---

# Revit scripting through pyRevit

## Workflow

1. **Context.** `get_context` returns the Revit version, the document, the active view, the selection, the levels, the agent policy and `scripting`.
2. **Explore.** Use `run_query`, `inspect_elements` and `lookup_revit_api`. Filter and aggregate inside the script, and return only what you need.
3. **Show.** `show_elements` selects, zooms to, or temporarily isolates or hides elements. It needs no approval. Don't write `run_modify` scripts to show things.
4. **Change.** Call `run_modify` with `dry_run=true`, review the change set, then run it for real.
   - Policy `ask`: the user approves the change in Revit. Status `rejected` means they discarded it; ask them before retrying.
   - Policy `auto`: the change is committed without a prompt. Dry-run first and keep each change focused.
   - Policy `readonly`: modify runs are refused.
5. **Check.** `capture_view` returns a PNG of a view (`"3d"` for the whole model). Look at it before you report success.

## Script contract

- **Injected names:** `doc`, `uidoc`, `app`, `uiapp`, `DB` (Autodesk.Revit.DB), `UI` (Autodesk.Revit.UI), and `inputs` (the dict you pass as `inputs`). Don't `import DB` or `import UI`.
- **Returning data:** assign `result`. It must be JSON-serializable. `ElementId`, `Element` and `XYZ` are converted for you, and so are .NET numbers and collections. Use `print()` for short notes only.
- **Large results:** results over 256 KB are saved to the run record. Page through them with `get_run(run_id, offset, length)`.

## Python version

Read `get_context.scripting` before writing code. Scripts run on `scripting.default_engine` unless you pass `engine`.

- **IronPython 2.7:** Python 2 syntax. No f-strings, annotations or keyword-only arguments.
- **IronPython 3.4:** f-strings work. Not supported: walrus `:=`, `async`, `1_000` literals, positional-only `/`, `match`.
- **CPython 3.12:** full syntax. Pass `engine="cpython"` only when `scripting.engines.cpython.available` is true.

The `engine` field of every run response confirms what actually ran. `"{}".format(x)` works everywhere.

## Transactions

- **`run_query` never opens a transaction.** If the model changes, the run fails with `query_modified_model` and is rolled back.
- **`run_modify` scripts open their own transactions.** The host wraps the whole run in one group, so a committed run is one undo entry named "Agent: title".

  ```python
  t = DB.Transaction(doc, "Set comments")
  t.Start()
  # ... changes ...
  t.Commit()
  ```

- **Leave nothing open.** A transaction left open fails the run with `transaction_left_open`.
- **View state counts as a change.** Graphic overrides and view properties change the document, so they need a transaction. Temporary hide/isolate does too, but `show_elements` does it for you without approval.

## Units and ids

- **Units:** internal lengths are feet and angles are radians. To report in project units, use `DB.UnitUtils.ConvertFromInternalUnits(value, DB.UnitTypeId.Millimeters)`.
- **ElementId values:** `element_id.Value` on Revit 2024 and later, `IntegerValue` before that. `Value` is a .NET Int64: use `str(element_id.Value)` or `"{}".format(...)` to build strings.
- **Building ids:** `DB.ElementId(value)`.

## Revit API essentials

- **Collectors:** `DB.FilteredElementCollector(doc)`. There is no `DB.Collector`.
  - Instances of a class: `.OfClass(DB.Wall)`.
  - Instances in a category: `.OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType()`.
  - Counting: `.GetElementCount()` is cheaper than `len(.ToElements())`.
- **`OfCategory` takes a `BuiltInCategory`**, not a `Category` object.
- **`OfClass` only accepts native classes.** For rooms, areas and spaces use `OfCategory(DB.BuiltInCategory.OST_Rooms)`, or `OfClass(DB.SpatialElement)` plus `isinstance()`.
- **A category holds several classes.** `OST_Walls` also returns in-place walls as `FamilyInstance`. Filter with `OfClass` or `isinstance()` before using class members such as `Wall.WallType`.
- **Sub-namespaces:** `DB.Architecture.Room`, `DB.Structure.StructuralType`, `DB.Plumbing.Pipe`, `DB.Mechanical.Duct`. There is no `DB.Roof`; roofs are `DB.RoofBase` (`FootPrintRoof`, `ExtrusionRoof`).
- **Categories:** `DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Walls)` needs the document first.
- **Types and parameters:**
  - Type of an element: `doc.GetElement(element.GetTypeId())`.
  - Parameter by name: `element.LookupParameter("Mark")`.
  - Built-in parameter: `element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK)`. Prefer built-in parameters: `LookupParameter` names are UI names, they're localized, and some don't match (a floor's "Height Offset From Level" is `FLOOR_HEIGHTABOVELEVEL_PARAM`).
  - Comments: `DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS`.
  - Family name of an instance: `instance.Symbol.FamilyName`.
- **Geometry:**
  - Extents: `element.get_BoundingBox(None)` (model extents; pass a view for view extents).
  - Solids: `element.get_Geometry(DB.Options())` yields `Solid` and `GeometryInstance` objects; call `GetInstanceGeometry()` on instances. Skip solids with `Volume == 0`.
  - Geometry classes live directly in `DB`: `DB.Options`, `DB.Solid`, `DB.GeometryCreationUtilities`. There is no `DB.Geometry`.
- **.NET collections:** methods typed `ICollection<ElementId>` or `IList<...>` need a .NET collection, not a Python list:

  ```python
  from System.Collections.Generic import List
  ids = List[DB.ElementId](python_ids)
  ```

- **Out parameters:** many Revit methods reject a null out argument with `ArgumentNullException`, so the usual "omit it and get a tuple back" doesn't work for them. Pass a pre-filled reference and read `.Value`:

  ```python
  import clr
  mapping = clr.Reference[DB.ModelCurveArray](DB.ModelCurveArray())
  roof = doc.Create.NewFootPrintRoof(footprint, level, roof_type, mapping)
  model_curves = mapping.Value
  ```

- **No LINQ:** collectors have no `FirstOrDefault` or `Where`. Use `.FirstElement()`, `.ToElements()` and list comprehensions.
- **No `import *`:** `from Autodesk.Revit.DB import *` skips enums on IronPython (`ViewType`, `StructuralType`). Use the injected `DB.` prefix. `Autodesk` itself isn't a name in the script; write `DB.GeometryObject`, not `Autodesk.Revit.DB.GeometryObject`.
- **Fail loudly.** When a lookup by name finds nothing, `raise` with the names that do exist; don't carry on with `None`. When a filter matches no elements, raise too. Silent no-ops look like success in the change set.
- **Never hardcode type names.** They differ between templates ("Generic - 300mm" wall, "Generic 300mm" floor, metric vs imperial). Query the types first and pick by name from that list.
- **Enum values** differ from UI names. For example it's `TemporaryViewMode.TemporaryHideIsolate`, not `.Isolate`. Look the enum up first.
- **pyrevitlib** is importable and has tested helpers: `from pyrevit import revit`, with `revit.query` and `revit.create`.

## Finding the right API

- **`lookup_revit_api(name)`** reflects the exact Revit version that is running. Use it instead of guessing.
  - `lookup_revit_api("Wall")` gives signatures, the `namespace`, the `python_import` line, and a `creation` list (static factories and `doc.Create.New...` methods).
  - `lookup_revit_api("FootPrintRoof.DefinesSlope")` looks up one member.
- **Declared members only:** it lists a type's own members. For inherited ones, look up its `base_type`.
- **Creating elements:** some types have static factories (`Wall.Create`, `Floor.Create`, `Point.Create`, `ViewSheet.Create`). Others go through `doc.Create.New...` (`NewFootPrintRoof`, `NewRoom`, `NewFamilyInstance`).

## When a run fails

- **Read `error.hint` first.** For a missing `DB.X` it already names the real type, or similar ones.
- **`[.NET: ...]`** in the message is the underlying Revit exception. Its text usually says what was wrong with the input.
- **`revit_failure`** means Revit rolled back a transaction because of an error. `failures` lists the messages, for example an opening that can't cut its host wall.
- **Dialogs never block a run.** They're closed automatically and reported in `dialogs`. Warnings are removed and reported in `failures`.
- **`decision: no_changes`** means the script ran and changed nothing. If you expected changes, your filters or lookups matched nothing; it is not a Revit error.
- **The change set is a summary:** counts, categories and the first added ids. Names, classes and modified ids are in `get_run(run_id)`.
- **Fix one thing at a time and rerun.** Large results can be paged with `get_run(run_id)`.
