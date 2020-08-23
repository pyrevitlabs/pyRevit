"""Batch duplicates the selected views with or without detailing."""

from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()


def duplicableview(view):
    return view.CanViewBeDuplicated(DB.ViewDuplicateOption.Duplicate)


def duplicate_views(viewlist, with_detailing=True):
    dup_view_ids = []
    with revit.Transaction('Duplicate selected views'):
        for el in viewlist:
            if with_detailing:
                dupop = DB.ViewDuplicateOption.WithDetailing
            else:
                dupop = DB.ViewDuplicateOption.Duplicate

            try:
                dup_view_ids.append(el.Duplicate(dupop))
            except Exception as duplerr:
                logger.error('Error duplicating view "{}" | {}'
                             .format(revit.query.get_name(el), duplerr))
        if dup_view_ids:
            revit.doc.Regenerate()
    return dup_view_ids

selected_views = forms.select_views(filterfunc=duplicableview,
                                    use_selection=True)

if selected_views:
    selected_option = \
        forms.CommandSwitchWindow.show(
            ['WITH Detailing',
             'WITHOUT Detailing'],
            message='Select duplication option:'
            )

    if selected_option:
        dup_view_ids = duplicate_views(
            selected_views,
            with_detailing=True if selected_option == 'WITH Detailing'
            else False)
        if dup_view_ids:
            revit.get_selection().set_to(dup_view_ids)
