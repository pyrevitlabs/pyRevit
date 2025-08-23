from pyrevit import revit, forms, DB, EXEC_PARAMS

options = [
    DB.BuiltInCategory.OST_Grids,
    DB.BuiltInCategory.OST_Levels,
    DB.BuiltInCategory.OST_RvtLinks,
    DB.BuiltInCategory.OST_SectionBox,
]

category_map = {}
for cat in options:
    name = DB.LabelUtils.GetLabelFor(cat)
    category_map[name] = cat

# Add pseudo-category for DWG Imports
dwg_label = "Imported DWG Files"
category_map[dwg_label] = "DWG_IMPORT"

selection = forms.SelectFromList.show(
    sorted(category_map.keys()),
    multiselect=True,
    title="Select categories to %s"
    % ("UNPIN" if EXEC_PARAMS.config_mode else "PIN"),
    width=320,
    height=300,
)

if selection:
    elements_to_modify = []

    for name in selection:
        cat = category_map[name]
        if cat == "DWG_IMPORT":
            elements = (
                DB.FilteredElementCollector(revit.doc)
                .OfClass(DB.ImportInstance)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        else:
            elements = (
                DB.FilteredElementCollector(revit.doc)
                .OfCategory(cat)
                .WhereElementIsNotElementType()
                .ToElements()
            )

        for e in elements:
            if EXEC_PARAMS.config_mode:
                if e.Pinned:
                    elements_to_modify.append(e)
            else:
                if not e.Pinned:
                    elements_to_modify.append(e)

    if elements_to_modify:
        with revit.Transaction("Mass Unpin" if EXEC_PARAMS.config_mode else "Mass Pin"):
            for elem in elements_to_modify:
                elem.Pinned = not EXEC_PARAMS.config_mode
