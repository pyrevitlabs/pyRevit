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
5. **Check.** `capture_view` returns a PNG of a view: `view="3d"` frames the whole model, `elements=[...]` frames part of it, `direction` picks the side. Look at it, and read back a number (a height, an area, a count), before you report success.

## Before you change a model

- **Unsaved document:** when `get_context` shows an empty `document.path`, ask the user to save the project before you build. Everything else lives only in memory, and Revit's save reminder will interrupt the session.
- **Revit busy for a long time:** a `revit_busy` error names the open Revit windows. A modal dialog such as the save reminder blocks every request until it is answered. Ask the user to answer it. Never close Revit windows yourself (for example with WM_CLOSE): closing one cancels whatever it was asking about.
- **`warnings` in a run result** say that elements from an earlier commit have disappeared, either because the user undid them or because Revit undid that commit together with a rolled-back run. Rebuild that stage and check it before building on it.

## Script contract

- **Injected names:** `doc`, `uidoc`, `app`, `uiapp`, `DB` (Autodesk.Revit.DB), `UI` (Autodesk.Revit.UI), and `inputs` (the dict you pass as `inputs`). Don't `import DB` or `import UI`.
- **Use the shared libraries first.** pyrevitlib (`from pyrevit import revit`; `from pyrevit.revit.db import query, create, update`) and rpw (`from rpw import db`) cover lookups, element and view creation, parameters, units, transactions and navigation, and they handle the API traps below. Find functions with `lookup_pyrevit_api`; the `pyrevit-library` skill maps them. Write raw `DB.` code only for what they don't cover.
- **Your own helpers across runs:** put plan data and helper functions in modules in a folder, and pass the folder as `workspace` to `run_query` and `run_modify`. Then `import my_module` works, and it is re-imported fresh every run, so edits apply. Don't paste the same library into every script.
- **Modules don't see the injected names.** `doc`, `DB` and the others exist only in the run script, so a workspace module that uses them fails with `NameError`. Import in the module and take the document as an argument:

  ```python
  from pyrevit import revit, DB

  def wall_count(doc=None):
      doc = doc or revit.doc
      return DB.FilteredElementCollector(doc).OfClass(DB.Wall).GetElementCount()
  ```

  Call it as `my_module.wall_count(doc)` from the run script.
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
- **Runs stop after `timeout_s` seconds** (default 300) with error `timeout` and are rolled back. Pass a larger `timeout_s` for long batch work rather than splitting it into many runs.
- **`run_modify` scripts open their own transactions.** The host wraps the whole run in one group, so a committed run is one undo entry named "Agent: title".

  ```python
  from pyrevit import revit
  with revit.Transaction("Set comments"):
      ...
  ```

  It rolls back and re-raises when the block raises. `DB.Transaction` with `Start()`/`Commit()` works too.

- **Leave nothing open.** A transaction left open fails the run with `transaction_left_open`.
- **View state counts as a change.** Graphic overrides and view properties change the document, so they need a transaction. Temporary hide/isolate does too, but `show_elements` does it for you without approval.

## Units and ids

- **Units:** internal lengths are feet and angles are radians. To report in project units, use `DB.UnitUtils.ConvertFromInternalUnits(value, DB.UnitTypeId.Millimeters)`.
- **A bare number is feet everywhere,** in the Revit API and in pyrevitlib. `create.create_wall(..., height=3500)` builds a wall 3,500 feet high without complaint. Write `"3500mm"`, or convert first, and read a dimension back after creating.
- **ElementId values:** `element_id.Value` on Revit 2024 and later, `IntegerValue` before that. `Value` is a .NET Int64: use `str(element_id.Value)` or `"{}".format(...)` to build strings.
- **Building ids:** `DB.ElementId(value)`.

## Collecting elements

Every element that reaches Python costs time, so let Revit filter before anything crosses over. On a 6,000-element model, native filters were 5-12 times faster than the same filter in Python on IronPython 3.4, and 10-30 times faster on CPython; the gap grows with the model.

1. **Quick filters first:** `DB.FilteredElementCollector(doc)` (there is no `DB.Collector`), then `.OfClass(DB.Wall)` or `.OfCategory(DB.BuiltInCategory.OST_Doors)`, and `.WhereElementIsNotElementType()` or `.WhereElementIsElementType()`.
2. **Parameter conditions in the database:** `.WherePasses(DB.ElementParameterFilter(rule))` with a rule from `DB.ParameterFilterRuleFactory`, or pyrevitlib's `query.get_elements_by_param_value`.
3. **Native endings:** `.GetElementCount()` to count, `.FirstElement()` for one element, `.ToElementIds()` when ids are enough. Build Python lists only from what's left.

