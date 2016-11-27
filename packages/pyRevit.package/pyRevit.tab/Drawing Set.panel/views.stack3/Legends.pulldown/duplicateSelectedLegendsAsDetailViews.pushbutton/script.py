"""
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
"""

__doc__ = 'Converts selected legend views to detail views.'

import sys
from Autodesk.Revit.DB import *
from System.Collections.Generic import List
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


def error(msg):
    TaskDialog.Show('pyrevit', msg)
    sys.exit(0)


# get a list of selected legends
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() if
             doc.GetElement(elId).ViewType == ViewType.Legend]

if len(selection) > 0:
    # get the first style for Drafting views. This will act as the default style
    cl = FilteredElementCollector(doc).OfClass(ViewFamilyType)
    for type in cl:
        if type.ViewFamily == ViewFamily.Drafting:
            draftingViewType = type
            break
    # iterate over scriptexec legend views
    for srcView in selection:
        print('\nCOPYING {0}'.format(srcView.ViewName))
        # get legend view elements and exclude non-copyable elements
        viewElements = FilteredElementCollector(doc, srcView.Id).ToElements()
        elementList = []
        for el in viewElements:
            if isinstance(el, Element) and el.Category and el.Category.Name != 'Legend Components':
                elementList.append(el.Id)
            else:
                print('SKIPPING ELEMENT WITH ID: {0}'.format(el.Id))
        if len(elementList) < 1:
            print('SKIPPING {0}. NO ELEMENTS FOUND.'.format(srcView.ViewName))
            continue
        # start creating views and copying elements
        with Transaction(doc, 'Duplicate Legend as Drafting') as t:
            t.Start()
            destView = ViewDrafting.Create(doc, draftingViewType.Id)
            options = CopyPasteOptions()
            options.SetDuplicateTypeNamesHandler(CopyUseDestination())
            copiedElement = ElementTransformUtils.CopyElements(srcView,
                                                               List[ElementId](elementList),
                                                               destView,
                                                               None,
                                                               options)
            # matching element graphics overrides and view properties
            for dest, src in zip(copiedElement, elementList):
                destView.SetElementOverrides(dest, srcView.GetElementOverrides(src))
            destView.ViewName = srcView.ViewName
            destView.Scale = srcView.Scale
            t.Commit()
else:
    error('At least one Legend view must be selected.')
