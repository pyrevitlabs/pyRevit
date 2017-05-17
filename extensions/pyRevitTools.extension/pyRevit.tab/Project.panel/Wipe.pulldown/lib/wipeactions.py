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
    logger.warning('Error Removing Element with Id: {} Type: {} | {}'.format(el_id, el_type, err_msg))


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


    rem_count = len(elements_to_remove)
    this_script.output.reset_progress()
    with Action(action_title):
        for idx, element in enumerate(elements_to_remove):
            this_script.output.update_progress(idx + 1, rem_count)
            if validity_func:
                try:
                    if validity_func(element):
                        remove_element(element)
                except Exception as e:
                    log_debug('Validity func failed. | {}'.format(e))
                    continue
            else:
                remove_element(element)

    print('Completed...\n')


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
    consts = list(cl.OfCategory(BuiltInCategory.OST_Constraints).WhereElementIsNotElementType().ToElements())

    print_header('REMOVING ALL CONSTRAINTS')
    remove_action('Remove All Constraints', 'Constraint', consts, validity_func=confirm_removal)


@notdependent
def remove_all_groups():
    """Remove (and Explode) All Groups"""

    def confirm_removal(group_type):
        return group_type and group_type.Category.Name != 'Attached Detail Groups'

    group_types = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(GroupType)).ToElements())
    groups = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(Group)).ToElements())

    print_header('EXPLODING GROUPS')         # ungroup all groups

    with ActionGroup('Remove All Groups', assimilate=True):
        with Action('Exploding All Groups'):
            for grp in groups:
                grp.UngroupMembers()

        # delete group types
        this_script.output.print_md('### {}'.format('REMOVING GROUPS'))
        remove_action('Remove All Groups', 'Group Type', group_types, validity_func=confirm_removal)


@dependent
def remove_all_external_links():
    """Remove All External Links"""

    def confirm_removal(link_el):
        return isinstance(link_el, RevitLinkType) or isinstance(link_el, CADLinkType)

    print_header('REMOVE ALL EXTERNAL LINKS')

    if doc.PathName:
        modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(doc.PathName)
        try:
            transData = TransmissionData.ReadTransmissionData(modelPath)
            externalReferences = transData.GetAllExternalFileReferenceIds()
            xref_links = [doc.GetElement(x) for x in externalReferences]
        except:
            logger.warning('Model must be saved for external links to be removed.')
            return

        remove_action('Remove All External Links', 'External Link', xref_links, validity_func=confirm_removal)
    else:
        logger.warning('Model must be saved for external links to be removed.')


@notdependent
def remove_all_sheets():
    """Remove All Sheets (except open sheets)"""

    cl = FilteredElementCollector(doc)
    sheets = cl.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
    open_UIViews = uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(sht):
        return isinstance(sht, ViewSheet) and sht.Id.IntegerValue not in open_views

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


@notdependent
def remove_all_render_materials():
    """Remove All Materials (only Render Materials)"""

    cl = FilteredElementCollector(doc)
    mats = cl.OfCategory(BuiltInCategory.OST_Materials).WhereElementIsNotElementType().ToElements()
    render_mats = [x for x in mats if x.Name.startswith('Render Material')]

    print_header('REMOVING MATERIALS')
    remove_action('Remove All Render Materials', 'Render Material', render_mats)


@notdependent
def remove_all_imported_lines():
    """Remove All Imported Line Patterns"""

    cl = FilteredElementCollector(doc)
    line_pats = cl.OfClass(LinePatternElement).ToElements()
    import_lines = [x for x in line_pats if x.Name.lower().startswith('import')]

    print_header('REMOVING MATERIALS')
    remove_action('Remove All Import Lines', 'Line Pattern', import_lines)


READONLY_VIEWS = [ViewType.ProjectBrowser,
                  ViewType.SystemBrowser,
                  ViewType.Undefined,
                  ViewType.DrawingSheet,
                  ViewType.Internal]

def _purge_all_views(viewclass_to_purge, viewtype_to_purge, header, action_title, action_cat):
    cl = FilteredElementCollector(doc)
    views = set(cl.OfClass(viewclass_to_purge).WhereElementIsNotElementType().ToElements())
    open_UIViews = uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(v):
        if isinstance(v, viewclass_to_purge):
            if viewtype_to_purge and v.ViewType != viewtype_to_purge:
                return False
            elif v.ViewType in READONLY_VIEWS:
                return False
            elif v.IsTemplate:
                return False
            elif ViewType.ThreeD == v.ViewType and '{3D}' == v.ViewName:
                return False
            elif '<' in v.ViewName:
                return False
            elif v.Id.IntegerValue in open_views:
                return False
            else:
                return True
        else:
            return False

    print_header(header)
    remove_action(action_title, action_cat, views, validity_func=confirm_removal)


@dependent
def remove_all_views():
    """Remove All Views (of any kind, except open views and sheets)"""

    # (View3D, ViewPlan, ViewDrafting, ViewSection, ViewSchedule)
    _purge_all_views(View, None,
                     'REMOVING DRAFTING, PLAN, SECTION, AND ELEVATION VIEWS',
                     'Remove All Views', 'View')


