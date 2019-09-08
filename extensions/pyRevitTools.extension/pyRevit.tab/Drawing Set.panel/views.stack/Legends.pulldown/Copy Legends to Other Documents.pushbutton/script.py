#pylint: disable=E0401,W0613,C0103,C0111
import sys
from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


__helpurl__ = '{{docpath}}ThzcRM_Tj8g'


logger = script.get_logger()


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


# find open documents other than the active doc
open_docs = forms.select_open_docs(title='Select Destination Documents')
if not open_docs:
    sys.exit(0)

# get a list of selected legends
legends = forms.select_views(
    title='Select Drafting Views',
    filterfunc=lambda x: x.ViewType == DB.ViewType.Legend,
    use_selection=True)

if legends:
    for dest_doc in open_docs:
        # get all views and collect names
        all_graphviews = revit.query.get_all_views(doc=dest_doc)
        all_legend_names = [revit.query.get_name(x)
                            for x in all_graphviews
                            if x.ViewType == DB.ViewType.Legend]

        print('Processing Document: {0}'.format(dest_doc.Title))
        # finding first available legend view
        base_legend = revit.query.find_first_legend(doc=dest_doc)
        if not base_legend:
            forms.alert('At least one Legend must exist in target document.',
                        exitscript=True)

        # iterate over interfacetypes legend views
        for src_legend in legends:
            print('\tCopying: {0}'.format(revit.query.get_name(src_legend)))
            # get legend view elements and exclude non-copyable elements
            view_elements = \
                DB.FilteredElementCollector(revit.doc, src_legend.Id)\
                  .ToElements()

            elements_to_copy = []
            for el in view_elements:
                if isinstance(el, DB.Element) and el.Category:
                    elements_to_copy.append(el.Id)
                else:
                    logger.debug('Skipping element: %s', el.Id)
            if not elements_to_copy:
                logger.debug('Skipping empty view: %s',
                             revit.query.get_name(src_legend))
                continue

            # start creating views and copying elements
            with revit.Transaction('Copy Legends to this document',
                                   doc=dest_doc):
                dest_view = dest_doc.GetElement(
                    base_legend.Duplicate(
                        DB.ViewDuplicateOption.Duplicate
                        )
                    )

                options = DB.CopyPasteOptions()
                options.SetDuplicateTypeNamesHandler(CopyUseDestination())
                copied_elements = \
                    DB.ElementTransformUtils.CopyElements(
                        src_legend,
                        List[DB.ElementId](elements_to_copy),
                        dest_view,
                        None,
                        options)

                # matching element graphics overrides and view properties
                for dest, src in zip(copied_elements, elements_to_copy):
                    dest_view.SetElementOverrides(
                        dest,
                        src_legend.GetElementOverrides(src)
                        )

                # matching view name and scale
                src_name = revit.query.get_name(src_legend)
                count = 0
                new_name = src_name
                while new_name in all_legend_names:
                    count += 1
                    new_name = src_name + ' (Duplicate %s)' % count
                    logger.warning(
                        'Legend already exists. Renaming to: "%s"', new_name)
                revit.update.set_name(dest_view, new_name)
                dest_view.Scale = src_legend.Scale
