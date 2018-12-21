"""List all groups that includethe selected group element as a nested group."""

from pyrevit import framework
from pyrevit import revit, DB


__context__ = 'selection'


selection = revit.get_selection()


grps = list(DB.FilteredElementCollector(revit.doc)
              .OfClass(framework.get_type(DB.Group))
              .ToElements())

grpTypes = set()


if len(selection) > 0:
    for el in selection:
        if isinstance(el, DB.Group):
            selectedgtid = el.GroupType.Id
            for g in grps:
                mems = g.GetMemberIds()
                for memid in mems:
                    mem = revit.doc.GetElement(memid)
                    if isinstance(mem, DB.Group):
                        memgtid = mem.GroupType.Id
                        if memgtid == selectedgtid:
                            grpTypes.add(g.GroupType.Id)

            for gtId in grpTypes:
                print(revit.query.get_name(revit.doc.GetElement(gtId)))
