import clr
from scriptutils import this_script, logger
from revitutils import doc, uidoc, Action, ActionGroup

# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import *


def dependent(func):
    func.is_dependent = True
    return func


def notdependent(func):
    func.is_dependent = False
    return func


def print_header(header):
    this_script.output.insert_divider()
    this_script.output.print_md('### {}'.format(header))


def log_debug(message):
    logger.debug(message)


def log_error(el_type='', el_id=0, delete_err=None):
    err_msg = str(delete_err).replace('\n', ' ').replace('\r', '')
    logger.error('Error Removing Element with Id: {} Type: {} | {}'.format(el_type, el_id, err_msg))


def remove_action(action_title, action_cat, elements_to_remove, validity_func=None):
    def remove_element(rem_el):
        if rem_el:
            try:
                log_debug('Removing element:{} id:{}'.format(rem_el, rem_el.Id))
                doc.Delete(rem_el.Id)
                return True
            except Exception as e:
                if hasattr(rem_el, 'Id'):
                    log_error(el_type=action_cat, el_id=rem_el.Id, delete_err=e)
                else:
                    log_error(el_type=action_cat, delete_err=e)
        else:
            log_debug('Element does not have value. It might have been already removed by other actions.')

        return False

    with Action(action_title):
        for element in elements_to_remove:
            if validity_func:
                if validity_func(element):
                    remove_element(element)
            else:
                remove_element(element)


@notdependent
def call_purge():
    """Call Revit "Purge Unused" after completion."""
    from Autodesk.Revit.UI import PostableCommand as pc
    from Autodesk.Revit.UI import RevitCommandId as rcid
    cid_PurgeUnused = rcid.LookupPostableCommandId(pc.PurgeUnused)
    __revit__.PostCommand(cid_PurgeUnused)


@dependent
def remove_all_constraints():
    """Remove All Constraints"""

    def confirm_removal(cnst):
        return cnst.View is not None

    cl = FilteredElementCollector(doc)
    consts = list(cl.OfCategory(BuiltInCategory.OST_Constraints).WhereElementIsNotElementType())

    print_header('REMOVING ALL CONSTRAINTS')
    remove_action('Remove All Constraints', 'Constraint', consts, validity_func=confirm_removal)


@notdependent
def remove_all_groups():
    """Remove (and Explode) All Groups"""

    def confirm_removal(group_typeid):
        group_type = doc.GetElement(group_typeid)
        return group_type and group_type.Category.Name != 'Attached Detail Groups'

    group_types = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(GroupType)).ToElementIds())
    groups = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(Group)).ToElements())

    print_header('EXPLODING GROUPS')         # ungroup all groups

    with ActionGroup('Remove All Groups', assimilate=True):
        with Action('Exploding All Groups'):
            for grp in groups:
                grp.UngroupMembers()

        print_header('REMOVING GROUPS')          # delete group types
        remove_action('Remove All Groups', 'Group Type', group_types, validity_func=confirm_removal)


@notdependent
def remove_all_external_links():
    """Remove All External Links"""

    def confirm_removal(refId):
        link_el = doc.GetElement(refId)
        return isinstance(link_el, RevitLinkType) or isinstance(link_el, CADLinkType)

    if doc.PathName:
        modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(doc.PathName)
        transData = TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        cl = FilteredElementCollector(doc)
        import_instances = list(cl.OfClass(clr.GetClrType(ImportInstance)).ToElements())

        print_header('REMOVE ALL EXTERNAL LINKS')
        remove_action('Remove All External Links', 'External Link', import_instances, validity_func=confirm_removal)
    else:
        log_error('Model must be saved for external links to be removed.')


@notdependent
def remove_all_sheets():
    """Remove All Sheets"""

    cl = FilteredElementCollector(doc)
    sheets = cl.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
    open_UIViews = uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(sht):
        return sht.Id.IntegerValue in open_views

    print_header('REMOVING SHEETS')
    remove_action('Remove All Sheets', 'Sheet', sheets, validity_func=confirm_removal)


@dependent
def remove_all_rooms():
    """Remove All Rooms"""

    cl = FilteredElementCollector(doc)
    rooms = cl.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING ROOMS')
    remove_action('Remove All Rooms', 'Room', rooms)


@dependent
def remove_all_areas():
    """Remove All Areas"""

    cl = FilteredElementCollector(doc)
    areas = cl.OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING AREAS')
    remove_action('Remove All Areas', 'Area', areas)


@notdependent
def remove_all_room_separation_lines():
    """Remove All Room Separation Lines"""

    cl = FilteredElementCollector(doc)
    rslines = cl.OfCategory(BuiltInCategory.OST_RoomSeparationLines).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING ROOM SEPARATIONS LINES')
    remove_action('Remove All Room Separation Lines', 'Room Separation Line', rslines)


