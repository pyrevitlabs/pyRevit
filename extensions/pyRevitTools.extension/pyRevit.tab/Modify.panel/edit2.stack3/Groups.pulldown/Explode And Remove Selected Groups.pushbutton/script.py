from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script

__context__ = 'selection'
__doc__ = 'Explodes all instances of the selected groups and removes '\
          'the group definition from project browser.'


selection = revit.get_selection()

logger = script.get_logger()

with revit.Transaction('Explode and Purge Selected Groups'):
    grpTypes = set()
    grps = []
    attachedGrpIds = set()

    for el in selection:
        if isinstance(el, DB.GroupType):
            grpTypes.add(el)
        elif isinstance(el, DB.Group):
            grpTypes.add(el.GroupType)

    if len(grpTypes) == 0:
        forms.alert('At least one group type must be selected.')

    grpTypeIds = [x.Id for x in grpTypes]
    for gt in grpTypes:
        for grp in gt.Groups:
            grps.append(grp)

    for g in grps:
        if g.Parameter[DB.BuiltInParameter.GROUP_ATTACHED_PARENT_NAME]:
            attachedGrpIds.add(g.GroupType.Id)
        g.UngroupMembers()

    for agt_id in attachedGrpIds:
        agt = revit.doc.GetElement(agt_id)
        if agt:
            revit.doc.Delete(agt.Id)
        else:
            logger.warning("Unable to find and delete Attached GroupType id=%d" % agt_id.IntegerValue)

    for gt_id in grpTypeIds:
        gt = revit.doc.GetElement(gt_id)
        if gt:
            revit.doc.Delete(gt.Id)
        else:
            logger.warning("Unable to find and delete source GroupType id=%d" % gt_id.IntegerValue)
