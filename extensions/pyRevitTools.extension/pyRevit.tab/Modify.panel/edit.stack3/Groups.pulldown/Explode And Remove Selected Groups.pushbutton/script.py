from pyrevit import revit, DB, UI
from pyrevit import forms


__context__ = 'selection'
__doc__ = 'Explodes all instances of the selected groups and removes '\
          'the group definition from project browser.'


selection = revit.get_selection()

with revit.Transaction('Explode and Purge Selected Groups'):
    grpTypes = set()
    grps = []
    attachedGrps = []

    for el in selection:
        if isinstance(el, DB.GroupType):
            grpTypes.add(el)
        elif isinstance(el, DB.Group):
            grpTypes.add(el.GroupType)

    if len(grpTypes) == 0:
        forms.alert('At least one group type must be selected.')

    for gt in grpTypes:
        for grp in gt.Groups:
            grps.append(grp)

    for g in grps:
        if g.LookupParameter('Attached to'):
            attachedGrps.append(g.GroupType)
        g.UngroupMembers()

    for agt in attachedGrps:
        revit.doc.Delete(agt.Id)

    for gt in grpTypes:
        revit.doc.Delete(gt.Id)
