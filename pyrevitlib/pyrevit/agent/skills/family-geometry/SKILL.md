---
name: family-geometry
description: Creating content inside Revit families. Covers reference planes, labelled dimensions, locked extrusions, formulas, shared parameters, visibility and graphics, materials, and nested families. Use it for "build a parametric family", "add reference planes and dimensions", "lock the extrusion to the planes", "nest one family in another", "add a shared parameter to a family" and similar tasks. Read family-editing first for opening, saving and loading families.
---

# Family geometry

Read `revit-scripting` and `family-editing` first. Everything below runs in a **family document**: one the user has open, one from `doc.EditFamily`, or a new one from `app.NewFamilyDocument(template_path)`. Templates are under `app.FamilyTemplatePath`.

```python
from pyrevit.revit.db import create, update
```

The snippets were run in Revit 2024.1 on IronPython 2.7.12; the helpers also on CPython 3.12.

## Rules that decide whether a script works

- **Roll back before you close.** If a script fails with a transaction open, `fam_doc.Close(False)` in `finally` raises "Close is not allowed when there is any open sub-transaction" and hides the real error. Keep the transaction in a variable and roll it back in `except`:

  ```python
  fam_doc = app.NewFamilyDocument(template_path)
  t = DB.Transaction(fam_doc, "Build")
  try:
      t.Start()
      t.Commit()
  except Exception:
      if t.GetStatus() == DB.TransactionStatus.Started:
          t.RollBack()
      raise
  finally:
      fam_doc.Close(False)
  ```
- **Transactions on the family document** are needed for `Regenerate()`, `NewType` and every edit. Setting `fm.CurrentType` outside one fails.
- **A family starts with no type.** `fm.CurrentType` is `None` and `SetFormula` raises "There is no valid family type" until you call `fm.NewType("name")`.
- **Plan views** are `DB.ViewPlan` with `ViewType.FloorPlan`; the Generic Model template names both its floor plan and ceiling plan "Ref. Level", so filter by `ViewType`, not by name. Elevations are `ViewType.Elevation`, named "Front", "Back", "Left", "Right".
- **Units are feet** in the family document, as everywhere in the API.

## Parametric box: planes, dimensions, extrusion, locks

Build in this order. The extrusion follows the parameters only when its faces are aligned to reference planes that dimensions drive.

```python
tpl = r"C:\ProgramData\Autodesk\RVT 2024\Family Templates\English\Metric Generic Model.rft"
fam_doc = app.NewFamilyDocument(tpl)
t = DB.Transaction(fam_doc, "Build box")
try:
    fm = fam_doc.FamilyManager
    plan = [v for v in DB.FilteredElementCollector(fam_doc).OfClass(DB.ViewPlan)
            if not v.IsTemplate and v.ViewType == DB.ViewType.FloorPlan][0]
    centre = dict((p.Name, p) for p in DB.FilteredElementCollector(fam_doc).OfClass(DB.ReferencePlane))
    t.Start()
    width = fm.AddParameter("Width", DB.GroupTypeId.Geometry, DB.SpecTypeId.Length, False)
    height = fm.AddParameter("Height", DB.GroupTypeId.Geometry, DB.SpecTypeId.Length, False)
    fm.NewType("Default")
    fm.Set(width, 2.0)
    fm.Set(height, 3.0)

    left = create.create_reference_plane("Left", (-1, -2), (-1, 2), plan, reference="left", doc=fam_doc)
    right = create.create_reference_plane("Right", (1, -2), (1, 2), plan, reference="right", doc=fam_doc)
    fam_doc.Regenerate()
    create.create_labelled_dimension(plan, [left, right], (-1, -1.5), (1, -1.5), label=width, doc=fam_doc)
    create.create_labelled_dimension(plan, [left, centre["Center (Left/Right)"], right], (-1, -2.5), (1, -2.5),
                                     equal_segments=True, doc=fam_doc)

    level = DB.FilteredElementCollector(fam_doc).OfClass(DB.Level).FirstElement()
    sketch_plane = DB.SketchPlane.Create(fam_doc, level.GetPlaneReference())
    profile = DB.CurveArrArray()
    profile.Append(create.create_curve_array([(-1, -0.5), (1, -0.5), (1, 0.5), (-1, 0.5)]))
    extrusion = fam_doc.FamilyCreate.NewExtrusion(True, profile, sketch_plane, 3.0)
    fam_doc.Regenerate()

    create.align_faces_to_planes(extrusion, plan, [left, right], doc=fam_doc)
    fm.AssociateElementParameterToFamilyParameter(
        extrusion.get_Parameter(DB.BuiltInParameter.EXTRUSION_END_PARAM), height)
    t.Commit()
except Exception:
    if t.GetStatus() == DB.TransactionStatus.Started:
        t.RollBack()
    raise
finally:
    fam_doc.Close(False)
```

