"""Lists all sheets and views that the selected elements is visible in."""

from collections import defaultdict, namedtuple
from scriptutils import this_script
from revitutils import doc, uidoc, selection
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory


VportView = namedtuple('VportView', ['viewport', 'view'])

cl_views = FilteredElementCollector(doc)
allsheets = cl_views.OfCategory(BuiltInCategory.OST_Sheets) \
                    .WhereElementIsNotElementType() \
                    .ToElements()

sorted_sheets = sorted(allsheets, key=lambda x: x.SheetNumber)

def find_sheeted_views(sheet):
    return [VportView(doc.GetElement(vp),
                      doc.GetElement(doc.GetElement(vp).ViewId)) \
                for vp in sheet.GetAllViewports()]


sheet_dict = defaultdict(list)
for sheet in sorted_sheets:
    for vpview_tuple in find_sheeted_views(sheet):
        view_els = FilteredElementCollector(doc, vpview_tuple.view.Id) \
                   .WhereElementIsNotElementType() \
                   .ToElementIds()

        for el_id in selection.element_ids:
            if el_id in view_els:
                sheet_dict[sheet].append(vpview_tuple)

this_script.output.print_md('### Sheets Containing the selected objects:')

for sheet in sheet_dict:
    this_script.output.print_md('-----\nSheet {}: **{} - {}**'
                                .format(this_script.output.linkify(sheet.Id),
                                        sheet.SheetNumber, sheet.Name))
    for vpview_tuple in sheet_dict[sheet]:
        print('\t\tVisible in View {}: {}'
              .format(this_script.output.linkify(vpview_tuple.viewport.Id),
                      vpview_tuple.view.ViewName))
