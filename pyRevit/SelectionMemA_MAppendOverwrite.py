__doc__ = 'Clear memory and Append current selection. Works like the M+ button in a calculator. This is a project-dependent (Revit *.rvt) memory. Every project has its own memory saved in user temp folder as *.sel files.'


__window__.Close()
# from Autodesk.Revit.DB import ElementId
import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveRevitSelection.sel'

selection = { elId.ToString() for elId in uidoc.Selection.GetElementIds() }

f = open(datafile, 'w')
pl.dump( selection, f)
f.close()
