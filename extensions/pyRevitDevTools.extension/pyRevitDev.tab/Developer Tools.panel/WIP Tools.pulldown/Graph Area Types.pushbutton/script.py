"""Display the total area of different area types in a graph."""

from pyrevit import revit, DB
from pyrevit import script


doc = revit.doc
output = script.get_output()

areas = DB.FilteredElementCollector(doc) \
          .OfCategory(DB.BuiltInCategory.OST_Areas) \
          .WhereElementIsNotElementType().ToElements()


total = {}
for area in areas:
    try:
        area_type = area.LookupParameter('Area Type').AsValueString()
        if area_type.lower() != '(none)':
            if area_type in total:
                total[area_type] += area.Area
            else:
                total[area_type] = area.Area
    except Exception:
        continue

output.set_width(400)
output.set_height(450)

chart = output.make_pie_chart()
chart.data.labels = total.keys()
area_dataset = chart.data.new_dataset('area types')
area_dataset.data = [round(v, 2) for v in total.values()]

chart.randomize_colors()
chart.draw()
