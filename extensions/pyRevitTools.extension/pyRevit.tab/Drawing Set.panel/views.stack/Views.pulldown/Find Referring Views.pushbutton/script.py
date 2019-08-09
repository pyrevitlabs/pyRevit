"""List all view that are referring the selected viewports or active view."""
#pylint: disable=import-error,broad-except,invalid-name
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


logger = script.get_logger()
output = script.get_output()


selection = revit.get_selection()
if not selection:
    activeview = revit.active_view
    if revit.query.can_refer_other_views(activeview):
        selection = [activeview]


if selection:
    list_nonsheeted = \
        forms.CommandSwitchWindow.show(
            ['All Views',
             'Only Sheeted Views'],
            message='Select listing option:') == 'All Views'


    print('Collecting all references in all view...')
    for vp in selection:
        if isinstance(vp, DB.Viewport):
            target_view = revit.doc.GetElement(vp.ViewId)
        else:
            target_view = vp

        target_viewname = revit.query.get_name(target_view)
        title = \
            target_view.Parameter[DB.BuiltInParameter.VIEW_DESCRIPTION]\
                        .AsString()
        print('\nTarget View: \"{}\" referenced by:'
              .format(title if title else target_viewname))

        for ref_viewid in revit.query.yield_referring_views(target_view):
            ref_view = revit.doc.GetElement(ref_viewid)
            sheetrefinfo = revit.query.get_view_sheetrefinfo(ref_view)
            if sheetrefinfo:
                print('\t\t{} \"{}\" {} {}/{} (\"{}\")'
                      .format(output.linkify(ref_viewid),
                              revit.query.get_name(ref_view,
                                                   title_on_sheet=True),
                              'referred to on' if sheetrefinfo.ref_viewid \
                                  else 'placed on',
                              sheetrefinfo.detail_num,
                              sheetrefinfo.sheet_num,
                              sheetrefinfo.sheet_name))
            elif list_nonsheeted:
                print('\t\t{} \"{}\"'
                      .format(output.linkify(ref_viewid),
                              revit.query.get_name(ref_view,
                                                   title_on_sheet=True)))
