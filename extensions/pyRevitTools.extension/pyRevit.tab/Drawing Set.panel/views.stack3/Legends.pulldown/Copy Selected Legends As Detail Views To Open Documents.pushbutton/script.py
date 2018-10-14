from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import forms


__helpurl__ = '{{docpath}}ThzcRM_Tj8g'
__doc__ = 'Converts selected legend views to detail views and copies '\
          'them to all projects currently open in Revit.'


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


def error(msg):
    forms.alert(msg)
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
        # get the first style for Drafting views.
        # This will act as the default style
        for type in DB.FilteredElementCollector(dest_doc)\
                      .OfClass(DB.ViewFamilyType):
            if type.ViewFamily == DB.ViewFamily.Drafting:
                draftingViewType = type
                break

        # iterate over interfacetypes legend views
        for source_view in selection:
            print('\nCOPYING {0}'.format(source_view.ViewName))
            # get legend view elements and exclude non-copyable elements
            element_list = []
            for el in DB.FilteredElementCollector(revit.doc, source_view.Id)\
                        .ToElements():
                if isinstance(el, DB.Element) \
                        and el.Category \
                        and el.Category.Name != 'Legend Components':
                    element_list.append(el.Id)
                else:
                    print('SKIPPING ELEMENT WITH ID: {0}'.format(el.Id))
            if len(element_list) < 1:
                print('SKIPPING {0}. NO ELEMENTS FOUND.'
                      .format(source_view.ViewName))
                continue

            # start creating views and copying elements
            with revit.Transaction('Duplicate Legend as Drafting',
                                   doc=dest_doc):
                destView = DB.ViewDrafting.Create(dest_doc,
                                                  draftingViewType.Id)
                options = DB.CopyPasteOptions()
                options.SetDuplicateTypeNamesHandler(CopyUseDestination())
                copiedElement = \
                    DB.ElementTransformUtils.CopyElements(
                        source_view,
                        List[DB.ElementId](element_list),
                        destView,
                        None,
                        options)

                # matching element graphics overrides and view properties
                for dest, src in zip(copiedElement, element_list):
                    destView.SetElementOverrides(
                        dest,
                        source_view.GetElementOverrides(src)
                        )

                destView.ViewName = source_view.ViewName
                destView.Scale = source_view.Scale
else:
    error('At least one Legend view must be selected.')
