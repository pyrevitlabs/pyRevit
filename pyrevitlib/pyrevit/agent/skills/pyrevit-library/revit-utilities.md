# Revit utility classes

Revit keeps many operations in static helper classes named `...Utils` or `...Utilities`, not on the elements they act on. Nothing on a `Wall` tells you that its join behaviour lives in `WallUtils`, so look here before writing geometry math or concluding that the API can't do something. Then call `lookup_revit_api` with the class name for exact signatures.

Classes in `Autodesk.Revit.DB` are reached through the injected `DB` (`DB.ElementTransformUtils`). Classes in sub-namespaces need an import, shown in their row. This list was read from Revit 2025's API; older versions may lack a class or method.

## Moving, copying, mirroring

| Class | Use it for |
|---|---|
| `DB.ElementTransformUtils` | `MoveElement(s)`, `CopyElement(s)` (also between documents and views), `RotateElement(s)`, `MirrorElement(s)`, `CanMirrorElement`, `GetTransformFromViewToView` |

## Joins, cuts and hosts

| Class | Use it for |
|---|---|
| `DB.JoinGeometryUtils` | `JoinGeometry`, `UnjoinGeometry`, `SwitchJoinOrder`, `AreElementsJoined`, `GetJoinedElements` |
| `DB.WallUtils` | allow or disallow a wall's end join: `AllowWallJoinAtEnd`, `DisallowWallJoinAtEnd`, `IsWallJoinAllowedAtEnd` |
| `DB.HostObjectUtils` | face references of walls, floors, roofs and ceilings: `GetSideFaces(wall, DB.ShellLayerType.Interior)`, `GetTopFaces`, `GetBottomFaces` |
| `DB.SolidSolidCutUtils` | solid-solid cuts between elements: `AddCutBetweenSolids`, `RemoveCut`, `CanElementCutElement` |
| `DB.InstanceVoidCutUtils` | cut a host with a family's void: `AddInstanceVoidCut`, `RemoveInstanceVoidCut`, `CanBeCutWithVoid` |

**Face-based families on walls:** `HostObjectUtils.GetSideFaces` returns face references that `doc.Create.NewFamilyInstance(reference, point, direction, symbol)` accepts. This places work-plane-based families such as receptacles on a wall face:

```python
face_ref = list(DB.HostObjectUtils.GetSideFaces(wall, DB.ShellLayerType.Interior))[0]
face = wall.GetGeometryObjectFromReference(face_ref)
point = face.Project(DB.XYZ(x, y, height)).XYZPoint
receptacle = doc.Create.NewFamilyInstance(face_ref, point, DB.XYZ.BasisX, symbol)
```

The height of an instance placed this way is its `Location.Point.Z` less its level's elevation. Its `Elevation from Level` parameter reads 0.

## Geometry

| Class | Use it for |
|---|---|
| `DB.GeometryCreationUtilities` | build a `Solid` in memory: `CreateExtrusionGeometry`, `CreateRevolvedGeometry`, `CreateSweptGeometry`, `CreateLoftGeometry`, `CreateBlendGeometry`, ... (for clash checks, volumes, `DirectShape`) |
| `DB.BooleanOperationsUtils` | `ExecuteBooleanOperation(a, b, DB.BooleanOperationsType.Intersect)`, union, difference; `CutWithHalfSpace` |
| `DB.SolidUtils` | `CreateTransformed`, `Clone`, `SplitVolumes`, `TessellateSolidOrShell` |
| `DB.MathComparisonUtils` | tolerant comparisons: `IsAlmostEqual`, `IsAlmostZero`, `IsGreaterThan`, ... |
| `DB.FacetingUtils` | `ConvertTrianglesToQuads` for tessellated output |

## Families, masses and forms

| Class | Use it for |
|---|---|
| `DB.FamilyUtils` | `FamilyCanConvertToFaceHostBased`, `ConvertFamilyToFaceHostBased`, `GetProfileSymbols` |
| `DB.AdaptiveComponentInstanceUtils` | place and read adaptive components: `CreateAdaptiveComponentInstance`, `GetInstancePlacementPointElementRefIds`, ... |
| `DB.AdaptiveComponentFamilyUtils` | adaptive points inside an adaptive family |
| `DB.MassInstanceUtils` | mass floors and quantities: `AddMassLevelDataToMassInstance`, `GetGrossFloorArea`, `GetGrossVolume`, ... |
| `DB.FormUtils`, `DB.CurveByPointsUtils` | conceptual forms and curves by points |

