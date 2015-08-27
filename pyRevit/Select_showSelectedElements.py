__window__.Close()
from Autodesk.Revit.DB import ElementId
from Autodesk.Revit.UI import PostableCommand as pc
from Autodesk.Revit.UI import RevitCommandId as rcid
import os

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

def addToClipBoard( text ):
	command = 'echo ' + text.strip() + '| clip'
	os.system( command )

selectedIds = ''

for elId in uidoc.Selection.GetElementIds():
	selectedIds = selectedIds + str( elId ) + ','

cid_SelectById = rcid.LookupPostableCommandId( pc.SelectById )
addToClipBoard( selectedIds )
__revit__.PostCommand( cid_SelectById )