@notdependent
def remove_all_area_separation_lines():
    """Remove All Area Separation Lines"""

    cl = FilteredElementCollector(doc)
    aslines = cl.OfCategory(BuiltInCategory.OST_AreaSchemeLines).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING AREA SEPARATIONS LINES')
    remove_action('Remove All Area Separation Lines', 'Area Separation Line', aslines)


@notdependent
def remove_all_scope_boxes():
    """Remove All Scope Boxes"""

    cl = FilteredElementCollector(doc)
    scopeboxes = cl.OfCategory(BuiltInCategory.OST_VolumeOfInterest).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING SCOPE BOXES')
    remove_action('Remove All ScopeBoxes', 'Scope Box', scopeboxes)


@notdependent
def remove_all_reference_planes():
    """Remove All Reference Planes"""

    cl = FilteredElementCollector(doc)
    refplanes = cl.OfCategory(BuiltInCategory.OST_CLines).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING REFERENCE PLANES')
    remove_action('Remove All Reference Planes', 'Reference Plane', refplanes)


@notdependent
def remove_all_materials():
    """Remove All Materials"""

    def confirm_removal(mat):
        if 'poche' in mat.Name.lower():
            return False
        return True

    cl = FilteredElementCollector(doc)
    mats = cl.OfCategory(BuiltInCategory.OST_Materials).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING MATERIALS')
    remove_action('Remove All Materials', 'Material', mats, validity_func=confirm_removal)


READONLY_VIEWS = [ViewType.ProjectBrowser,
                  ViewType.SystemBrowser,
                  ViewType.Undefined,
                  ViewType.DrawingSheet,
                  ViewType.Internal]

@notdependent
def remove_all_views():
    """Remove All Views"""

    cl = FilteredElementCollector(doc)
    views = set(cl.OfClass(View).WhereElementIsNotElementType().ToElementIds())
    open_UIViews = uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(v):
        if isinstance(v, View):
            if ViewType.ThreeD == v.ViewType and '{3D}' == v.ViewName:
                return False
            elif '<' in v.ViewName or v.IsTemplate:
                return False
            elif vid.IntegerValue in open_views:
                return False
            else:
                return True
        else:
            return False

    print_header('REMOVING VIEWS / LEGENDS / SCHEDULES')
    remove_action('Remove All Views', 'View', views, validity_func=confirm_removal)


@notdependent
def remove_all_view_templates():
    """Remove All View Templates"""

    def confirm_removal(v):
        if isinstance(v, View) \
        and v.IsTemplate \
        and v.ViewType not in READONLY_VIEWS:
                return True
        else:
            return False

    cl = FilteredElementCollector(doc)
    views = set(cl.OfClass(View).WhereElementIsNotElementType().ToElements())

    print_header('REMOVING ALL VIEW TEMPLATES')
    remove_action('Remove All View Templates', 'View Templates', views, validity_func=confirm_removal)


@notdependent
def remove_all_elevation_markers():
    """Remove All Elevation Markers"""

    def confirm_removal(elev_marker):
        return elev_marker.CurrentViewCount == 0

    cl = FilteredElementCollector(doc)
    elev_markers = cl.OfClass(ElevationMarker).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING ELEVATION MARKERS')
    remove_action('Remove All Elevation Markers', 'Elevation Marker', elev_markers, validity_func=confirm_removal)


@notdependent
def remove_all_filters():
    """Remove All Filters"""

    cl = FilteredElementCollector(doc)
    filters = cl.OfClass(FilterElement).WhereElementIsNotElementType().ToElements()

    print_header('REMOVING ALL FILTERS')
    remove_action('Remove All Filters', 'View Filter', filters)


# dynamically generate function that remove all elements on a workset, based on current model worksets
@notdependent
def template_workset_remover(workset_name=None):
    workset_list = FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset)
    workset_dict = {workset.Name:workset.Id for workset in workset_list}

    element_workset_filter = ElementWorksetFilter(workset_dict[workset_name], False)
    workset_elements = FilteredElementCollector(doc).WherePasses(element_workset_filter).ToElements()

    print_header('REMOVING ALL ELEMENTS ON WORKSET "{}"'.format(workset_name))
    remove_action('Remove All on WS: {}'.format(workset_name), 'Workset Element', workset_elements)


import types
def copy_func(f, workset_name):
    new_func = types.FunctionType(f.func_code, f.func_globals,
                                  '{}_{}'.format(f.func_name, workset_name),            # function name
                                  tuple([workset_name]),                                # function name
                                  f.func_closure)
    # set the docstring
    new_func.__doc__ = 'Remove All Elements on Workset "{}"'.format(workset_name)
    new_func.is_dependent = False
    return new_func

# if model is workshared, get a list of current worksets
if doc.IsWorkshared:
    cl = FilteredWorksetCollector(doc)
    worksetlist = cl.OfKind(WorksetKind.UserWorkset)
    # duplicate the workset element remover function for each workset
    for workset in worksetlist:
        locals()[workset.Name] = copy_func(template_workset_remover, workset.Name)
