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

__doc__ = 'Copies selected legend views to all projects currently open in Revit.'

import sys
from Autodesk.Revit.DB import *
from System.Collections.Generic import List
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
activeDoc = __revit__.ActiveUIDocument.Document


class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


def error(msg):
    TaskDialog.Show('pyrevit', msg)
    sys.exit(0)


# find open documents other than the active doc
openDocs = [d for d in __revit__.Application.Documents if not d.IsLinked]
openDocs.remove(activeDoc)
if len(openDocs) < 1:
    error('Only one active document is found. At least two documents must be open. Operation cancelled.')

# get a list of selected legends
selection = [activeDoc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() if
             activeDoc.GetElement(elId).ViewType == ViewType.Legend]

if len(selection) > 0:
    for doc in openDocs:
        print('\n---PROCESSING DOCUMENT {0}---'.format(doc.Title))
        # finding first available legend view
        allViews = FilteredElementCollector(doc).OfClass(View)
        baseLegendView = None
        for v in allViews:
            if v.ViewType == ViewType.Legend:
                baseLegendView = v
                break
        if None == baseLegendView:
            error('Document\n{0}\nmust have at least one Legend view.'.format(doc.Title))
        # iterate over cstemplates legend views
        for srcView in selection:
            print('\nCOPYING {0}'.format(srcView.ViewName))
            # get legend view elements and exclude non-copyable elements
            viewElements = FilteredElementCollector(activeDoc, srcView.Id).ToElements()
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
            with Transaction(doc, 'Copy Legends to this document') as t:
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
    error('At least one Legend view must be selected.')
