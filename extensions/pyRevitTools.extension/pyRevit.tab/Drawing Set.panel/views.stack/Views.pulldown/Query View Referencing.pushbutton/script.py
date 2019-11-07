"""Query all selected views and determine if referenced or not."""
#pylint: disable=import-error,broad-except,invalid-name
from pyrevit import revit
from pyrevit import forms
from pyrevit import script


output = script.get_output()


selected_views = forms.select_views(title="Select Views to List", use_selection=True)

if selected_views:
    selected_option, switches = \
        forms.CommandSwitchWindow.show(
            ['List Referenced Views', 'List Non-Referenced Views'],
            switches={'Only Sheeted': False},
            message='Select search option:')

    list_nonsheeted = not switches['Only Sheeted']

    collector_func = \
        revit.query.yield_referenced_views \
            if selected_option == 'List Referenced Views' \
            else revit.query.yield_unreferenced_views

    for ref_viewid in collector_func(doc=revit.doc, all_views=selected_views):
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
