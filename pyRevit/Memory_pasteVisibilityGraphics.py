__doc__ = '''Apply the copied Visibility Graphics settings to the active view.'''

__window__.Hide()
from Autodesk.Revit.DB import ElementId, Transaction
from System.Collections.Generic import List

import os
import os.path as op
import pickle as pl

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

usertemp = os.getenv('Temp')
prjname = op.splitext( op.basename( doc.PathName ) )[0]
datafile = usertemp + '\\' + prjname + '_pySaveVisibilityGraphicsState.pym'

try:
	f = open(datafile, 'r')
	id = pl.load(f)
	f.close()
	with Transaction(doc, 'Paste Visibility Graphics') as t:
		t.Start()
		uidoc.ActiveGraphicalView.ApplyViewTemplateParameters( doc.GetElement( ElementId( id )))
		t.Commit()
	__window__.Close()
except:
	__window__.Show()
	print('CAN NOT FIND ANY VISIBILITY GRAPHICS SETTINGS IN MEMORY:\n{0}'.format(datafile))

