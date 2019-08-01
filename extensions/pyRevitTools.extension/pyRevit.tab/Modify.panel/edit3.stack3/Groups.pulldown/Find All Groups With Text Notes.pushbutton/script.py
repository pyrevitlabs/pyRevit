from pyrevit import framework
from pyrevit import revit, DB


__doc__ = 'List all detail groups that include a text element inside them. '\
          'This is helpful for spell checking.'


grps = list(DB.FilteredElementCollector(revit.doc)
              .OfClass(framework.get_type(DB.Group))
              .ToElements())

grpTypes = set()

for g in grps:
    mems = g.GetMemberIds()
    for el in mems:
        mem = revit.doc.GetElement(el)
        if isinstance(mem, DB.TextNote):
            grpTypes.add(g.GroupType.Id)

for gtId in grpTypes:
    print(revit.query.get_name(revit.doc.GetElement(gtId)))
