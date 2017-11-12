"""Converts selected detail views to legend views."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script


logger = script.get_logger()


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


# get a list of selected drafting views
selection = [el for el in revit.get_selection()
             if isinstance(el, DB.View)
             and el.ViewType == DB.ViewType.DraftingView]


if not len(selection) > 0:
    UI.TaskDialog.Show('pyRevit',
                       'At least one Drafting view must be selected.')
    script.exit()


# finding first available legend view
baseLegendView = None
for v in DB.FilteredElementCollector(revit.doc).OfClass(DB.View):
    if v.ViewType == DB.ViewType.Legend:
        baseLegendView = v
        break

if not baseLegendView:
    UI.TaskDialog.Show('pyRevit',
                       'At least one Legend view must exist in the model.')
    script.exit()

# iterate over interfacetypes drafting views
for src_view in selection:
    print('\nCOPYING {0}'.format(src_view.ViewName))

    # get drafting view elements and exclude non-copyable elements
    view_elements = \
        DB.FilteredElementCollector(revit.doc, src_view.Id).ToElements()

    elements_to_copy = []
    for el in view_elements:
        if isinstance(el, DB.Element) and el.Category:
            elements_to_copy.append(el.Id)
        else:
            logger.debug('Skipping Element with id: {0}'.format(el.Id))
    if len(elements_to_copy) < 1:
        logger.debug('Skipping {0}. No copyable elements where found.'
                     .format(src_view.ViewName))
        continue

    # start creating views and copying elements
    with revit.Transaction('Duplicate Drafting as Legend'):
        # copying and pasting elements
        dest_view = revit.doc.GetElement(
            baseLegendView.Duplicate(DB.ViewDuplicateOption.Duplicate)
            )

        options = DB.CopyPasteOptions()
        options.SetDuplicateTypeNamesHandler(CopyUseDestination())
        copied_element = \
            DB.ElementTransformUtils.CopyElements(
                src_view,
                List[DB.ElementId](elements_to_copy),
                dest_view,
                None,
                options)

        # matching element graphics overrides and view properties
        for dest, src in zip(copied_element, elements_to_copy):
            dest_view.SetElementOverrides(dest,
                                          src_view.GetElementOverrides(src))
        dest_view.ViewName = src_view.ViewName
        dest_view.Scale = src_view.Scale
