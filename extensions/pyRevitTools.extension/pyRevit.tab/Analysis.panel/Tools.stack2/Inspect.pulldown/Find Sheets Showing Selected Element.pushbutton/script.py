"""Lists all sheets and views that the selected elements is visible in."""
#pylint: disable=E0401,C0103
from collections import defaultdict, namedtuple
from pyrevit import script
from pyrevit import revit, DB


__context__ = 'selection'


output = script.get_output()
selection = revit.get_selection()


VportView = namedtuple('VportView', ['viewport', 'view'])

cl_views = DB.FilteredElementCollector(revit.doc)
allsheets = cl_views.OfCategory(DB.BuiltInCategory.OST_Sheets) \
                    .WhereElementIsNotElementType() \
                    .ToElements()


sorted_sheets = sorted(allsheets, key=lambda x: x.SheetNumber)


def find_sheeted_views(target_sheet):
    return [VportView(revit.doc.GetElement(vp),
                      revit.doc.GetElement(revit.doc.GetElement(vp).ViewId))
            for vp in target_sheet.GetAllViewports()]


sheet_dict = defaultdict(list)
for sheet in sorted_sheets:
    for vpview_tuple in find_sheeted_views(sheet):
        view_els = DB.FilteredElementCollector(revit.doc,
                                               vpview_tuple.view.Id) \
                     .WhereElementIsNotElementType() \
                     .ToElementIds()

        # check if selected element is a viewport on a sheet
        if vpview_tuple.viewport.Id in selection.element_ids:
            sheet_dict[sheet].append(vpview_tuple)

        # check if view contains any of the selected elements
        for el_id in selection.element_ids:
            if el_id in view_els:
                sheet_dict[sheet].append(vpview_tuple)

output.print_md('### Sheets Containing the selected objects:')

for sheet in sheet_dict:
    output.print_md('-----\nSheet {}: **{} - {}**'
                    .format(output.linkify(sheet.Id),
                            sheet.SheetNumber,
                            sheet.Name))

    for vpview_tuple in sheet_dict[sheet]:
        print('\t\tViewport {}: {}'
              .format(output.linkify(vpview_tuple.viewport.Id),
                      revit.query.get_name(vpview_tuple.view)))
