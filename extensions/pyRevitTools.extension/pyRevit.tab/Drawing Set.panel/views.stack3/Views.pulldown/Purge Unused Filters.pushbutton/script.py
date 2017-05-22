"""Deletes all view parameter filters that has not been listed on any views. This includes sheets as well."""

from scriptutils import logger
from scriptutils.userinput import SelectFromCheckBoxes
from revitutils import doc, uidoc
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, \
                              View, ParameterFilterElement, Transaction, ElementId

views = FilteredElementCollector(doc).OfClass(View).WhereElementIsNotElementType().ToElements()
filters = FilteredElementCollector(doc).OfClass(ParameterFilterElement).ToElements()

usedFiltersSet = set()
allFilters = set()
for flt in filters:
    allFilters.add(flt.Id.IntegerValue)

# print('{} Filters found.'.format(len(allFilters)))

for v in views:
    try:
        filters = v.GetFilters()
        for flid in filters:
            usedFiltersSet.add(flid.IntegerValue)
    except:
        continue

unusedFilters = allFilters - usedFiltersSet

if unusedFilters:
    # ask user for wipe actions
    class ViewFilterToPurge:
        def __init__(self, filter_elid):
            self.state = False
            self.filter_el = doc.GetElement(ElementId(filter_elid))
            self.name = self.filter_el.Name

    return_options = SelectFromCheckBoxes.show([ViewFilterToPurge(x) for x in unusedFilters],
                                               title='Select Filters to Purge', width=500, button_name='Purge Filters')

    # print('{} Filters have not been used and will be purged.'.format(len(unusedFilters)))

    if return_options:
        t = Transaction(doc, 'Purge Unused Filters')
        t.Start()

        for vf in return_options:
            if vf.state:
                print('Purging Filter: {0}\t{1}'.format(vf.filter_el.Id, vf.name))
                try:
                    doc.Delete(vf.filter_el.Id)
                except Exception as del_err:
                    logger.error('Error purging filter: {} | {}'.format(vf.name, del_err))

        t.Commit()
else:
    print('All filters are in use. No purging in necessary.')
