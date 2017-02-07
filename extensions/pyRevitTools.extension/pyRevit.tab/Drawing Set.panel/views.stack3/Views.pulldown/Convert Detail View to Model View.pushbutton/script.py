import sys
import clr

from scriptutils import logger, this_script, print_md
from scriptutils.userinput import CommandSwitchWindow
from revitutils import doc, selection

from System.Collections.Generic import List
from Autodesk.Revit.DB import Element, ElementId, View, ViewType, FilteredElementCollector, BuiltInCategory, \
                              CopyPasteOptions, ElementTransformUtils, ElevationMarker, \
                              Transaction, TransactionGroup, IDuplicateTypeNamesHandler, ViewDuplicateOption, \
                              ViewPlan, ViewDrafting, ViewSection, BoundingBoxXYZ, ElementTypeGroup, XYZ, \
                              IFailuresPreprocessor, FailureProcessingResult
from Autodesk.Revit.UI import TaskDialog


__doc__ = "Converts selected detail views to selected model view type." \
          "The resulting model views will not show the model, and their associated tags are only visible in 1:1 views."


selected_level = None

view_types_dict = {'Floor Plan': ViewPlan,
                   'Section': ViewSection,
                   'Reflected Ceiling Plan': ViewPlan,
                   'Elevation': ViewSection,
                   # 'Area Plan': ViewPlan,
                   # 'Structural Plan': ViewPlan,
                   }


class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        logger.debug('Duplicate types found. Using destination types.')
        return DuplicateTypeAction.UseDestinationTypes


class ViewConverterFailurePreProcessor(IFailuresPreprocessor):
    def __init__(self, trans_name, view_name):
        self.transaction_name = trans_name
        self.src_viewname = view_name

    def PreprocessFailures(self, failures_accessor):
        trans_name = failures_accessor.GetTransactionName()
        fmas = list(failures_accessor.GetFailureMessages())

        if len(fmas) == 0:
            return FailureProcessingResult.Continue

        # We already know the transaction name.
        if trans_name == self.transaction_name:
            # DeleteWarning mimics clicking 'Ok' button
            for fma in fmas:
                logger.warning('Revit failure occured | {}'.format(fma.GetDescriptionText()))
                failures_accessor.DeleteWarning(fma)

            return FailureProcessingResult.ProceedWithCommit

        return FailureProcessingResult.Continue


def process_selection():
    if not selection.is_empty:
        return [el for el in selection.elements if isinstance(el, ViewDrafting)]
    else:
        TaskDialog.Show('pyRevit', 'At least one Drafting view must be selected.')
        sys.exit(0)


def get_modelview_type():
    switch = CommandSwitchWindow(view_types_dict.keys()).pick_cmd_switch()
    if switch:
        return switch
    else:
        logger.debug('User cancelled.')
        sys.exit(0)


def get_view_level():
    global selected_level
    if not selected_level:
        levels = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Levels) \
                                              .WhereElementIsNotElementType()         \
                                              .ToElements()
        levels_dict = {lvl.Name:lvl for lvl in levels}
        picked_level = CommandSwitchWindow(levels_dict.keys()).pick_cmd_switch()
        selected_level = levels_dict[picked_level]

    return selected_level


def find_first_floorplan():
    view_list = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(ViewPlan)) \
                                                 .WhereElementIsNotElementType()      \
                                                 .ToElements())
    for view in view_list:
        if view.ViewType == ViewType.FloorPlan:
            return view


