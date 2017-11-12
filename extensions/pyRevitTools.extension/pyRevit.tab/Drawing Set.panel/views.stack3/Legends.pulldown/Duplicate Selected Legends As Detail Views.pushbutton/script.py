"""Converts selected legend views to detail views."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


def error(msg):
    UI.TaskDialog.Show('pyrevit', msg)
    script.exit()


# get a list of selected legends
selection = [x for x in revit.get_selection()
             if x.ViewType == DB.ViewType.Legend]

if len(selection) > 0:
    # get the first style for Drafting views.
    # This will act as the default style
    for type in DB.FilteredElementCollector(revit.doc)\
                  .OfClass(DB.ViewFamilyType):
        if type.ViewFamily == DB.ViewFamily.Drafting:
            draftingViewType = type
            break

    # iterate over interfacetypes legend views
    for srcView in selection:
        print('\nCOPYING {0}'.format(srcView.ViewName))
        # get legend view elements and exclude non-copyable elements
        viewElements = DB.FilteredElementCollector(revit.doc, srcView.Id)\
                         .ToElements()

        element_list = []
        for el in viewElements:
            if isinstance(el, DB.Element) \
                    and el.Category \
                    and el.Category.Name != 'Legend Components':
                element_list.append(el.Id)
            else:
                print('SKIPPING ELEMENT WITH ID: {0}'.format(el.Id))
        if len(element_list) < 1:
            print('SKIPPING {0}. NO ELEMENTS FOUND.'.format(srcView.ViewName))
            continue

        # start creating views and copying elements
        with revit.Transaction('Duplicate Legend as Drafting'):
            destView = DB.ViewDrafting.Create(revit.doc, draftingViewType.Id)
            options = DB.CopyPasteOptions()
            options.SetDuplicateTypeNamesHandler(CopyUseDestination())
            copiedElement = \
                DB.ElementTransformUtils.CopyElements(
                    srcView,
                    List[DB.ElementId](element_list),
                    destView,
                    None,
                    options)

            # matching element graphics overrides and view properties
            for dest, src in zip(copiedElement, element_list):
                destView.SetElementOverrides(dest,
                                             srcView.GetElementOverrides(src))

            destView.ViewName = srcView.ViewName
            destView.Scale = srcView.Scale
else:
    error('At least one Legend view must be selected.')
