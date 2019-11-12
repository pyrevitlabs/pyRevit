"""
Get a total count and types of In Place Family in the current document.
Copyright (c) 2019 Jean-Marc Couffin
https://github.com/jmcouffin
--------------------------------------------------------
PyRevit Notice:
Copyright (c) 2014-2019 Ehsan Iran-Nejad
pyRevit: repository at https://github.com/eirannejad/pyRevit
"""

__title__ = 'Get In Place Family count'
__author__ = 'Jean-Marc Couffin'
__contact__ = 'https://github.com/jmcouffin'
__credits__ = 'http://eirannejad.github.io/pyRevit/credits/'
__doc__ = 'Get a total count and types of In Place Family in the current document.'


from pyrevit.framework import List
from pyrevit import revit, DB

famInstE = DB.FilteredElementCollector(revit.doc)\
             .OfClass(DB.FamilyInstance)\
             .WhereElementIsNotElementType()\
             .ToElements()
             
famInstInPlace = [e for e in famInstE if e.Symbol.Family.IsInPlace]

print('In Place Families count : {0}'.format(len(list(famInstInPlace))))

elist = []

print('\nCATEGORY & FAMILY NAME')

for e in famInstInPlace:
    ptcategory = revit.doc.GetElement(revit.doc.GetElement(e.Id).GetTypeId()).Category.Name
    ename = e.Symbol.Family.Name
    l = ptcategory +' | '+ ename
    elist.append(l)
    
a = sorted(elist)
print((str('\n'.join(a))))

