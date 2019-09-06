"""Add selected view to selected sheets."""

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__author__ = 'Dan Mapes'
__doc__ = 'Adds the selected views (callouts, sections, elevations) to the '\
          'selected sheets. Model views will only be added to the first '\
          'selected sheet since they can not exist on multiple sheets. ' \
          'The command defaults to active view if no views are selected.' \
          '\n\nShift+Click:\n' \
          'Pick source views from list instead of selection or active view.'


logger = script.get_logger()


selected_views = forms.select_views(use_selection=True)


if selected_views:
    logger.debug('Selected views: {}'.format(len(selected_views)))
    # get the destination sheets from user
    dest_sheets = forms.select_sheets()

    if dest_sheets:
        logger.debug('Selected sheets: {}'.format(len(dest_sheets)))
        with revit.Transaction("Add Views to Sheets"):
            for selected_view in selected_views:
                for sheet in dest_sheets:
                    logger.debug('Adding: %s',
                                 revit.query.get_name(selected_view))
                    try:
                        DB.Viewport.Create(revit.doc,
                                           sheet.Id,
                                           selected_view.Id,
                                           DB.XYZ(0, 0, 0))
                    except Exception as place_err:
                        logger.debug('Error placing view on sheet: {} -> {}'
                                     .format(selected_view.Id, sheet.Id))
else:
    forms.alert('No views selected.')
