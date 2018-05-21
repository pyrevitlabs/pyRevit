from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script


__doc__ = 'Deletes all view parameter filters that has not been '\
          'listed on any views. This includes sheets as well.'

logger = script.get_logger()


class ViewFilterToPurge:
    def __init__(self, filter_elid):
        self.state = False
        self.filter_el = revit.doc.GetElement(DB.ElementId(filter_elid))
        self.name = self.filter_el.Name


views = DB.FilteredElementCollector(revit.doc)\
          .OfClass(DB.View)\
          .WhereElementIsNotElementType()\
          .ToElements()

filters = DB.FilteredElementCollector(revit.doc)\
            .OfClass(DB.ParameterFilterElement)\
            .ToElements()

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
    except Exception:
        continue

if not allFilters:
    forms.alert('There are no filters available.')
    script.exit()

unusedFilters = allFilters - usedFiltersSet

if not unusedFilters:
    forms.alert('All filters are in use. No purging in necessary.')

# ask user for wipe actions
return_options = \
    forms.SelectFromList.show(
        [ViewFilterToPurge(x) for x in unusedFilters],
        title='Select Filters to Purge',
        width=500,
        button_name='Purge Filters',
        multiselect=True
        )

# print('{} Filters have not been used and will be purged.'
#        .format(len(unusedFilters)))

if return_options:
    with revit.Transaction('Purge Unused Filters'):
        for vf in return_options:
            if vf.state:
                logger.debug('Purging Filter: {0}\t{1}'
                             .format(vf.filter_el.Id, vf.name))
                try:
                    revit.doc.Delete(vf.filter_el.Id)
                except Exception as del_err:
                    logger.error('Error purging filter: {} | {}'
                                 .format(vf.name, del_err))
