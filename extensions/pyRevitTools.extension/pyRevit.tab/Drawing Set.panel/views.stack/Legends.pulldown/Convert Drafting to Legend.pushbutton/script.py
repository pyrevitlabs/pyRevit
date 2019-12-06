"""Converts selected detail views to legend views."""
#pylint: disable=E0401,W0613,C0103
from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


logger = script.get_logger()


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DB.DuplicateTypeAction.UseDestinationTypes


# get all views and collect names
all_graphviews = revit.query.get_all_views(doc=revit.doc)
all_legend_names = [revit.query.get_name(x)
                    for x in all_graphviews
                    if x.ViewType == DB.ViewType.Legend]

# get a list of selected legends
drafting_views = forms.select_views(
    title='Select Legends',
    filterfunc=lambda x: x.ViewType == DB.ViewType.DraftingView)


if drafting_views:
    # finding first available legend view
    base_legend = revit.query.find_first_legend()

    if not base_legend:
        forms.alert('At least one Legend view must exist in the model.',
                    exitscript=True)

    # iterate over interfacetypes drafting views
    for src_drafting in drafting_views:
        logger.debug('Copying %s', revit.query.get_name(src_drafting))

        # get drafting view elements and exclude non-copyable elements
        view_elements = \
            DB.FilteredElementCollector(revit.doc, src_drafting.Id).ToElements()

        elements_to_copy = []
        for el in view_elements:
            if isinstance(el, DB.Element) and el.Category:
                elements_to_copy.append(el.Id)
            else:
                logger.debug('Skipping element: %s', el.Id)
        if not elements_to_copy:
            logger.debug('Skipping empty view: %s',
                         revit.query.get_name(src_drafting))
            continue

        # start creating views and copying elements
        with revit.Transaction('Duplicate Drafting as Legend'):
            # copying and pasting elements
            dest_view = revit.doc.GetElement(
                base_legend.Duplicate(DB.ViewDuplicateOption.Duplicate)
                )

            options = DB.CopyPasteOptions()
            options.SetDuplicateTypeNamesHandler(CopyUseDestination())
            copied_elements = \
                DB.ElementTransformUtils.CopyElements(
                    src_drafting,
                    List[DB.ElementId](elements_to_copy),
                    dest_view,
                    None,
                    options)

            # matching element graphics overrides and view properties
            for dest, src in zip(copied_elements, elements_to_copy):
                dest_view.SetElementOverrides(
                    dest,
                    src_drafting.GetElementOverrides(src)
                    )
            # matching view name and scale
            new_name = revit.query.get_name(src_drafting)
            if new_name in all_legend_names:
                new_name += ' (Converted from Drafting)'
                logger.warning('Legend already exists. Renaming to: "%s"',
                               new_name)
            revit.update.set_name(dest_view, new_name)
            dest_view.Scale = src_drafting.Scale
