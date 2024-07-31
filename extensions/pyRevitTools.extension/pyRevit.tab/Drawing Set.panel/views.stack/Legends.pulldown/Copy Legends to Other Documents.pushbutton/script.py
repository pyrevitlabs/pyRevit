#pylint: disable=E0401,W0613,C0103,C0111
import sys
from pyrevit.framework import List
from pyrevit import revit, DB
from pyrevit import script
from pyrevit import forms


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

        # get reference plane category, subcategories in destination document
        src_plane_category = \
            DB.Category.GetCategory(
                revit.doc, DB.BuiltInCategory.OST_CLines)
        dest_plane_category = \
            DB.Category.GetCategory(
                dest_doc, DB.BuiltInCategory.OST_CLines)
        dest_subcats = {subcat.Name:subcat 
                        for subcat in dest_plane_category.SubCategories}
        dest_pats = {pat.Name:pat for pat in 
                     DB.FilteredElementCollector(dest_doc)\
                       .OfClass(DB.LinePatternElement)\
                       .ToElements()}

        # iterate over interfacetypes legend views
        for src_legend in legends:
            print('\tCopying: {0}'.format(revit.query.get_name(src_legend)))
            # get legend view elements and exclude non-copyable elements
            view_elements = \
                DB.FilteredElementCollector(revit.doc, src_legend.Id)\
                  .ToElements()

            elements_to_copy = []
            reference_planes = []
            for el in view_elements:
                if isinstance(el, DB.Element) and el.Category:
                    if isinstance(el, DB.ReferencePlane):
                        reference_planes.append(el)
                    else:
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

                # matching reference planes
                for src_plane in reference_planes:
                    src_param = \
                        src_plane.GetParameter(
                            DB.ParameterTypeId.ClineSubcategory)
                    src_subcat = \
                        DB.Category.GetCategory(
                            revit.doc, src_param.AsElementId())
                    dest_plane = \
                        dest_doc.Create.NewReferencePlane(
                            src_plane.BubbleEnd, 
                            src_plane.FreeEnd, 
                            DB.XYZ(0,0,1), 
                            dest_view)
                    if src_subcat.Id != src_plane_category.Id:
                        if src_subcat.Name not in dest_subcats:
                            p_line_style = DB.GraphicsStyleType.Projection
                            dest_subcats[src_subcat.Name] = \
                                dest_doc.Settings.Categories.NewSubcategory(
                                    dest_plane_category, src_subcat.Name)
                            dest_subcats[src_subcat.Name].SetLineWeight(
                                src_subcat.GetLineWeight(p_line_style), 
                                p_line_style)
                            dest_subcats[src_subcat.Name].LineColor = \
                                src_subcat.LineColor
                            src_pat = revit.doc.GetElement(
                                src_subcat.GetLinePatternId(p_line_style))
                            if src_pat is not None:
                                if src_pat.Name not in dest_pats:
                                    dest_pats[src_pat.Name] = \
                                        DB.LinePatternElement\
                                            .Create(dest_doc, 
                                                    src_pat.GetLinePattern())
                                dest_subcats[src_subcat.Name]\
                                    .SetLinePatternId(
                                        dest_pats[src_pat.Name].Id, 
                                        p_line_style)
                        dest_plane.GetParameter(
                            DB.ParameterTypeId.ClineSubcategory).Set(
                                dest_subcats[src_subcat.Name].Id)
