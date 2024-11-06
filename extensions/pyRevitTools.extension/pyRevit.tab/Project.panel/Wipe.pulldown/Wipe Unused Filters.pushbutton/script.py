from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit.compat import get_elementid_value_func


logger = script.get_logger()


class ViewFilterToPurge(forms.TemplateListItem):
    @property
    def name(self):
        return self.item.Name


views = DB.FilteredElementCollector(revit.doc)\
          .OfClass(DB.View)\
          .WhereElementIsNotElementType()\
          .ToElements()

filters = DB.FilteredElementCollector(revit.doc)\
            .OfClass(DB.ParameterFilterElement)\
            .ToElements()

usedFiltersSet = set()
allFilters = set()

get_elementid_value = get_elementid_value_func()

for flt in filters:
    allFilters.add(get_elementid_value(flt.Id))

# print('{} Filters found.'.format(len(allFilters)))

for v in views:
    if v.AreGraphicsOverridesAllowed():
        view_filters = v.GetFilters()
        for filter_id in view_filters:
            usedFiltersSet.add(get_elementid_value(filter_id))

if not allFilters:
    forms.alert('There are no filters available.')
    script.exit()

unusedFilters = allFilters - usedFiltersSet

if not unusedFilters:
    forms.alert('All filters are in use. No purging necessary.')
else:
    # ask user for wipe actions
    return_options = \
        forms.SelectFromList.show(
            [ViewFilterToPurge(revit.doc.GetElement(DB.ElementId(x)))
            for x in unusedFilters],
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
                logger.debug('Purging Filter: {0}\t{1}'
                                .format(vf.Id, vf.Name))
                try:
                    revit.doc.Delete(vf.Id)
                except Exception as del_err:
                    logger.error('Error purging filter: {} | {}'
                                    .format(vf.Name, del_err))
