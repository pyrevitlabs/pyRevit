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

__doc__ = 'Converts selected detail views to legend views.'

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


# get a list of selected drafting views
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() if
             doc.GetElement(elId).ViewType == ViewType.DraftingView]

if len(selection) > 0:
    # finding first available legend view
    allViews = FilteredElementCollector(doc).OfClass(View)
    for v in allViews:
        if v.ViewType == ViewType.Legend:
            baseLegendView = v
            break
    # iterate over interfacetypes drafting views
    for srcView in selection:
        print('\nCOPYING {0}'.format(srcView.ViewName))
        # get drafting view elements and exclude non-copyable elements
        viewElements = FilteredElementCollector(doc, srcView.Id).ToElements()
        elementList = []
        for el in viewElements:
            if isinstance(el, Element) and el.Category:
                elementList.append(el.Id)
            else:
                print('SKIPPING ELEMENT WITH ID: {0}'.format(el.Id))
        if len(elementList) < 1:
            print('SKIPPING {0}. NO ELEMENTS FOUND.'.format(srcView.ViewName))
            continue
        # start creating views and copying elements
        with Transaction(doc, 'Duplicate Drafting as Legend') as t:
            t.Start()
            destView = doc.GetElement(baseLegendView.Duplicate(ViewDuplicateOption.Duplicate))
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
    error('At least one Drafting view must be selected.')
