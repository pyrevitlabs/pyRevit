"""Converts selected detail views to legend views."""

import sys

from scriptutils import logger
from revitutils import doc, selection

from System.Collections.Generic import List

from Autodesk.Revit.DB import Element, ElementId, View, ViewType, FilteredElementCollector, Transaction, \
                              CopyPasteOptions, ElementTransformUtils, IDuplicateTypeNamesHandler, ViewDuplicateOption
from Autodesk.Revit.UI import TaskDialog



class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


# get a list of selected drafting views
selection = [el for el in selection.elements if isinstance(el, View) and el.ViewType == ViewType.DraftingView]

if not len(selection) > 0:
    TaskDialog.Show('pyRevit', 'At least one Drafting view must be selected.')
    sys.exit(0)

# finding first available legend view
baseLegendView = None
allViews = FilteredElementCollector(doc).OfClass(View)
for v in allViews:
    if v.ViewType == ViewType.Legend:
        baseLegendView = v
        break

if not baseLegendView:
    TaskDialog.Show('pyRevit', 'At least one Legend view must exist in the model.')
    sys.exit(0)

# iterate over interfacetypes drafting views
for src_view in selection:
    print('\nCOPYING {0}'.format(src_view.ViewName))

    # get drafting view elements and exclude non-copyable elements
    view_elements = FilteredElementCollector(doc, src_view.Id).ToElements()
    elements_to_copy = []
    for el in view_elements:
        if isinstance(el, Element) and el.Category:
            elements_to_copy.append(el.Id)
        else:
            logger.debug('Skipping Element with id: {0}'.format(el.Id))
    if len(elements_to_copy) < 1:
        logger.debug('Skipping {0}. No copyable elements where found.'.format(src_view.ViewName))
        continue

    # start creating views and copying elements
    with Transaction(doc, 'Duplicate Drafting as Legend') as t:
        t.Start()

        # copying and pasting elements
        dest_view = doc.GetElement(baseLegendView.Duplicate(ViewDuplicateOption.Duplicate))
        options = CopyPasteOptions()
        options.SetDuplicateTypeNamesHandler(CopyUseDestination())
        copied_element = ElementTransformUtils.CopyElements(src_view,
                                                            List[ElementId](elements_to_copy),
                                                            dest_view,
                                                            None,
                                                            options)

        # matching element graphics overrides and view properties
        for dest, src in zip(copied_element, elements_to_copy):
            dest_view.SetElementOverrides(dest, src_view.GetElementOverrides(src))
        dest_view.ViewName = src_view.ViewName
        dest_view.Scale = src_view.Scale

        t.Commit()
