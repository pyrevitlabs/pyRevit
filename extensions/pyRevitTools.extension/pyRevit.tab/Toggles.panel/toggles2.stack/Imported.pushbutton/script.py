"""Toggles visibility of imported categories on current view."""

from pyrevit import revit, forms, DB

def vg_parameter_controlled_by_template(view, built_in_parameter):
    """
    Checks if certain view parameter is overrided by template
    """
    if view.ViewTemplateId == DB.ElementId.InvalidElementId:
        return False
    view_template = view.Document.GetElement(view.ViewTemplateId)
    if DB.ElementId(int(built_in_parameter)) in view_template.GetNonControlledTemplateParameterIds():
        return False
    else:
        return True

@revit.carryout('Toggle Imported')
def toggle_imported():
    aview = revit.active_view
    # check if 'Imported' is overrided by Template. If so, enable temporary view
    if vg_parameter_controlled_by_template(aview, DB.BuiltInParameter.VIS_GRAPHICS_IMPORT):
        if not aview.IsTemporaryViewPropertiesModeEnabled():
            aview.EnableTemporaryViewPropertiesMode(aview.ViewTemplateId)
    aview.AreImportCategoriesHidden = \
        not aview.AreImportCategoriesHidden


toggle_imported()
