from pyrevit import revit, script, DB

doc = revit.doc
logger = script.get_logger()
output = script.get_output()
output.close_others()

elements = revit.query.get_elements_by_class(DB.FamilyInstance, doc=doc)

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
            ("coarse", DB.ViewDetailLevel.Coarse),
            ("medium", DB.ViewDetailLevel.Medium),
            ("fine", DB.ViewDetailLevel.Fine),
        ]:
            try:
                geom_objs = revit.query.get_geometry(element, detail_level=opt)

                # Filter for solids and count triangles
                total_triangles = 0
                for geom in geom_objs:
                    if isinstance(geom, DB.Solid) and geom.Faces.Size > 0:
                        for face in geom.Faces:
                            mesh = face.Triangulate()
                            if mesh is not None:
                                total_triangles += mesh.NumTriangles

                counts[level_name] = total_triangles
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
else:
    logger.error("No families with solid geometry found")
    script.exit()

# Sort by fine detail count (or change to coarse/medium as needed)
table_data_sorted = sorted(table_data[:-1], key=lambda x: x[3]) + [table_data[-1]]

output.print_table(
    table_data_sorted,
    ["Name", "Coarse", "Medium", "Fine"],
    last_line_style="color:white;font-weight: bolder; background-color: gray;",
)