- **Always flex it.** Set the parameters to other values inside a new transaction, call `Regenerate()`, and read `extrusion.get_BoundingBox(None)`. An extrusion that was not aligned keeps its size while the planes move. `Constraints are not satisfied` at this step means conflicting locks or dimensions.
- **Label a two-plane dimension only.** A label on a dimension through three planes labels *every segment*: a `Width` of 2 became 4 per segment, 8 overall. Label the outer pair and add a second, unlabelled dimension through the centre plane with `equal_segments=True` (`AreSegmentsEqual`). `create_labelled_dimension` raises if you label three planes.
- **`reference=`** sets "Is Reference" on a plane: `"left"`, `"center_left_right"`, `"right"`, `"front"`, `"center_front_back"`, `"back"`, `"bottom"`, `"center_elevation"`, `"top"`, `"strong"`, `"weak"`, `"not_a_reference"`. A host family aligns to a nested family's planes only when they are flagged, so flag the planes of any family you intend to nest.
- **Raw API behind the helpers:** `fam_doc.FamilyCreate.NewReferencePlane(bubble_end, free_end, cut_vector, view)`, `NewDimension(view, line, reference_array)` then `dimension.FamilyLabel = parameter`, and `NewAlignment(view, plane.GetReference(), face.Reference)` with faces from `get_Geometry` using `DB.Options()` with `ComputeReferences = True` and `View` set. Use the plan view for vertical faces and an elevation view for horizontal ones.
- **Extent parameters:** `EXTRUSION_START_PARAM` and `EXTRUSION_END_PARAM` on the extrusion take the association; an extrusion's height is not a plane unless you also align its top face.
- **Sloped solids:** a point where two sloped faces meet has no face to align. Give it a flat edge of at least `app.ShortCurveTolerance` (a 0.005 ft edge worked; 0.002 ft raised "Curve length is too small"), then align that face to a plane in an elevation view. A pure apex also followed its plane in a simple test, so flex before adding the edge.

## Formulas

```python
update.set_formula(fm, panel_width, "Width / 2")
update.set_formula(fm, is_wide, "not(Width > 5')")
```

- **`update.set_formula(fm, parameter, formula)`** re-raises Revit's "It is an invalid formula string" with the parameter and formula in the message. Use it instead of `fm.SetFormula` so a batch shows which formula failed.
- **No `<=` or `>=`.** Both are rejected. Use `not(a > b)` for `a <= b`. `>`, `not(...)` and `if(cond, a, b)` work. A formula that names a parameter that doesn't exist is rejected the same way.
- **Lengths in formulas carry units**: `Width > 5'`, `if(Width > 5', 1', 2')`. A Yes/No parameter takes a condition directly.
- **`set_formula(fm, parameter, None)`** clears a formula.

## Shared parameters in a family

```python
original = app.SharedParametersFilename
try:
    app.SharedParametersFilename = shared_parameter_file
    definition_file = app.OpenSharedParameterFile()
    definition = definition_file.Groups.get_Item("Doors").Definitions.get_Item("Fire Rating")
    parameter = fam_doc.FamilyManager.AddParameter(definition, DB.GroupTypeId.Identity, True)
finally:
    app.SharedParametersFilename = original
```

- **`SharedParametersFilename` is the user's setting.** Reading definitions needs it set, so set it and restore it in `finally`, as above. `OpenSharedParameterFile()` returns `None` for a file that doesn't exist; an empty existing file opens fine and can receive new groups with `Groups.Create`.
- **Create a definition** with `DB.ExternalDefinitionCreationOptions(name, DB.SpecTypeId.Length)`; set `options.GUID = System.Guid("...")` for a fixed GUID, then `group.Definitions.Create(options)`.
- **GUIDs are stable.** Adding one definition to two families gives both parameters the same `parameter.GUID`. Look up by `fm.get_Parameter("Name")` or `fm.get_Parameter(guid)`. The property is `GUID`, not `Guid`.
- **Adding the same definition twice** raises "The shared parameter 'X' is already in use". Check `fm.get_Parameter(definition.Name)` first.

## Visibility and graphics

```python
visibility = extrusion.GetVisibility()
visibility.IsShownInCoarse = False
extrusion.SetVisibility(visibility)

category = fam_doc.OwnerFamily.FamilyCategory
subcategory = fam_doc.Settings.Categories.NewSubcategory(category, "Frame")
extrusion.Subcategory = subcategory
subcategory.SetLineWeight(5, DB.GraphicsStyleType.Projection)
subcategory.LineColor = DB.Color(200, 0, 0)
patterns = list(DB.FilteredElementCollector(fam_doc).OfClass(DB.LinePatternElement))
subcategory.SetLinePatternId(patterns[0].Id, DB.GraphicsStyleType.Projection)
```

