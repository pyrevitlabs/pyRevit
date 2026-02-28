# -*- coding: utf-8 -*-
"""Convert Imported CAD Symbol to FreeForm or DirectShape Elements."""

from pyrevit.framework import List
from pyrevit import forms
from pyrevit import revit, DB
from pyrevit import script


logger = script.get_logger()


# make sure active document is a family
forms.check_familydoc(exitscript=True)

selection = revit.get_selection()
if selection:
    cad_imports = [e for e in selection if isinstance(e, DB.ImportInstance)]
    if not cad_imports:
        forms.alert("No CAD import found in selection.", exitscript=True)
    cad_import = cad_imports[0]
    if len(cad_imports) > 1:
        forms.alert("Multiple CAD imports selected. Using the first one.")
else:
    cad_import = revit.pick_element("Select an imported instance")
    if not cad_import:
        script.exit()
    if not isinstance(cad_import, DB.ImportInstance):
        forms.alert("Selected element is not a CAD import.", exitscript=True)


cad_trans = cad_import.GetTransform()
cad_type = cad_import.Document.GetElement(cad_import.GetTypeId())
cad_name = revit.query.get_name(cad_type)

family_cat = revit.doc.OwnerFamily.FamilyCategory

geo_elem = cad_import.get_Geometry(DB.Options())
geo_elements = []
for geo in geo_elem:
    logger.debug(geo)
    if isinstance(geo, DB.GeometryInstance):
        geo_elements.extend([x for x in geo.GetSymbolGeometry()])

solid_count = 0
mesh_count = 0
with revit.Transaction("Convert CAD Import to FreeForm/DirectShape"):
    for gel in geo_elements:
        logger.debug(gel)
        if isinstance(gel, DB.Solid):
            # if hasattr(gel, 'Volume') and gel.Volume > 0.0:
            DB.FreeFormElement.Create(revit.doc, gel)
            solid_count += 1
        elif isinstance(gel, DB.Mesh):
            builder = DB.TessellatedShapeBuilder()
            builder.OpenConnectedFaceSet(False)

            triangles = [gel.Triangle[x] for x in range(0, gel.NumTriangles)]
            for t in triangles:
                p1 = cad_trans.OfPoint(t.Vertex[0])
                p2 = cad_trans.OfPoint(t.Vertex[1])
                p3 = cad_trans.OfPoint(t.Vertex[2])
                tface = DB.TessellatedFace(
                    List[DB.XYZ]([p1, p2, p3]), DB.ElementId.InvalidElementId
                )
                builder.AddFace(tface)

            builder.CloseConnectedFaceSet()
            builder.Target = DB.TessellatedShapeBuilderTarget.AnyGeometry
            builder.Fallback = DB.TessellatedShapeBuilderFallback.Mesh
            builder.Build()

            ds = DB.DirectShape.CreateElement(revit.doc, family_cat.Id)
            ds.ApplicationId = "B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D"
            ds.ApplicationDataId = ""
            ds.SetShape(builder.GetBuildResult().GetGeometricalObjects())
            ds.Name = cad_name
            mesh_count += 1

if not solid_count and not mesh_count:
    forms.alert(
        "No solids or meshes found in the CAD import. Nothing was converted.",
        exitscript=True,
    )
logger.info(
    "Converted {} solids and {} meshes from {}".format(
        solid_count, mesh_count, cad_name
    )
)