## MEP

| Class | Import | Use it for |
|---|---|---|
| `MechanicalUtils` | `from Autodesk.Revit.DB.Mechanical import MechanicalUtils` | `ConnectAirTerminalOnDuct` (mount a terminal on a duct face), `BreakCurve`, duct placeholders (`ConvertDuctPlaceholders`, `ConnectDuctPlaceholdersAtElbow`/`Tee`/`Cross`) |
| `PlumbingUtils` | `from Autodesk.Revit.DB.Plumbing import PlumbingUtils` | `PlaceCapOnOpenEnds`, `HasOpenConnector`, `BreakCurve`, pipe placeholders |
| `DB.MEPSupportUtils` | | `CreateDuctworkStiffener` |
| `FabricationUtils` | `from Autodesk.Revit.DB.Fabrication import FabricationUtils` | `ValidateConnectivity`, `ExportToPCF` |

## Structure

| Class | Import | Use it for |
|---|---|---|
| `StructuralFramingUtils` | `from Autodesk.Revit.DB.Structure import StructuralFramingUtils` | beam ends: `AllowJoinAtEnd`, `DisallowJoinAtEnd`, `FlipEnds`, `GetEndReference`, `SetEndReference` |
| `StructuralSectionUtils` | `from Autodesk.Revit.DB.Structure.StructuralSections import StructuralSectionUtils` | `GetStructuralSection`, `SetStructuralSection` |
| `RebarSpliceUtils`, `RebarSpliceTypeUtils` | `from Autodesk.Revit.DB.Structure import RebarSpliceUtils, RebarSpliceTypeUtils` | splice rebar and manage splice types |

## Views, annotation, parts and assemblies

| Class | Use it for |
|---|---|
| `DB.DetailElementOrderUtils` | draw order of detail elements: `BringToFront`, `SendToBack`, ... |
| `DB.AnnotationMultipleAlignmentUtils` | align tags and annotations, moving them with their leaders |
| `DB.ReferenceableViewUtils` | `GetReferencedViewId`, `ChangeReferencedView` for reference sections and callouts |
| `DB.AssemblyViewUtils` | views, schedules and sheets for an assembly: `Create3DOrthographic`, `CreatePartList`, `CreateSheet`, ... |
| `DB.PartUtils` | parts: `CreateParts`, `DivideParts`, `CreateMergedPart`, ... |

## Units, parameters and names

| Class | Use it for |
|---|---|
| `DB.UnitUtils` | `ConvertToInternalUnits(value, DB.UnitTypeId.Millimeters)`, `ConvertFromInternalUnits`, `GetAllUnits`, ... |
| `DB.UnitFormatUtils` | `Format` a value as Revit displays it; `TryParse` text such as `3'-6"` |
| `DB.LabelUtils` | user-visible names: `GetLabelForBuiltInParameter`, `GetLabelForSpec`, `GetLabelForUnit`, ... |
| `DB.SpecUtils`, `DB.ParameterUtils` | data types and built-in parameters: `GetAllSpecs`, `GetAllBuiltInParameters`, `GetBuiltInParameter`, ... |
| `DB.ParameterFilterUtilities` | what a view filter may use: `GetAllFilterableCategories`, `GetFilterableParametersInCommon`, `IsParameterApplicable` |
| `DB.NamingUtils` | `IsValidName` before naming a view, type or sheet; `CompareNames` |

## Files, links and collaboration

| Class | Import | Use it for |
|---|---|---|
| `DB.ModelPathUtils` | | `ConvertUserVisiblePathToModelPath`, `ConvertModelPathToUserVisiblePath`, cloud paths |
| `DB.WorksharingUtils` | | `GetCheckoutStatus`, `CheckoutElements`, `CheckoutWorksets`, `CreateNewLocal`, `RelinquishOwnership`, ... |
| `DB.ExternalFileUtils` | | `GetAllExternalFileReferences`, `GetExternalFileReference` (links, keynotes) |
| `DB.ExternalResourceUtils` | | `GetAllExternalResourceReferences` |
| `DB.ExportUtils` | | `GetExportId`, `GetGBXMLDocumentId` |
| `DB.OptionalFunctionalityUtils` | | whether an import or export is installed: `IsDWGExportAvailable`, `IsIFCAvailable`, ... |
| `PointCloudFilterUtils` | `from Autodesk.Revit.DB.PointClouds import PointCloudFilterUtils` | `GetFilteredOutline` |
