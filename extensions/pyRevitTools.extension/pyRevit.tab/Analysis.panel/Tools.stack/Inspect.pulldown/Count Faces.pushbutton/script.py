from pyrevit import revit, script, DB

doc = revit.doc
output = script.get_output()
output.close_others()

elements = (
    DB.FilteredElementCollector(doc)
    .OfClass(DB.FamilyInstance)
    .WhereElementIsNotElementType()
    .ToElements()
)

# Setup options for each detail level
opt_coarse = DB.Options()
opt_coarse.DetailLevel = DB.ViewDetailLevel.Coarse

opt_medium = DB.Options()
opt_medium.DetailLevel = DB.ViewDetailLevel.Medium

opt_fine = DB.Options()
opt_fine.DetailLevel = DB.ViewDetailLevel.Fine

# Storage
processed_types = {}  # typeId: {name, coarse, medium, fine}

for element in elements:
    typeId = element.GetTypeId()

    if typeId not in processed_types:
        element_name = (
            output.linkify(element.Id)
            + "**"
            + element.Name
            + "** (*Category*: "
            + element.Category.Name
            + ")"
        )

        # Process each detail level
        counts = {}
        for level_name, opt in [
            ("coarse", opt_coarse),
            ("medium", opt_medium),
            ("fine", opt_fine),
        ]:
            total_triangles = []
            geometry_set = element.get_Geometry(opt)

            try:
                for geometry in geometry_set:
                    if isinstance(geometry, DB.Solid) and geometry.Faces.Size > 0:
                        nbrtriangle = sum(
                            [
                                f.Triangulate().NumTriangles
                                for f in geometry.Faces
                                if f.Triangulate() is not None
                            ]
                        )
                        total_triangles.append(nbrtriangle)
                    elif isinstance(geometry, DB.GeometryInstance):
                        for instObj in geometry.SymbolGeometry:
                            if isinstance(instObj, DB.Solid) and instObj.Faces.Size > 0:
                                nbrtriangle = sum(
                                    [
                                        f.Triangulate().NumTriangles
                                        for f in instObj.Faces
                                        if f.Triangulate() is not None
                                    ]
                                )
                                total_triangles.append(nbrtriangle)

                geometry_set.Dispose()
                counts[level_name] = sum(total_triangles)
            except Exception:
                counts[level_name] = 0

        # Only add if at least one level has triangles
        if any(counts.values()):
            processed_types[typeId] = {
                "name": element_name,
                "coarse": counts["coarse"],
                "medium": counts["medium"],
                "fine": counts["fine"],
            }

# Prepare table data
table_data = []
for type_info in processed_types.values():
    table_data.append(
        [type_info["name"], type_info["coarse"], type_info["medium"], type_info["fine"]]
    )

# Add grand totals
if table_data:
    grand_coarse = sum([row[1] for row in table_data])
    grand_medium = sum([row[2] for row in table_data])
    grand_fine = sum([row[3] for row in table_data])

    table_data.append(["Grand Total", grand_coarse, grand_medium, grand_fine])

# Sort by fine detail count (or change to coarse/medium as needed)
table_data_sorted = sorted(table_data[:-1], key=lambda x: x[3]) + [table_data[-1]]

output.print_table(
    table_data_sorted,
    ["Name", "Coarse", "Medium", "Fine"],
    last_line_style="color:white;font-weight: bolder; background-color: gray;",
)
