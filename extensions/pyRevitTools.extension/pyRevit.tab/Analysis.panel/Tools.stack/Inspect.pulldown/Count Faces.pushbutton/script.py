from pyrevit import revit, script, DB

doc = revit.doc
# currView = revit.active_view

# Get the output window
output = script.get_output()
output.close_others()


# Get Elements of the FamilyInstance Class
elements = (
    DB.FilteredElementCollector(doc)
    .OfClass(DB.FamilyInstance)
    .WhereElementIsNotElementType()
    .ToElements()
)

grand_total = []
table_data = []
elements_name = []
elements_count = []
elements_category = []
elements_type = []

opt = DB.Options()

for element in elements:
    total_triangles = []
    typeId = element.GetTypeId()
    if typeId not in elements_type:
        elements_type.append(typeId)
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
                else:
                    pass
            geometry_set.Dispose()
            total_triangles = sum(total_triangles)
            if total_triangles != 0:
                elements_count.append(total_triangles)
                elements_name.append(
                    output.linkify(element.Id)
                    + "**"
                    + element.Name
                    + "** (*Category*: "
                    + element.Category.Name
                    + ")"
                )
                grand_total.append(total_triangles)
        except:
            pass

# adding grand total and making a dictionary out of it
elements_count.append(sum(grand_total))
elements_name.append("Grand Total")
my_dict = dict(zip(elements_name, elements_count))

# output as a table
output.print_table(
    sorted(my_dict.items(), key=lambda item: item[1]),
    ["Name", "Count"],
    last_line_style="color:white;font-weight: bolder; background-color: gray;",
)