```python
walls_with_comments = (
    DB.FilteredElementCollector(doc)
    .OfClass(DB.Wall)
    .WherePasses(DB.ElementParameterFilter(
        DB.ParameterFilterRuleFactory.CreateNotEqualsRule(
            DB.ElementId(DB.BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS), "")))
    .ToElements()
)
```

- **Slow:** `len(list(collector))` and `[e for e in collector if e.get_Parameter(...)...]` over a whole model. Fine on a short, already filtered list.
- **`CreateHasValueParameterRule` isn't "not empty".** An empty text value counts as a value. For text, use `CreateNotEqualsRule(parameter_id, "")`.
- **Deleting by category deletes its types too.** `OfCategory(...)` without `.WhereElementIsNotElementType()` returns the category's types as well, so a cleanup that deletes "last run's output" by category also deletes the types a later step needs.
- **Filters change the collector itself.** `walls = everything.OfClass(DB.Wall)` returns the same object, so `everything` now holds only walls too. Start a new `FilteredElementCollector` for each query.

## Performance rules (strict)

A script runs on Revit's main thread, and Revit is frozen until it returns. Models hold tens of thousands of elements, so a quadratic script that takes a second on a test model takes hours on a real one, and the run is stopped at `timeout_s`. These rules are not optional:

1. **No O(n²): never compare every element with every other one.** No nested loops over two collections of elements, and no `for a in walls: for b in walls:`. Let Revit's spatial index find the neighbours of each element (below), or group elements by a key in a dict first.
2. **No O(2ⁿ) or O(n!): never search combinations, subsets, permutations or layouts by trying them.** No `itertools.combinations`/`permutations` over elements, and no recursion that branches per element. Compute the answer directly from the geometry. If you can't, stop and ask the user.
3. **Look up in a dict or a set, never in a list inside a loop.** Build `{room.Number: room for room in rooms}` or a set of id values once; `x in some_list` inside a loop is O(n²).
4. **Nothing expensive inside a loop over elements:** no collector whose result doesn't depend on the loop variable (collect once before the loop), no transaction per element (one transaction per stage), and no `doc.Regenerate()` per element.
5. **Walking connected elements needs a visited set.** Connectors reference each other in both directions, and joins and hosts can form cycles, so a walk without `seen` never ends.
6. **Every `while` loop has a bound.** Count iterations and raise with a clear message past a limit you can justify.

Neighbours through Revit's spatial index instead of pairwise checks:

```python
from System.Collections.Generic import List

walls = list(DB.FilteredElementCollector(doc).OfClass(DB.Wall))
touching = {}
for wall in walls:
    box = wall.get_BoundingBox(None)
    if box is None:
        continue
    others = List[DB.ElementId]()
    others.Add(wall.Id)
    touching[wall.Id] = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.Wall)
        .WherePasses(DB.BoundingBoxIntersectsFilter(DB.Outline(box.Min, box.Max)))
        .Excluding(others)
        .ToElementIds()
    )
```

`DB.ElementIntersectsElementFilter(element)` and `DB.ElementIntersectsSolidFilter(solid)` narrow the bounding-box hits to real geometry overlaps.

Walking a connected network, each element visited once:

```python
from collections import deque


def id_value(element):
    return element.Id.Value if hasattr(element.Id, "Value") else element.Id.IntegerValue


def connected(first, limit=10000):
    seen = {id_value(first)}
    queue = deque([first])
    members = []
    while queue:
        if len(members) >= limit:
            raise RuntimeError("More than {} connected elements; narrow the search.".format(limit))
        element = queue.popleft()
        members.append(element)
        manager = getattr(element, "ConnectorManager", None) or getattr(getattr(element, "MEPModel", None), "ConnectorManager", None)
        for connector in (manager.Connectors if manager else []):
            for other in connector.AllRefs:
                owner = other.Owner
                if id_value(owner) not in seen:
                    seen.add(id_value(owner))
                    queue.append(owner)
    return members
```

## Code style (strict)

1. **No comments, ever.** No `#` comment lines, no comments at the end of a line, and no commented-out code, in run scripts and in workspace modules. Clear names and small functions carry the meaning; explanations go in your reply to the user. The only `#` lines allowed are the ones tools read: `#! python3` and `# -*- coding: utf-8 -*-`.
2. **No docstrings.** No string literal as the first statement of a script, module, function or class.
3. **Extensions are the one exception for docstrings.** Button scripts and modules in an extension's `lib\` may have them; the `extension-authoring` skill says how. Comments stay forbidden there too.

## Revit API essentials

