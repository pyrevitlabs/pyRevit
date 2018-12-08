#pylint: disable=C0111,E0401,W0613,W0603,W0703,C0301,C0103
import sys
import clr

from pyrevit import framework
from pyrevit import revit, DB
from pyrevit import forms
from pyrevit import script

__title__ = ""
__author__ = "{{author}}"
__context__ = ""
__doc__ = "Converts selected detail views to selected model view type." \
          "The resulting model views will not show the model, and their associated tags are only visible in 1:1 views."


doc = revit.doc
selection = revit.get_selection()
logger = script.get_logger()
output = script.get_output()


selected_level = None

view_types_dict = {'Floor Plan': DB.ViewPlan,
                   'Section': DB.ViewSection,
                   'Reflected Ceiling Plan': DB.ViewPlan,
                   'Elevation': DB.ViewSection,
                   'Drafting': DB.ViewDrafting,
                   # 'Area Plan': DB.ViewPlan,
                   # 'Structural Plan': DB.ViewPlan,
                   }


class CopyUseDestination(DB.IDuplicateTypeNamesHandler):
    def OnDuplicateTypeNamesFound(self, args):
        logger.debug('Duplicate types found. Using destination types.')
        return DB.DuplicateTypeAction.UseDestinationTypes


class ViewConverterFailurePreProcessor(DB.IFailuresPreprocessor):
    def __init__(self, trans_name, view_name):
        self.transaction_name = trans_name
        self.src_viewname = view_name

    def PreprocessFailures(self, failures_accessor):
        trans_name = failures_accessor.GetTransactionName()
        fmas = list(failures_accessor.GetFailureMessages())

        if fmas:
            return DB.FailureProcessingResult.Continue

        # We already know the transaction name.
        if trans_name == self.transaction_name:
            # DeleteWarning mimics clicking 'Ok' button
            for fma in fmas:
                logger.warning('Revit failure occured | {}: {}'
                               .format(fma.GetId().Guid,
                                       fma.GetDescriptionText()))
                failures_accessor.DeleteWarning(fma)

            return DB.FailureProcessingResult.ProceedWithCommit

        return DB.FailureProcessingResult.Continue


def process_selection():
    if not selection.is_empty:
        return selection.elements
    else:
        forms.alert('At least one view must be selected.', exitscript=True)


def get_modelview_type():
    switch = forms.CommandSwitchWindow.show(view_types_dict.keys(),
                                            message='Pick view type:')
    if switch:
        return switch
    else:
        logger.debug('User cancelled.')
        sys.exit(0)


def get_view_level():
    global selected_level
    if not selected_level:
        levels = DB.FilteredElementCollector(doc)\
                   .OfCategory(DB.BuiltInCategory.OST_Levels)\
                   .WhereElementIsNotElementType()\
                   .ToElements()
        levels_dict = {lvl.Name:lvl for lvl in levels}
        picked_level = \
            forms.CommandSwitchWindow.show(levels_dict.keys(),
                                           message='Pick level:')
        selected_level = levels_dict[picked_level]

    return selected_level


def find_first_floorplan():
    view_list = list(DB.FilteredElementCollector(doc)\
                       .OfClass(clr.GetClrType(DB.ViewPlan))\
                       .WhereElementIsNotElementType()\
                       .ToElements())
    for view in view_list:
        if view.ViewType == DB.ViewType.FloorPlan:
            return view


def create_dest_view(view_type, view_name, view_scale):
    with DB.Transaction(doc, 'Create model view') as t:
        t.Start()
        try:
            new_dest_view = None

            if view_type == 'Floor Plan':
                level = get_view_level()
                view_fam_typeid = \
                    doc.GetDefaultElementTypeId(
                        DB.ElementTypeGroup.ViewTypeFloorPlan
                        )
                new_dest_view = \
                    DB.ViewPlan.Create(doc, view_fam_typeid, level.Id)

            elif view_type == 'Reflected Ceiling Plan':
                level = get_view_level()
                view_fam_typeid = \
                    doc.GetDefaultElementTypeId(
                        DB.ElementTypeGroup.ViewTypeCeilingPlan
                    )
                new_dest_view = \
                    DB.ViewPlan.Create(doc, view_fam_typeid, level.Id)

            elif view_type == 'Section':
                view_fam_typeid = \
                    doc.GetDefaultElementTypeId(
                        DB.ElementTypeGroup.ViewTypeSection
                        )
                view_direction = DB.BoundingBoxXYZ()
                trans_identity = DB.Transform.Identity
                trans_identity.BasisX = -DB.XYZ.BasisX    # x direction
                trans_identity.BasisY = DB.XYZ.BasisZ    # up direction
                trans_identity.BasisZ = DB.XYZ.BasisY    # view direction
                view_direction.Transform = trans_identity
                new_dest_view = \
                    DB.ViewSection.CreateSection(doc,
                                                 view_fam_typeid,
                                                 view_direction)
                scale_param = new_dest_view.Parameter[
                    DB.BuiltInParameter.SECTION_COARSER_SCALE_PULLDOWN_IMPERIAL
                    ]
                scale_param.Set(1)

            elif view_type == 'Elevation':
                view_fam_typeid = \
                    doc.GetDefaultElementTypeId(
                        DB.ElementTypeGroup.ViewTypeElevation
                        )
                elev_marker = \
                    DB.ElevationMarker.CreateElevationMarker(
                        doc,
                        view_fam_typeid,
                        DB.XYZ(0, 0, 0),
                        1)
                default_floor_plan = find_first_floorplan()
                new_dest_view = \
                    elev_marker.CreateElevation(doc, default_floor_plan.Id, 0)
                scale_param = new_dest_view.Parameter[
                    DB.BuiltInParameter.SECTION_COARSER_SCALE_PULLDOWN_IMPERIAL
                    ]
                scale_param.Set(1)
            elif view_type == 'Drafting':
                view_fam_typeid = \
                    doc.GetDefaultElementTypeId(
                        DB.ElementTypeGroup.ViewTypeDrafting
                        )
                new_dest_view = DB.ViewDrafting.Create(doc, view_fam_typeid)

            new_dest_view.ViewName = view_name
            new_dest_view.Scale = view_scale
            model_visib_param = new_dest_view.Parameter[
                DB.BuiltInParameter.VIEW_MODEL_DISPLAY_MODE
                ]
            if model_visib_param:
                model_visib_param.Set(2)
            new_dest_view.CropBoxActive = False
            new_dest_view.CropBoxVisible = False
            t.Commit()
            return new_dest_view
        except Exception as create_err:
            t.RollBack()
            logger.debug('Can not create model view: {} | {}'
                         .format(view_name, create_err))
            raise create_err


