from pyrevit import revit, DB, UI


__doc__ = 'Uses the Worksharing tooltip to find out the '\
          'element creator and other info.'


selection = revit.get_selection()


if revit.doc.IsWorkshared:
    if selection and len(selection) == 1:
        wti = DB.WorksharingUtils.GetWorksharingTooltipInfo(
            revit.doc,
            selection.first.Id
            )

        UI.TaskDialog.Show('pyrevit',
                           'Creator: {0}\n'
                           'Current Owner: {1}\n'
                           'Last Changed By: {2}'.format(wti.Creator,
                                                         wti.Owner,
                                                         wti.LastChangedBy))
    else:
        UI.TaskDialog.Show('pyrevit', 'Exactly one element must be selected.')
else:
    UI.TaskDialog.Show('pyrevit', 'Model is not workshared.')
