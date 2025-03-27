from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms

logger = script.get_logger()

selection = revit.get_selection()

if len(selection) > 0:
    for el in selection:
        linked_model_name = ""
        if isinstance(el, DB.RevitLinkInstance):
            linked_model_name = "ZL_RVT_" + el.Name.split(":")[0].split(".rvt")[0]
        elif isinstance(el, DB.ImportInstance):
            linked_model_name = (
                "ZL_DWG_"
                + el.Parameter[DB.BuiltInParameter.IMPORT_SYMBOL_NAME]
                .AsString()
                .split(".dwg")[0]
            )
        if linked_model_name:
            with revit.Transaction("Create Workset for linked model"):
                if not revit.doc.IsWorkshared and revit.doc.CanEnableWorksharing:
                    revit.doc.EnableWorksharing("Shared Levels and Grids", "Workset1")
                try:
                    newWs = DB.Workset.Create(revit.doc, linked_model_name)
                    worksetParam = el.Parameter[
                        DB.BuiltInParameter.ELEM_PARTITION_PARAM
                    ]
                    worksetParam.Set(newWs.Id.IntegerValue)
                except Exception as e:
                    print(
                        "Workset: {} already exists\nError: {}".format(
                            linked_model_name, e
                        )
                    )
else:
    forms.alert("At least one linked element must be selected.")
