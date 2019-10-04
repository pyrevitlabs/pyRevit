"""Explodes all instances of the selected groups and removes
the group definition from project browser.
"""
#pylint: disable=import-error,invalid-name,broad-except
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script


__context__ = 'selection'


logger = script.get_logger()


group_types = set()
for el in revit.get_selection():
    if isinstance(el, DB.GroupType):
        group_types.add(el)
    elif isinstance(el, DB.Group):
        group_types.add(el.GroupType)

# find all groups
all_groups = [x for gt in group_types for x in gt.Groups]
logger.debug('all groups: %s', all_groups)

# grab all group types to be deleted
group_type_ids = {x.Id.IntegerValue for x in group_types}
group_type_ids.update(
    [x.GroupType.Id.IntegerValue for x in all_groups
     if x.Parameter[DB.BuiltInParameter.GROUP_ATTACHED_PARENT_NAME]]
)
logger.debug('group types: %s', group_type_ids)
if not group_type_ids:
    forms.alert(
        'At least one group type must be selected.',
        exitscript=True
        )

with revit.Transaction('Explode and Purge Selected Groups'):
    # ungroup groups
    for grp in all_groups:
        logger.debug('Ungrouping %s', grp.Id)
        grp.UngroupMembers()

    for grpt_id in group_type_ids:
        logger.debug('Deleting %s', grpt_id)
        revit.doc.Delete(DB.ElementId(grpt_id))
