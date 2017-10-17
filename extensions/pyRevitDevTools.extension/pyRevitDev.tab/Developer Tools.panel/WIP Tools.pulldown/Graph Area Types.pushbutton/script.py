"""Display the total area of different area types in a graph."""

from scriptutils import this_script
from revitutils import doc, selection

from Autodesk.Revit.DB import FilteredElementCollector, ElementId, BuiltInCategory, Area


areas = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Areas)\
                                     .WhereElementIsNotElementType().ToElements()


total = dict()
for area in areas:
    try:
        area_type = area.LookupParameter('Area Type').AsValueString()
        if area_type.lower() != '(none)':
            if area_type in total:
                total[area_type] += area.Area
            else:
                total[area_type] = area.Area
    except:
        continue

this_script.output.set_width(400)
this_script.output.set_height(450)

chart = this_script.output.make_pie_chart()
chart.data.labels = total.keys()
area_dataset = chart.data.new_dataset('area types')
area_dataset.data = [round(v, 2) for v in total.values()]

chart.randomize_colors()
chart.draw()