def create_dest_view(view_type, view_name, view_scale):
    with Transaction(doc, 'Create model view') as t:
        t.Start()
        try:
            dest_view = None
            if view_type == 'Floor Plan':
                level = get_view_level()
                view_fam_typeid = doc.GetDefaultElementTypeId(ElementTypeGroup.ViewTypeFloorPlan)
                dest_view = ViewPlan.Create(doc, view_fam_typeid, level.Id)
            elif view_type == 'Reflected Ceiling Plan':
                level = get_view_level()
                view_fam_typeid = doc.GetDefaultElementTypeId(ElementTypeGroup.ViewTypeCeilingPlan)
                dest_view = ViewPlan.Create(doc, view_fam_typeid, level.Id)
            elif view_type == 'Section':
                view_fam_typeid = doc.GetDefaultElementTypeId(ElementTypeGroup.ViewTypeSection)
                dest_view = ViewSection.CreateSection(doc, view_fam_typeid, BoundingBoxXYZ())
                scale_param = dest_view.LookupParameter('Hide at scales coarser than')
                scale_param.Set(1)
            elif view_type == 'Elevation':
                view_fam_typeid = doc.GetDefaultElementTypeId(ElementTypeGroup.ViewTypeElevation)
                elev_marker = ElevationMarker.CreateElevationMarker(doc, view_fam_typeid, XYZ(0,0,0), 1)
                default_floor_plan = find_first_floorplan()
                dest_view = elev_marker.CreateElevation(doc, default_floor_plan.Id, 0)
                scale_param = dest_view.LookupParameter('Hide at scales coarser than')
                scale_param.Set(1)

            dest_view.ViewName = view_name
            dest_view.Scale = view_scale
            model_visib_param = dest_view.LookupParameter('Display Model')
            model_visib_param.Set(2)
            dest_view.CropBoxActive = False
            dest_view.CropBoxVisible = False
            t.Commit()
            return dest_view
        except Exception as create_err:
            t.RollBack()
            logger.debug('Can not create model view: {} | {}'.format(view_name, create_err))
            raise create_err


def get_copyable_elements(src_view):
    # get drafting view elements and exclude non-copyable elements
    view_elements = FilteredElementCollector(doc, src_view.Id).ToElements()
    elements_to_copy = []
    for el in view_elements:
        if isinstance(el, Element) and el.Category:
            elements_to_copy.append(el.Id)
        else:
            logger.debug('Skipping Element with id: {0}'.format(el.Id))

    return elements_to_copy


def copy_paste_elements_btwn_views(src_view, dest_view):
    elements_to_copy = get_copyable_elements(src_view)
    if len(elements_to_copy) >= 1:
        # copying and pasting elements
        trans_name = 'Copy and Paste elements'
        try:
            with Transaction(doc, trans_name) as t:
                t.Start()

                failure_ops = t.GetFailureHandlingOptions()
                failure_ops.SetFailuresPreprocessor(ViewConverterFailurePreProcessor(trans_name, src_view.ViewName))
                # failure_ops.SetForcedModalHandling(False)
                t.SetFailureHandlingOptions(failure_ops)

                options = CopyPasteOptions()
                options.SetDuplicateTypeNamesHandler(CopyUseDestination())
                copied_element = ElementTransformUtils.CopyElements(src_view,
                                                                    List[ElementId](elements_to_copy),
                                                                    dest_view,
                                                                    None,
                                                                    options)

                # matching element graphics overrides and view properties
                if len(copied_element) != len(elements_to_copy):
                    logger.error('Some elements were not copied from view: {}'.format(src_view.ViewName))
                for dest, src in zip(copied_element, elements_to_copy):
                    dest_view.SetElementOverrides(dest, src_view.GetElementOverrides(src))

                t.Commit()
                return len(copied_element)
        except Exception as err:
            logger.error('Error occured while copying elements from {} | {}'.format(src_view.ViewName, err))
            return 0
    else:
        print('No copyable elements where found.')


drafting_views = process_selection()
dest_view_type = get_modelview_type()
successfully_converted = 0

# iterate over drafting views
with TransactionGroup(doc, 'Convert Drafting to Model') as tg:
    tg.Start()
    tg.IsFailureHandlingForcedModal = False

    for src_view in drafting_views:
        print_md('-----\n**Converting: {}**'.format(src_view.ViewName))
        dest_view_successfully_setup = False
        try:
            dest_view = create_dest_view(dest_view_type, src_view.ViewName, src_view.Scale)
            dest_view_successfully_setup = True
        except Exception as err:
            logger.error('Error creating model view for: {}. Conversion unsuccessful. | {}'.format(src_view.ViewName,
                                                                                                   err))

        if dest_view_successfully_setup:
            print('Copying contents from {} to {}'.format(this_script.output.linkify(src_view.Id),
                                                          this_script.output.linkify(dest_view.Id)))
            el_count = copy_paste_elements_btwn_views(src_view, dest_view)
            if el_count:
                print('Conversion completed. {} elements were copied.\n\n'.format(el_count))
                successfully_converted += 1
            else:
                print('Conversion cancelled. No elements were copied.\n\n')


    tg.Assimilate()

print_md('**{} out of {} views were successfully converted.**'.format(successfully_converted, len(drafting_views)))
