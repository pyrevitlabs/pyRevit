import sys
import clr

from scriptutils import logger
from scriptutils.userinput import CommandSwitchWindow
from revitutils import doc, selection

from System.Collections.Generic import List
from Autodesk.Revit.DB import Element, ElementId, View, ViewType, FilteredElementCollector, BuiltInCategory, \
                              CopyPasteOptions, ElementTransformUtils, ElevationMarker, \
                              Transaction, TransactionGroup, IDuplicateTypeNamesHandler, ViewDuplicateOption, \
                              ViewPlan, ViewDrafting, ViewSection, BoundingBoxXYZ, ElementTypeGroup, XYZ
from Autodesk.Revit.UI import TaskDialog


__doc__ = "Converts selected detail views to selected model view type." \
          "The resulting model views will not show the model and their associated tags are only visible in 1:1 views."


selected_level = None

view_types_dict = {'Floor Plan': ViewPlan,
                   'Section': ViewSection,
                   'Reflected Ceiling Plan': ViewPlan,
                   'Elevation': ViewSection,
                #    'Area Plan': ViewPlan,
                #    'Structural Plan': ViewPlan,
                   }


class CopyUseDestination(IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        return DuplicateTypeAction.UseDestinationTypes


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

    if len(elements_to_copy) < 1:
        logger.debug('Skipping {0}. No copyable elements where found.'.format(src_view.ViewName))

    return elements_to_copy


def copy_paste_elements_btwn_views(src_view, dest_view):
    elements_to_copy = get_copyable_elements(src_view)
    # copying and pasting elements
    try:
        with Transaction(doc, 'Copy and Paste elements') as t:
            t.Start()
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

            t.Commit()
            return True
    except Exception as err:
        logger.error(err)
        return False


drafting_views = process_selection()
dest_view_type = get_modelview_type()

# iterate over drafting views
with TransactionGroup(doc, 'Convert Drafting to Model') as tg:
    tg.Start()
    for src_view in drafting_views:
        logger.info('Converting: {}'.format(src_view.ViewName))
        dest_view_successfully_setup = False
        try:
            dest_view = create_dest_view(dest_view_type, src_view.ViewName, src_view.Scale)
            dest_view_successfully_setup = True
        except Exception as err:
            logger.error('Error converting: {} | {}'.format(src_view.ViewName, err))
            logger.debug(err)

        if dest_view_successfully_setup:
            copy_paste_elements_btwn_views(src_view, dest_view)

    tg.Assimilate()
