"""Copies selected legend views to all projects currently open in Revit."""

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


def error(msg):
    UI.TaskDialog.Show('pyrevit', msg)
    script.exit()


# find open documents other than the active doc
open_docs = [d for d in revit.docs if not d.IsLinked]
open_docs.remove(revit.doc)
if len(open_docs) < 1:
    error('Only one active document is found. '
          'At least two documents must be open. Operation cancelled.')

# get a list of selected legends
selection = [x for x in revit.get_selection()
             if x.ViewType == DB.ViewType.Legend]

if len(selection) > 0:
    for dest_doc in open_docs:
        print('\n---PROCESSING DOCUMENT {0}---'.format(dest_doc.Title))
        # finding first available legend view
        base_legend_view = None
        for v in DB.FilteredElementCollector(dest_doc).OfClass(DB.View):
            if v.ViewType == DB.ViewType.Legend:
                base_legend_view = v
                break

        if base_legend_view is None:
            error('Document\n{0}\nmust have at least one Legend view.'
                  .format(dest_doc.Title))
        # iterate over interfacetypes legend views
        for source_view in selection:
            print('\nCOPYING {0}'.format(source_view.ViewName))
            # get legend view elements and exclude non-copyable elements
            viewElements = \
                DB.FilteredElementCollector(revit.doc, source_view.Id)\
                  .ToElements()

            element_list = []
            for el in viewElements:
                if isinstance(el, DB.Element) and el.Category:
                    element_list.append(el.Id)
                else:
                    print('SKIPPING ELEMENT WITH ID: {0}'.format(el.Id))
            if len(element_list) < 1:
                print('SKIPPING {0}. NO ELEMENTS FOUND.'
                      .format(source_view.ViewName))
                continue

            # start creating views and copying elements
            with revit.Transaction('Copy Legends to this document',
                                   doc=dest_doc):
                destView = dest_doc.GetElement(
                    base_legend_view.Duplicate(
                        DB.ViewDuplicateOption.Duplicate
                        )
                    )

                options = DB.CopyPasteOptions()
                options.SetDuplicateTypeNamesHandler(CopyUseDestination())
                copied_element = \
                    DB.ElementTransformUtils.CopyElements(
                        source_view,
                        List[DB.ElementId](element_list),
                        destView,
                        None,
                        options)

                # matching element graphics overrides and view properties
                for dest, src in zip(copied_element, element_list):
                    destView.SetElementOverrides(
                        dest,
                        source_view.GetElementOverrides(src)
                        )

                destView.ViewName = source_view.ViewName
                destView.Scale = source_view.Scale
else:
    error('At least one Legend view must be selected.')
