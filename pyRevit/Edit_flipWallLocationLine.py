__window__.Close()
from Autodesk.Revit.DB import TransactionGroup, Transaction, Wall

doc = __revit__.ActiveUIDocument.Document
selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

tg = TransactionGroup( doc, "Search for linked elements")
tg.Start()

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
		with Transaction( doc, 'Change Wall Location Line') as t:
			t.Start()
			param.Set( locLineValues[ 'Core Centerline' ] )
			t.Commit()
		with Transaction( doc, 'Flip Selected Wall') as t:
			t.Start()
			el.Flip()
			param.Set( locLineValues[ 'Core Face: Interior' ] )
			t.Commit()
tg.Commit()