- **`OfCategory` takes a `BuiltInCategory`**, not a `Category` object.
- **`OfClass` only accepts native classes.** For rooms, areas and spaces use `OfCategory(DB.BuiltInCategory.OST_Rooms)`, or `OfClass(DB.SpatialElement)` plus `isinstance()`.
- **A category holds several classes.** `OST_Walls` also returns in-place walls as `FamilyInstance`. Filter with `OfClass` or `isinstance()` before using class members such as `Wall.WallType`.
- **Types are elements too.** `FamilySymbol`, `WallType` and other types are element types, so `OfClass(DB.FamilySymbol).WhereElementIsNotElementType()` returns nothing. To check whether a family is loaded, collect `OfClass(DB.FamilySymbol)` or `OfClass(DB.Family)` without that filter.
- **Connectors** (MEP): a duct or pipe has `ConnectorManager` directly; a family instance has `instance.MEPModel.ConnectorManager`. A connector's position is `Origin` and its facing is `CoordinateSystem.BasisZ`; `Direction` is the flow direction (`FlowDirectionType`), not a vector. Round connectors have `Radius` (there is no `Diameter`); rectangular ones have `Width` and `Height` (check `connector.Shape`). Filter by `connector.Domain` before reading domain-specific members such as `DuctSystemType`.
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
  ids = List[DB.ElementId]()
  for element_id in python_ids:
      ids.Add(element_id)
  ```

  Build it with `Add`. `List[DB.ElementId](python_ids)` and `AddRange(python_ids)` work on IronPython but raise `TypeError` on CPython.

- **Out parameters:** IronPython 3.4 passes null for out arguments, whether you omit them, pass a value, or pass a `StrongBox`, and many Revit methods reject null with `ArgumentNullException`. The recipe that works on every engine is reflection with a pre-filled `System.Array[System.Object]`; the out value is written back into the array:

  ```python
  import System
  method = doc.Create.GetType().GetMethod("NewFootPrintRoof")
  arguments = System.Array[System.Object]([footprint, level, roof_type, DB.ModelCurveArray()])
  roof = method.Invoke(doc.Create, arguments)
  model_curves = arguments[3]
  ```

  A plain Python list fails; it must be `System.Array[System.Object]`. The pyrevitlib roof functions (`create.create_footprint_roof` and the gable, hip and shed variants) already do this.

- **No LINQ:** collectors have no `FirstOrDefault` or `Where`. Use `.FirstElement()`, `.WherePasses(...)` and `.GetElementCount()`, as in [Collecting elements](#collecting-elements).
- **No `import *`:** `from Autodesk.Revit.DB import *` skips enums on IronPython (`ViewType`, `StructuralType`). Use the injected `DB.` prefix. `Autodesk` itself isn't a name in the script; write `DB.GeometryObject`, not `Autodesk.Revit.DB.GeometryObject`.
- **Fail loudly.** Use the `query.find_*` functions, which raise with the names that exist. In your own code, when a lookup by name finds nothing, `raise` with the names that do exist; don't carry on with `None`. When a filter matches no elements, raise too. Silent no-ops look like success in the change set.
- **Never `except Exception: pass`.** Collect the error text and return it. A swallowed exception in a loop reports "0 changed" as if it were a result. A bare `except:` catches only `Exception`, so it can't swallow the timeout.
- **Read numbers back.** After creating geometry, compare a measured value (a bounding box height, an area, a count) with what you intended. Plausible-looking geometry is the error that screenshots don't catch.
- **Never hardcode type names.** They differ between templates ("Generic - 300mm" wall, "Generic 300mm" floor, metric vs imperial). Query the types first and pick by name from that list.
- **Enum values** differ from UI names. For example it's `TemporaryViewMode.TemporaryHideIsolate`, not `.Isolate`. Look the enum up first.
- **Names that don't exist:** agents often guess API names from other libraries or older Revit versions. Before writing a name you haven't seen work, and whenever one fails, read `get_skill("revit-scripting", "api-names.md")`: it maps the common wrong guesses to the real names.

## Finding the right API

- **Static `...Utils` classes** hold much of the API (wall joins, face references, solid booleans, MEP caps, units). `get_skill("pyrevit-library", "revit-utilities.md")` maps them by task.
- **`lookup_revit_api(name)`** reflects the exact Revit version that is running. Use it instead of guessing.
  - `found: false` means the name doesn't exist, even when the type does (`type_found: true`). Read `suggestions`, and for enums `in_other_enums`: a guessed `BuiltInCategory.LEVEL_PARAM_ROOF_OFFSET` suggests `BuiltInParameter.ROOF_LEVEL_OFFSET_PARAM`.
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
