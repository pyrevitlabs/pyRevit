# these commands get executed in the current scope
# of each new shell (but not for canned commands)
from Autodesk.Revit.DB import *
from Autodesk.Revit.DB.Architecture import *
from Autodesk.Revit.DB.Analysis import *
from Autodesk.Revit.UI import TaskDialog
from Autodesk.Revit.UI import UIApplication

import sys
sys.path.append('E:\Vault\Revit API\Scripts\packages')

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

def alert(msg):
   TaskDialog.Show('RevitPythonShell', msg)

def quit():
   __window__.Close()
exit = quit

def free():
   __window__.Hide()
   __window__.Show()

if len(selection) > 0:
   el = selection[0]