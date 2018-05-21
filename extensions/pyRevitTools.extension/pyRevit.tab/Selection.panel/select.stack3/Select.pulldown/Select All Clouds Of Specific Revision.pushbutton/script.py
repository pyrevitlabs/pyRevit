from pyrevit import revit, DB
from pyrevit import forms


__doc__ = 'Selects all revision clouds of a sepecific revision. '\
          'This is helpful for setting a parameter or comment ' \
          'on all the revision clouds at once.'


def select_clouds(revision_element):
    cl = DB.FilteredElementCollector(revit.doc)
    revclouds = cl.OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
                  .WhereElementIsNotElementType()

    clouds = []

    for revcloud in revclouds:
        if revcloud.RevisionId == revision_element.Id:
            clouds.append(revcloud.Id)

    revit.get_selection().set_to(clouds)


revision = forms.select_revisions(button_name='Select Revision Clouds',
                                  multiple=False)
if revision:
    select_clouds(revision)
