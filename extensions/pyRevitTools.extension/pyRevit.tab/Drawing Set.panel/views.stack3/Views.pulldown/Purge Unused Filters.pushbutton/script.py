"""Deletes all view parameter filters that has not been listed on any views. This includes sheets as well."""

from scriptutils import logger
from revitutils import doc, uidoc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, \
                              View, ParameterFilterElement, Transaction, ElementId

views = FilteredElementCollector(doc).OfClass(View).WhereElementIsNotElementType().ToElements()
filters = FilteredElementCollector(doc).OfClass(ParameterFilterElement).ToElements()

usedFiltersSet = set()
allFilters = set()
for flt in filters:
    allFilters.add(flt.Id.IntegerValue)

print('{} Filters found.'.format(len(allFilters)))

for v in views:
    try:
        filters = v.GetFilters()
        for flid in filters:
            usedFiltersSet.add(flid.IntegerValue)
    except:
        continue

unusedFilters = allFilters - usedFiltersSet

if unusedFilters:
    print('{} Filters have not been used and will be purged.'.format(len(unusedFilters)))

    t = Transaction(doc, 'Purge Unused Filters')
    t.Start()

    for flid in unusedFilters:
        fl = doc.GetElement(ElementId(flid))
        print('Purging Filter: {0}\t{1}'.format(fl.Id, fl.Name))
        try:
            doc.Delete(ElementId(flid))
        except Exception as del_err:
            logger.error('Error purging filter: {} | {}'.format(fl.Name, del_err))

    t.Commit()
else:
    print('All filters are in use. No purging in necessary.')
