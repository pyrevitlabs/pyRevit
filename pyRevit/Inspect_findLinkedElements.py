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

from Autodesk.Revit.DB import Transaction, TransactionGroup

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = __revit__.ActiveUIDocument.Selection.GetElementIds()

tg = TransactionGroup( doc, "Search for linked elements")
tg.Start()
t = Transaction( doc, "Search for linked elements")
t.Start()

list = []

for elId in selection:
	print("Searching for all objects tied to ELEMENT ID: {0}...".format( elId ))
	list = doc.Delete( elId )

t.Commit()
tg.RollBack()

for elId in list:
	el = doc.GetElement( elId )
	if el and elId in selection:
		print("ID: {0}\t\tTYPE: {1} ( selected object )".format( elId, el.GetType().Name ) )
	elif el:
		print("ID: {0}\t\tTYPE: {1}".format( elId, el.GetType().Name ) )
