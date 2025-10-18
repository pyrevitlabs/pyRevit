from pyrevit import revit, DB, UI, forms


doc = revit.doc
uidoc = revit.uidoc
curview = revit.active_view


def reorient(view):
    try:
        world_normal = None

        reference = uidoc.Selection.PickObject(
            UI.Selection.ObjectType.PointOnElement, "Pick a face to orient view to"
        )

        instance = doc.GetElement(reference.ElementId)
        picked_point = reference.GlobalPoint

        if isinstance(instance, DB.RevitLinkInstance):
            linked_doc = instance.GetLinkDocument()
            linked_element_id = reference.LinkedElementId
            element = linked_doc.GetElement(linked_element_id)
            transform = instance.GetTransform()
        else:
            element = instance
            transform = DB.Transform.Identity

        # Get geometry
        options = DB.Options()
        options.ComputeReferences = True
        options.IncludeNonVisibleObjects = True
        options.DetailLevel = curview.DetailLevel

        geom_elem = element.get_Geometry(options)

        def extract_solids(geom_element):
            solids = []
            for geom_obj in geom_element:
                if isinstance(geom_obj, DB.Solid) and geom_obj.Faces.Size > 0:
                    solids.append(geom_obj)
                elif isinstance(geom_obj, DB.GeometryInstance):
                    solids.extend(extract_solids(geom_obj.GetInstanceGeometry()))
            return solids

        solids = extract_solids(geom_elem)

        # Find face that contains the picked point
        target_face = None
        for solid in solids:
            for face in solid.Faces:
                try:
                    result = face.Project(picked_point)
                    if result and result.XYZPoint.DistanceTo(picked_point) < 1e-6:
                        target_face = face
                        break
                except Exception:
                    continue
            if target_face:
                break

        if not target_face:
            forms.alert("Could not find face at the picked point.", exitscript=True)

        local_normal = target_face.ComputeNormal(DB.UV(0.5, 0.5)).Normalize()
        world_normal = transform.OfVector(local_normal).Normalize()

        # Compute face origin in world coordinates
        local_origin = target_face.Evaluate(DB.UV(0.5, 0.5))
        world_origin = transform.OfPoint(local_origin)

        # Create plane and sketch plane
        base_plane = DB.Plane.CreateByNormalAndOrigin(world_normal, world_origin)

        with revit.Transaction("Orient to Face"):
            sketch_plane = DB.SketchPlane.Create(doc, base_plane)
            view_direction = view.ViewDirection.Normalize()
            if view_direction.DotProduct(world_normal) > 0:
                world_normal = world_normal.Negate()
            view.OrientTo(world_normal)
            view.SketchPlane = sketch_plane

        uidoc.RefreshActiveView()

    except Exception as ex:
        forms.alert("Error: {0}".format(str(ex)))


if isinstance(curview, DB.View3D):
    reorient(curview)
else:
    forms.alert("You must be on a 3D view for this tool to work.")