- **`FamilyElementVisibility`** has `IsShownInCoarse`, `IsShownInMedium`, `IsShownInFine`, `IsShownInPlanRCPCut`, `IsShownInFrontBack`, `IsShownInLeftRight`, `IsShownInTopBottom` and `IsShownOnlyWhenCut`. `SetVisibility` replaces all flags, so start from `element.GetVisibility()` when you change one, as above; a new `FamilyElementVisibility` resets the rest.
- **Keep the object `NewSubcategory` returns.** Looking the subcategory up again through the `category.SubCategories` you read earlier fails. Line patterns include "Dash", "Dash dot", "Center" and "Dot".
- **Materials:** `fam_doc.GetElement(DB.Material.Create(fam_doc, "Paint"))` gives a material; `material.Color`, `Transparency` (0 to 100) and `Shininess` set its look. To let each type choose, add a parameter `fm.AddParameter("Frame Material", DB.GroupTypeId.Materials, DB.SpecTypeId.Reference.Material, True)` and associate it with `extrusion.get_Parameter(DB.BuiltInParameter.MATERIAL_ID_PARAM)`; set the value with `fm.Set(parameter, material.Id)`.
- **Appearance assets are not covered here.** Editing one with `DB.Visual.AppearanceAssetEditScope` changed values in memory, but `Commit` failed with "EditScope cannot be closed, there is no opened transaction" in a family document on both engines. Say so to the user instead of retrying.
- **`Visible = No` hides nothing in the editor.** The form's `IS_VISIBLE_PARAM` set to 0 still returns its full solid from `get_Geometry`; the effect shows only on placed instances. Check hidden forms on an instance, not in the family view.

## Nested families

```python
child_family = create.load_family_document(child_doc, doc=host_doc, name="Frame")
t = DB.Transaction(host_doc, "Place")
t.Start()
symbol = host_doc.GetElement(list(child_family.GetFamilySymbolIds())[0])
if not symbol.IsActive:
    symbol.Activate()
host_doc.Regenerate()
instance = host_doc.FamilyCreate.NewFamilyInstance(DB.XYZ.Zero, symbol, DB.Structure.StructuralType.NonStructural)
host_doc.Regenerate()
fm = host_doc.FamilyManager
fm.AssociateElementParameterToFamilyParameter(instance.LookupParameter("Width"), host_width)
fm.AssociateElementParameterToFamilyParameter(instance.get_Parameter(DB.BuiltInParameter.IS_VISIBLE_PARAM), show_frame)
t.Commit()
```

- **Load outside a transaction.** `load_family_document` raises when the target has one open: `LoadFamily` runs its own. Call it before `t.Start()`.
- **Rename on load.** A family document that was never saved loads under its document title (`Family24`), and the same happens for a nested family loaded into a host. Pass `name=` to rename it at once, and do so before the host is itself loaded into a project: the nested name is stored in the host. The helper raises before loading when another family already has that name, and rolls its rename back if Revit rejects the name.
- **Reloading replaces the `Family`.** Keep the name, not the object, and look it up again after a reload. The helper returns the new object.
- **Associate a nested parameter** with a host parameter and the host drives it: a host `Width` of 6 resized the nested instance to 6. `IS_VISIBLE_PARAM` takes a Yes/No host parameter and shows or hides the instance.
- **`instance.GetReferenceByName("Left")`** returns the nested family's plane for alignment when the child flagged it with `reference="left"`.

## Limits that fail

| What you try | What Revit does |
|---|---|
| `fam_doc.OwnerFamily.FamilyCategory = Stairs` | `The input category id cannot be assigned as the new category for this family.` Use a category that loadable families allow, such as Generic Models. |
| `<=` or `>=` in a formula | `It is an invalid formula string.` Use `not(a > b)`. |
| Any formula before the first type | `There is no valid family type.` Call `NewType` first. |
| `Regenerate()` without a transaction | `Modification of the document is forbidden.` |
| `Close(False)` with a transaction open | `Close is not allowed when there is any open sub-transaction...` |
| Same shared definition added twice | `The shared parameter 'X' is already in use.` |
| A curve shorter than `app.ShortCurveTolerance` | `Curve length is too small for Revit's tolerance.` |

## Before you report done

- [ ] The parameters were flexed to other values and the geometry followed, checked by bounding box or `capture_view` on a placed instance.
- [ ] Each hidden form was checked on an instance, not in the family editor.
- [ ] `app.SharedParametersFilename` is back to what it was.
- [ ] Nested families have the names the user expects, not `FamilyNN`.
- [ ] Every family document you opened is closed, and no family file was saved unless the user asked.
