import sys

from pyrevit import framework
from pyrevit import forms
from pyrevit import revit, DB, UI
from pyrevit import script


__doc__ = 'Asks user to select the viewport types to be converted and the '\
          'viewport type to be replaced with. I made this tool to fix a '\
          'problem with viewport types duplicating themselves '\
          'during a project and would become unpurgable viewport types.'


logger = script.get_logger()


class ViewPortType:
    def __init__(self, rvt_element_type):
        self._rvt_type = rvt_element_type

    def __str__(self):
        return revit.query.get_name(self._rvt_type)

    def __repr__(self):
        return '<{} Name:{} Id:{}>'\
               .format(self.__class__.__name__,
                       revit.query.get_name(self._rvt_type),
                       self._rvt_type.Id.IntegerValue)

    def __lt__(self, other):
        return str(self) < str(other)

    @property
    def name(self):
        return str(self)

    def get_rvt_obj(self):
        return self._rvt_type

    def find_linked_elements(self):
        with revit.DryTransaction("Search for linked elements",
                                  clear_after_rollback=True):
            linked_element_ids = revit.doc.Delete(self._rvt_type.Id)

        return linked_element_ids


# Collect viewport types
all_element_types = \
    DB.FilteredElementCollector(revit.doc)\
      .OfClass(framework.get_type(DB.ElementType))\
      .ToElements()

all_viewport_types = \
    [ViewPortType(x) for x in all_element_types if x.FamilyName == 'Viewport']

logger.debug('Viewport types: {}'.format(all_viewport_types))

# Ask user for viewport types to be purged
purge_vp_types = \
    forms.SelectFromList.show(sorted(all_viewport_types),
                              title='Select Types to be Converted',
                              multiselect=True)

if not purge_vp_types:
    sys.exit()

for purged_vp_type in purge_vp_types:
    logger.debug('Viewport type to be purged: {}'.format(repr(purged_vp_type)))

# Ask user for replacement viewport type
dest_vp_types = \
    forms.SelectFromList.show(
        sorted([x for x in all_viewport_types if x not in purge_vp_types]),
        title='Select Replacement Type',
        multiselect=False
        )

if dest_vp_types:
    dest_vp_typeid = dest_vp_types.get_rvt_obj().Id
else:
    sys.exit()


# Collect all elements that are somehow linked to the
# viewport types to be purged
purge_dict = {}
for purge_vp_type in purge_vp_types:
    logger.info('Finding all viewports of type: {}'.format(purge_vp_type.name))
    logger.debug('Purging: {}'.format(repr(purge_vp_type)))
    linked_elements = purge_vp_type.find_linked_elements()
    logger.debug('{} elements are linked to this viewport type.'
                 .format(len(linked_elements)))
    purge_dict[purge_vp_type.name] = linked_elements


# Perform cleanup
with revit.TransactionGroup('Fixed Unpurgable Viewport Types'):
    # Correct all existing viewports that use the viewport types to be purged
    # Collect viewports and find the ones that use the purging viewport types
    all_viewports = \
        DB.FilteredElementCollector(revit.doc)\
          .OfClass(framework.get_type(DB.Viewport))\
          .ToElements()

    purge_vp_ids = [x.get_rvt_obj().Id for x in purge_vp_types]
    with revit.Transaction('Correct Viewport Types'):
        for vp in all_viewports:
            if vp.GetTypeId() in purge_vp_ids:
                try:
                    # change their type to the destination type
                    logger.debug('Changing viewport type for '
                                 'viewport with id: {}'.format(vp.Id))
                    vp.ChangeTypeId(dest_vp_typeid)
                except Exception as change_err:
                    logger.debug('Can not change type for '
                                 'viewport with id: {} | {}'
                                 .format(vp.Id, change_err))

    # Correct all hidden viewport elements that use
    # the viewport types to be purged
    with revit.Transaction('Correct Hidden Viewport Types'):
        for vp_type_name, linked_elements in purge_dict.items():
            has_error = False
            logger.info('Converting all viewports of type: {}'
                        .format(vp_type_name))

            for linked_elid in linked_elements:
                linked_el = revit.doc.GetElement(linked_elid)
                try:
                    if isinstance(linked_el, DB.Viewport) \
                            and linked_el.GetTypeId() in purge_vp_ids:
                        logger.debug('Changing viewport type for '
                                     'hidden viewport with id: {}'
                                     .format(linked_el.Id))
                        linked_el.ChangeTypeId(dest_vp_typeid)
                except Exception as change_err:
                    has_error = True
                    logger.debug('Can not change type for hidden '
                                 'viewport with id: {} | {}'
                                 .format(linked_el.Id, change_err))
            if has_error:
                logger.warning('Exceptions occured while converting '
                               'viewport type: {}\n'
                               'This is minor and the type '
                               'might still be purgable.'.format(vp_type_name))


forms.alert('Conversion Completed.\n'
            'Now you can remove the unused viewport '
            'types using Purge tool.')