def get_copyable_elements(source_view):
    # get drafting view elements and exclude non-copyable elements
    view_elements = \
        DB.FilteredElementCollector(doc, source_view.Id).ToElements()
    elements_to_copy = []
    for el in view_elements:
        if isinstance(el, DB.Element) and el.Category:
            elements_to_copy.append(el.Id)
        else:
            logger.debug('Skipping Element with id: {0}'.format(el.Id))

    return elements_to_copy


def copy_paste_elements_btwn_views(source_view, destination_view):
    elements_to_copy = get_copyable_elements(source_view)
    if len(elements_to_copy) >= 1:
        # copying and pasting elements
        trans_name = 'Copy and Paste elements'
        try:
            with DB.Transaction(doc, trans_name) as t:
                t.Start()

                failure_ops = t.GetFailureHandlingOptions()
                failure_ops.SetFailuresPreprocessor(
                    ViewConverterFailurePreProcessor(
                        trans_name,
                        source_view.ViewName))
                # failure_ops.SetForcedModalHandling(False)
                t.SetFailureHandlingOptions(failure_ops)

                options = DB.CopyPasteOptions()
                options.SetDuplicateTypeNamesHandler(CopyUseDestination())
                copied_element = \
                    DB.ElementTransformUtils.CopyElements(
                        source_view,
                        framework.List[DB.ElementId](elements_to_copy),
                        destination_view,
                        None,
                        options
                        )

                # matching element graphics overrides and view properties
                if len(copied_element) != len(elements_to_copy):
                    logger.warning('Some elements were not copied from view: {}'
                                   .format(source_view.ViewName))
                for dest, src in zip(copied_element, elements_to_copy):
                    destination_view.SetElementOverrides(
                        dest,
                        source_view.GetElementOverrides(src))

                t.Commit()
                return len(copied_element)
        except Exception as err:
            logger.error('Error occured while copying elements from {} | {}'
                         .format(source_view.ViewName, err))
            return 0
    else:
        print('No copyable elements where found.')


drafting_views = process_selection()
dest_view_type = get_modelview_type()
successfully_converted = 0

# iterate over drafting views
with DB.TransactionGroup(doc, 'Convert View Types') as tg:
    tg.Start()
    tg.IsFailureHandlingForcedModal = False
    view_count = 1
    total_view_count = len(drafting_views)

    for src_view in drafting_views:
        output.print_md('-----\n**{} of {}**'
                        .format(view_count, total_view_count))
        output.print_md('**Converting: {}**'
                        .format(src_view.ViewName))
        dest_view_successfully_setup = False
        try:
            dest_view = \
                create_dest_view(dest_view_type,
                                 src_view.ViewName,
                                 src_view.Scale)
            print('View created: {}'.format(dest_view.ViewName))
            dest_view_successfully_setup = True
        except Exception as err:
            logger.error('Error creating model view for: {}. '
                         'Conversion unsuccessful. | {}'
                         .format(src_view.ViewName, err))

        if dest_view_successfully_setup:
            print('Copying 2D contents from {} to {}'
                  .format(output.linkify(src_view.Id),
                          output.linkify(dest_view.Id)))
            el_count = copy_paste_elements_btwn_views(src_view, dest_view)
            if el_count:
                print('Conversion completed. {} elements were copied.\n\n'
                      .format(el_count))
                successfully_converted += 1
            else:
                print('Conversion cancelled. No elements were copied.\n\n')

        view_count += 1
        output.update_progress(view_count, total_view_count)

    tg.Assimilate()

output.print_md('**{} out of {} views were successfully converted.**'
                .format(successfully_converted, len(drafting_views)))
