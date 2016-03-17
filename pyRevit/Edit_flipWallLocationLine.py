'''
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
'''

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
			param.Set( locLineValues[ 'Core Face: Exterior' ] )
			t.Commit()
tg.Commit()

