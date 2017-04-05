"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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
"""

__doc__ = 'Lists all the elements that are tied to the selected element. For example elements tags or dimensions.'

from Autodesk.Revit.DB import Transaction, TransactionGroup

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = __revit__.ActiveUIDocument.Selection.GetElementIds()

if not selection.is_empty:
    t = Transaction(doc, "Search for linked elements")
    t.Start()

    print("Searching for all objects tied to ELEMENT ID: {0}...".format(selection.first.Id))
    linked_elements_list = doc.Delete(selection.first.Id)

    t.RollBack()


    for elId in linked_elements_list:
        el = doc.GetElement(elId)
        if el and elId in selection.element_ids:
            elid_link = this_script.output.linkify(elId)
            print("ID: {0}\t\tTYPE: {1} ( selected object )".format(elid_link, el.GetType().Name))
        elif el:
            elid_link = this_script.output.linkify(elId)
            print("ID: {0}\t\tTYPE: {1}".format(elid_link, el.GetType().Name))