@dependent
def remove_all_plans():
    """Remove All Views (Floor Plans only)"""

    _purge_all_views(ViewPlan, ViewType.FloorPlan,
                     'REMOVING PLAN VIEWS',
                     'Remove All Plan Views', 'Plan View')


@dependent
def remove_all_rcps():
    """Remove All Views (Reflected Ceiling Plans only)"""

    _purge_all_views(ViewPlan, ViewType.CeilingPlan,
                     'REMOVING RCP VIEWS',
                     'Remove All Reflected Ceiling Plans', 'Ceiling View')


@dependent
def remove_all_engplan():
    """Remove All Views (Engineering Plans only)"""

    _purge_all_views(ViewPlan, ViewType.EngineeringPlan,
                     'REMOVING ENGINEERING VIEWS',
                     'Remove All Engineering Plans', 'Engineering View')


@dependent
def remove_all_engplan():
    """Remove All Views (Area Plans only)"""

    _purge_all_views(ViewPlan, ViewType.AreaPlan,
                     'REMOVING AREA VIEWS',
                     'Remove All Area Plans', 'Area View')


@dependent
def remove_all_threed():
    """Remove All Views (3D Views only)"""

    _purge_all_views(View3D, ViewType.ThreeD,
                     'REMOVING 3D VIEWS',
                     'Remove All 3D Views', '3D View')


@dependent
def remove_all_drafting():
    """Remove All Views (Drafting Views only)"""

    _purge_all_views(ViewDrafting, None,
                     'REMOVING DRAFTING VIEWS',
                     'Remove All Drafting Views', 'Drafting View')


@dependent
def remove_all_sections():
    """Remove All Views (Sections only)"""
    _purge_all_views(ViewSection, ViewType.Section,
                     'REMOVING SECTION VIEWS',
                     'Remove All Section Views', 'Section View')


@dependent
def remove_all_elevations():
    """Remove All Views (Elevations only)"""
    _purge_all_views(ViewSection, ViewType.Elevation,
                     'REMOVING SECTION VIEWS',
                     'Remove All Section Views', 'Section View')


@dependent
def remove_all_schedules():
    """Remove All Views (Schedules only)"""

    cl = FilteredElementCollector(doc)
    sched_views = set(cl.OfClass(ViewSchedule).WhereElementIsNotElementType().ToElements())
    open_UIViews = uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(v):
        if isinstance(v, ViewSchedule):
            if v.ViewType in READONLY_VIEWS:
                return False
            elif v.IsTemplate:
                return False
            elif '<' in v.ViewName:
                return False
            elif v.Id.IntegerValue in open_views:
                return False
            elif v.Definition.CategoryId == Category.GetCategory(doc, BuiltInCategory.OST_KeynoteTags).Id:
                return False
            else:
                return True
        else:
            return False

    print_header('REMOVING SCHEDULES')
    remove_action('Remove All Schedules', 'Schedule', sched_views, validity_func=confirm_removal)


@dependent
def remove_all_legends():
    """Remove All Views (Legends only)"""

    cl = FilteredElementCollector(doc)
    legend_views = set(cl.OfClass(View).WhereElementIsNotElementType().ToElements())
    open_UIViews = uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(v):
        if isinstance(v, View) and v.ViewType == ViewType.Legend:
            if v.ViewType in READONLY_VIEWS:
                return False
            elif v.IsTemplate:
                return False
            elif '<' in v.ViewName:
                return False
            elif v.Id.IntegerValue in open_views:
                return False
            else:
                return True
        elif isinstance(v, ViewSchedule) \
            and v.Definition.CategoryId == Category.GetCategory(doc, BuiltInCategory.OST_KeynoteTags).Id:
                return True
        else:
            return False

    print_header('REMOVING LEGENDS')
    remove_action('Remove All Legends', 'Legend', legend_views, validity_func=confirm_removal)


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


@notdependent
def remove_all_model_patterns():
    """Remove All Patterns (Model)"""

    cl = FilteredElementCollector(doc)
    pattern_elements = cl.OfClass(FillPatternElement).WhereElementIsNotElementType().ToElements()
    model_patterns = [x for x in pattern_elements if x.GetFillPattern().Target == FillPatternTarget.Model]

    print_header('REMOVING ALL MODEL PATTERNS')
    remove_action('Remove All Model Patterns', 'Model Pattern', model_patterns)


@notdependent
def remove_all_drafting_patterns():
    """Remove All Patterns (Drafting)"""

    cl = FilteredElementCollector(doc)
    pattern_elements = cl.OfClass(FillPatternElement).WhereElementIsNotElementType().ToElements()
    draft_patterns = [x for x in pattern_elements if x.GetFillPattern().Target == FillPatternTarget.Drafting]

    print_header('REMOVING ALL DRAFTING PATTERNS')
    remove_action('Remove All Drafting Patterns', 'Drafting Pattern', draft_patterns)


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
