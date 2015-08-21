from Autodesk.Revit.DB import ElementId
#from System.Collections.Generic import List
from Autodesk.Revit.UI import PostableCommand as pc
from Autodesk.Revit.UI import RevitCommandId as rcid
import os

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

def addToClipBoard(text):
	command = 'echo ' + text.strip() + '| clip'
	os.system(command)


__window__.Close()

#selection = [el.Id for el in uidoc.Selection.Elements ]
#selectedIds = List[ElementId](selection)
#print (uidoc.ShowElements(el))

selectedIds = ''

for el in uidoc.Selection.Elements:
	selectedIds = selectedIds + str(el.Id) + ','

cid_SelectById = rcid.LookupPostableCommandId(pc.SelectById)
addToClipBoard(selectedIds)
__revit__.PostCommand(cid_SelectById)