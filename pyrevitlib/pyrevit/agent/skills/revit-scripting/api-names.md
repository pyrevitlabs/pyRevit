# Revit API names agents guess wrong

Each row is a name that doesn't exist in the Revit API (or does something else), and what to use instead. Check anything not listed with `lookup_revit_api`.

| Guess | Use |
|---|---|
| `doc.WallTypes`, `doc.Families`, `doc.GetViews()` | `DB.FilteredElementCollector(doc).OfClass(DB.WallType)` (or `query.get_types_by_class`, `query.get_all_views`) |
| `doc.FilteredElementCollector` | `DB.FilteredElementCollector(doc)` |
| `Family.GetSymbols()` | `family.GetFamilySymbolIds()` |
| `Parameter.Value` | `AsDouble()`, `AsString()`, `AsInteger()`, `AsElementId()`; rpw's `db.Element(e).parameters["Name"].value` |
| `doc.NewDirectShape`, `DirectShape.Create` | `DB.DirectShape.CreateElement(doc, category_id)` + `SetShape` |
| `doc.Create.NewCeiling` | `DB.Ceiling.Create` or `create.create_ceiling` |
| `Plane.Create(origin, normal)` | `DB.Plane.CreateByNormalAndOrigin(normal, origin)` |
| `CurveLoop.Create(curve_array)` | append each curve to `DB.CurveLoop()` with `loop.Append(curve)` |
| `Edge.Curve`, `face.Surface` | `edge.AsCurve()`; for a `PlanarFace`, `face.Origin` and `face.FaceNormal` |
| `BooleanOperationType.BoolCut` | `DB.BooleanOperationsUtils.ExecuteBooleanOperation(a, b, DB.BooleanOperationsType.Difference)` |
| `BuiltInParameter.WALL_HEIGHT`, `TYPE_MARK`, `ALL_MODEL_COMMENTS` | `WALL_USER_HEIGHT_PARAM`, `ALL_MODEL_TYPE_MARK`, `ALL_MODEL_INSTANCE_COMMENTS` |
| `view.SetCategoryHidden(category, True)` | `view.SetCategoryHidden(category.Id, True)` |
| `DB.RoomTagType`, `DB.StairsType`, `DB.StairsRun` | `DB.Architecture.RoomTagType`, `DB.Architecture.StairsType`, `DB.Architecture.StairsRun` |
| `symbol.FamilyPlacementType` | `symbol.Family.FamilyPlacementType` |
| `DB.Category.GetAllCategories()`, `OfClass(DB.Category)` | `doc.Settings.Categories` (categories aren't elements) |
| `floor.Symbol` | `floor.FloorType`, or `doc.GetElement(floor.GetTypeId())` for any element |
| `duct.MEPModel`, `pipe.MEPModel` | `duct.ConnectorManager` |
| `connector.Direction.X`, `connector.Diameter` | `connector.CoordinateSystem.BasisZ.X`, `connector.Radius * 2` |
| `BuiltInParameter.FAMILY_SYMBOL_WIDTH_PARAM`, `FLOOR_PARAM_STRUCTURE` | `FAMILY_WIDTH_PARAM`, `FLOOR_STRUCTURE_ID_PARAM` |
| `floor_type.Width`, `layer.LayerWidth` | `floor_type.GetCompoundStructure().GetWidth()`, `structure.GetLayerWidth(index)` |
| `.OfCategory(category)` or `.OfCategory(element_id)` | `.OfCategory(DB.BuiltInCategory.OST_X)`, or `.OfCategoryId(category.Id)` |
| `query.get_family_symbol(..., category=...)` | `query.find_family_symbol(type_name, family_name=..., category="OST_Doors")` |
| wall top constraint "Roof" through `WALL_HEIGHT_TYPE` | `update.attach_wall_tops(walls, roof)` when the running Revit API supports wall attachment; otherwise model the gable end explicitly |
