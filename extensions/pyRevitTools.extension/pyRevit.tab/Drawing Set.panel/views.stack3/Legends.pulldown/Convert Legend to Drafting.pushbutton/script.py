"""Converts selected legend views to detail views."""
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
all_drafting_names = [revit.query.get_name(x)
                      for x in all_graphviews
                      if x.ViewType == DB.ViewType.DraftingView]


# get a list of selected legends
legends = forms.select_views(
    title='Select Legends',
    filterfunc=lambda x: x.ViewType == DB.ViewType.Legend,
    use_selection=True)

print(legends)

if legends:
    # get the first style for Drafting views.
    # This will act as the default style
    for view_type in DB.FilteredElementCollector(revit.doc)\
                       .OfClass(DB.ViewFamilyType):
        if view_type.ViewFamily == DB.ViewFamily.Drafting:
            drafting_view_type = view_type
            break

    # iterate over interfacetypes legend views
    for src_legend in legends:
        logger.debug('Copying %s', revit.query.get_name(src_legend))
        # get legend view elements and exclude non-copyable elements
        view_elements = DB.FilteredElementCollector(revit.doc, src_legend.Id)\
                          .ToElements()

        elements_to_copy = []
        for el in view_elements:
            if isinstance(el, DB.Element) \
                    and el.Category \
                    and el.Category.Name != 'Legend Components':
                elements_to_copy.append(el.Id)
            else:
                logger.debug('Skipping element: %s', el.Id)
        if not elements_to_copy:
            logger.debug('Skipping empty view: %s',
                         revit.query.get_name(src_legend))
            continue

        # start creating views and copying elements
        with revit.Transaction('Duplicate Legend as Drafting'):
            dest_view = DB.ViewDrafting.Create(revit.doc, drafting_view_type.Id)
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
            new_name = revit.query.get_name(src_legend)
            if new_name in all_drafting_names:
                new_name += ' (Converted from Legend)'
                logger.warning('Drafting already exists. Renaming to: "%s"',
                               new_name)
            revit.update.set_name(dest_view, new_name)
            dest_view.Scale = src_legend.Scale
