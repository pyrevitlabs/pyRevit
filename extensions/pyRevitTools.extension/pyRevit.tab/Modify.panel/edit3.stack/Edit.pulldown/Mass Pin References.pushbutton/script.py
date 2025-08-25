from pyrevit import revit, forms, DB, EXEC_PARAMS

category_map = {}

category_map["Imported CAD Files"] = "CAD_IMPORT"
category_map["Project Base Point"] = "PROJECT_BASE_POINT"
category_map["Survey Point"] = "SURVEY_POINT"
options = [
    DB.BuiltInCategory.OST_Grids,
    DB.BuiltInCategory.OST_Levels,
    DB.BuiltInCategory.OST_RvtLinks,
    DB.BuiltInCategory.OST_SectionBox,
]
for cat in options:
    name = DB.LabelUtils.GetLabelFor(cat)
    category_map[name] = cat

selection = forms.SelectFromList.show(
    sorted(category_map.keys()),
    multiselect=True,
    title="Select categories to %s" % ("UNPIN" if EXEC_PARAMS.config_mode else "PIN"),
    width=320,
    height=340,
)

if selection:
    elements_to_modify = []

    for name in selection:
        cat = category_map[name]
        if cat == "CAD_IMPORT":
            elements = (
                DB.FilteredElementCollector(revit.doc)
                .OfClass(DB.ImportInstance)
                .WhereElementIsNotElementType()
                .ToElements()
            )
        elif cat in ["PROJECT_BASE_POINT", "SURVEY_POINT"]:
            elements = []
            basepoints = (
                DB.FilteredElementCollector(revit.doc)
                .OfClass(DB.BasePoint)
                .WhereElementIsNotElementType()
                .ToElements()
            )
            for bp in basepoints:
                if (cat == "PROJECT_BASE_POINT" and not bp.IsShared) or (
                    cat == "SURVEY_POINT" and bp.IsShared
                ):
                    elements.append(bp)
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
