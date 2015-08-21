__window__.Close()
from Autodesk.Revit.DB import Transaction, Wall

doc = __revit__.ActiveUIDocument.Document
selection = list(__revit__.ActiveUIDocument.Selection.Elements)

t = Transaction( doc, 'Flip Selected Wall Location Line')
t.Start()

locLineValues = {	'Wall Centerline':0,
					'Core Centerline':1,
					'Finish Face: Exterior':2,
					'Finish Face: Interior':3,
					'Core Face: Exterior':4,
					'Core Face: Interior':5,
					}

for el in selection:
	if isinstance( el, Wall ):
		param = el.LookupParameter('Location Line')
		param.Set( locLineValues[ 'Core Centerline' ])
		el.Flip()
		param.Set( locLineValues[ 'Core Face: Interior' ])

t.Commit()