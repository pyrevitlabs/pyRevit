import types
from collections import namedtuple

from pyrevit import framework
from pyrevit import coreutils
from pyrevit import revit, DB, UI
from pyrevit import script
from pyrevit import compat


logger = coreutils.logger.get_logger(__name__)


def dependent(func):
    func.is_dependent = True
    func.is_wipe_action = True
    return func


def notdependent(func):
    func.is_dependent = False
    func.is_wipe_action = True
    return func


def print_header(header):
    output = script.get_output()
    output.insert_divider()
    output.print_md('### {}'.format(header))


def log_debug(message):
    logger.debug(message)


def log_error(el_type='', el_id=0, delete_err=None):
    err_msg = str(delete_err).replace('\n', ' ').replace('\r', '')
    logger.warning('Error Removing Element with Id: {} Type: {} | {}'
                   .format(el_id, el_type, err_msg))


def remove_action(action_title, action_cat,
                  elements_to_remove,
                  validity_func=None):
    def remove_element(rem_el):
        if rem_el:
            try:
                log_debug('Removing element:{} id:{}'.format(rem_el,
                                                             rem_el.Id))
                revit.doc.Delete(rem_el.Id)
                return True
            except Exception as e:
                if hasattr(rem_el, 'Id'):
                    log_error(el_type=action_cat,
                              el_id=rem_el.Id,
                              delete_err=e)
                else:
                    log_error(el_type=action_cat, delete_err=e)
        else:
            log_debug('Element does not have value. '
                      'It might have been already removed by other actions.')

        return False

    output = script.get_output()
    output.reset_progress()

    rem_count = len(elements_to_remove)
    with revit.Transaction(action_title):
        for idx, element in enumerate(elements_to_remove):
            output.update_progress(idx + 1, rem_count)
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
    cid_PurgeUnused = \
        UI.RevitCommandId.LookupPostableCommandId(
            UI.PostableCommand.PurgeUnused
            )
    __revit__.PostCommand(cid_PurgeUnused)


@dependent
def remove_all_constraints():
    """Remove All Constraints"""

    cl = DB.FilteredElementCollector(revit.doc)
    consts = list(cl.OfCategory(DB.BuiltInCategory.OST_Constraints)
                    .WhereElementIsNotElementType()
                    .ToElements())

    print_header('REMOVING ALL CONSTRAINTS')
    remove_action('Remove All Constraints', 'Constraint', consts)


@dependent
def remove_all_viewspecific_constraints():
    """Remove All View-Specific Constraints"""

    def confirm_removal(cnst):
        return cnst.View is not None

    cl = DB.FilteredElementCollector(revit.doc)
    consts = list(cl.OfCategory(DB.BuiltInCategory.OST_Constraints)
                    .WhereElementIsNotElementType()
                    .ToElements())

    print_header('REMOVING ALL VIEW-SPECIFIC CONSTRAINTS')
    remove_action('Remove All View-Specific Constraints',
                  'Constraint',
                  consts, validity_func=confirm_removal)


@notdependent
def remove_all_groups():
    """Remove (and Explode) All Groups"""

    def confirm_removal(group_type):
        return group_type \
            and group_type.Category.Name != 'Attached Detail Groups'

    group_types = list(DB.FilteredElementCollector(revit.doc)
                         .OfClass(framework.get_type(DB.GroupType))
                         .ToElements())
    groups = list(DB.FilteredElementCollector(revit.doc)
                    .OfClass(framework.get_type(DB.Group))
                    .ToElements())

    output = script.get_output()
    print_header('EXPLODING GROUPS')         # ungroup all groups

    with revit.TransactionGroup('Remove All Groups', assimilate=True):
        with revit.Transaction('Exploding All Groups'):
            for grp in groups:
                grp.UngroupMembers()

        # delete group types
        output.print_md('### {}'.format('REMOVING GROUPS'))
        remove_action('Remove All Groups',
                      'Group Type',
                      group_types,
                      validity_func=confirm_removal)


@dependent
def remove_all_external_links():
    """Remove All External Links"""

    def confirm_removal(link_el):
        return isinstance(link_el, DB.RevitLinkType) \
                or isinstance(link_el, DB.CADLinkType)

    print_header('REMOVE ALL EXTERNAL LINKS')

    filepath = revit.doc.PathName
    if filepath:
        modelPath = \
            DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(filepath)
        try:
            transData = DB.TransmissionData.ReadTransmissionData(modelPath)
            externalReferences = transData.GetAllExternalFileReferenceIds()
            xref_links = [revit.doc.GetElement(x) for x in externalReferences]
        except Exception:
            logger.warning('Model must be saved for external '
                           'links to be removed.')
            return

        remove_action('Remove All External Links',
                      'External Link',
                      xref_links,
                      validity_func=confirm_removal)
    else:
        logger.warning('Model must be saved for external links to be removed.')


@notdependent
def remove_all_sheets():
    """Remove All Sheets (except open sheets)"""

    cl = DB.FilteredElementCollector(revit.doc)
    sheets = cl.OfCategory(DB.BuiltInCategory.OST_Sheets)\
               .WhereElementIsNotElementType()\
               .ToElements()
    open_UIViews = revit.uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(sht):
        return isinstance(sht, DB.ViewSheet) \
                and sht.Id.IntegerValue not in open_views

    print_header('REMOVING SHEETS')
    remove_action('Remove All Sheets',
                  'Sheet',
                  sheets,
                  validity_func=confirm_removal)


@dependent
def remove_all_rooms():
    """Remove All Rooms"""

    cl = DB.FilteredElementCollector(revit.doc)
    rooms = cl.OfCategory(DB.BuiltInCategory.OST_Rooms)\
              .WhereElementIsNotElementType()\
              .ToElements()

    print_header('REMOVING ROOMS')
    remove_action('Remove All Rooms', 'Room', rooms)


@dependent
def remove_all_areas():
    """Remove All Areas"""

    cl = DB.FilteredElementCollector(revit.doc)
    areas = cl.OfCategory(DB.BuiltInCategory.OST_Areas)\
              .WhereElementIsNotElementType()\
              .ToElements()

    print_header('REMOVING AREAS')
    remove_action('Remove All Areas', 'Area', areas)


@notdependent
def remove_all_room_separation_lines():
    """Remove All Room Separation Lines"""

    cl = DB.FilteredElementCollector(revit.doc)
    rslines = cl.OfCategory(DB.BuiltInCategory.OST_RoomSeparationLines)\
                .WhereElementIsNotElementType()\
                .ToElements()

    print_header('REMOVING ROOM SEPARATIONS LINES')
    remove_action('Remove All Room Separation Lines',
                  'Room Separation Line',
                  rslines)


@notdependent
def remove_all_area_separation_lines():
    """Remove All Area Separation Lines"""

    cl = DB.FilteredElementCollector(revit.doc)
    aslines = cl.OfCategory(DB.BuiltInCategory.OST_AreaSchemeLines)\
                .WhereElementIsNotElementType()\
                .ToElements()

    print_header('REMOVING AREA SEPARATIONS LINES')
    remove_action('Remove All Area Separation Lines',
                  'Area Separation Line',
                  aslines)


@notdependent
def remove_all_scope_boxes():
    """Remove All Scope Boxes"""

    cl = DB.FilteredElementCollector(revit.doc)
    scopeboxes = cl.OfCategory(DB.BuiltInCategory.OST_VolumeOfInterest)\
                   .WhereElementIsNotElementType()\
                   .ToElements()

    print_header('REMOVING SCOPE BOXES')
    remove_action('Remove All ScopeBoxes', 'Scope Box', scopeboxes)


@notdependent
def remove_all_reference_planes():
    """Remove All Reference Planes"""

    cl = DB.FilteredElementCollector(revit.doc)
    refplanes = cl.OfCategory(DB.BuiltInCategory.OST_CLines)\
                  .WhereElementIsNotElementType()\
                  .ToElements()

    print_header('REMOVING REFERENCE PLANES')
    remove_action('Remove All Reference Planes', 'Reference Plane', refplanes)


@notdependent
def remove_all_unnamed_reference_planes():
    """Remove All Reference Planes (Unnamed Only)"""

    cl = DB.FilteredElementCollector(revit.doc)
    refplanes = cl.OfCategory(DB.BuiltInCategory.OST_CLines)\
                  .WhereElementIsNotElementType()\
                  .ToElements()
    unnamed_refplanes = [
        x for x in refplanes
        if not x.Parameter[DB.BuiltInParameter.DATUM_TEXT].AsString()
        ]
    print_header('REMOVING REFERENCE PLANES')
    remove_action('Remove All Reference Planes', 'Reference Plane',
                  unnamed_refplanes)


@notdependent
def remove_all_materials():
    """Remove All Materials"""

    def confirm_removal(mat):
        if 'poche' in mat.Name.lower():
            return False
        return True

    cl = DB.FilteredElementCollector(revit.doc)
    mats = cl.OfCategory(DB.BuiltInCategory.OST_Materials)\
             .WhereElementIsNotElementType()\
             .ToElements()

    print_header('REMOVING MATERIALS')
    remove_action('Remove All Materials',
                  'Material',
                  mats,
                  validity_func=confirm_removal)


@notdependent
def remove_all_render_materials():
    """Remove All Materials (only Render Materials)"""

    cl = DB.FilteredElementCollector(revit.doc)
    mats = cl.OfCategory(DB.BuiltInCategory.OST_Materials)\
             .WhereElementIsNotElementType()\
             .ToElements()
    render_mats = [x for x in mats if x.Name.startswith('Render Material')]

    print_header('REMOVING MATERIALS')
    remove_action('Remove All Render Materials',
                  'Render Material',
                  render_mats)


@notdependent
def remove_all_imported_lines():
    """Remove All Imported Line Patterns"""

    cl = DB.FilteredElementCollector(revit.doc)
    line_pats = cl.OfClass(DB.LinePatternElement).ToElements()
    import_lines = [x for x in line_pats
                    if x.Name.lower().startswith('import')]

    print_header('REMOVING MATERIALS')
    remove_action('Remove All Import Lines', 'Line Pattern', import_lines)


READONLY_VIEWS = [DB.ViewType.ProjectBrowser,
                  DB.ViewType.SystemBrowser,
                  DB.ViewType.Undefined,
                  DB.ViewType.DrawingSheet,
                  DB.ViewType.Internal]


VIEWREF_PREFIX = {DB.ViewType.CeilingPlan: 'Reflected Ceiling Plan: ',
                  DB.ViewType.FloorPlan: 'Floor Plan: ',
                  DB.ViewType.EngineeringPlan: 'Structural Plan: ',
                  DB.ViewType.DraftingView: 'Drafting View: ',
                  DB.ViewType.Section: 'Section: ',
                  DB.ViewType.ThreeD: '3D View: '}


def _purge_all_views(viewclass_to_purge, viewtype_to_purge,
                     header, action_title, action_cat, keep_referenced=False):
    cl = DB.FilteredElementCollector(revit.doc)
    views = set(cl.OfClass(viewclass_to_purge)
                  .WhereElementIsNotElementType()
                  .ToElements())

    open_UIViews = revit.uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def is_referenced(v):
        view_refs = DB.FilteredElementCollector(revit.doc)\
                      .OfCategory(DB.BuiltInCategory.OST_ReferenceViewer)\
                      .WhereElementIsNotElementType()\
                      .ToElements()

        view_refs_names = set()
        for view_ref in view_refs:
            ref_param = view_ref.Parameter[
                DB.BuiltInParameter.REFERENCE_VIEWER_TARGET_VIEW
                ]
            view_refs_names.add(ref_param.AsValueString())

        refsheet = v.Parameter[DB.BuiltInParameter.VIEW_REFERENCING_SHEET]
        refviewport = v.Parameter[DB.BuiltInParameter.VIEW_REFERENCING_DETAIL]
        refprefix = VIEWREF_PREFIX.get(v.ViewType, '')
        if refsheet \
                and refviewport \
                and refsheet.AsString() != '' \
                and refviewport.AsString() != '' \
                or (refprefix + revit.query.get_name(v)) in view_refs_names:
            return True

    def confirm_removal(v):
        if isinstance(v, viewclass_to_purge):
            if viewtype_to_purge and v.ViewType != viewtype_to_purge:
                return False
            elif v.ViewType in READONLY_VIEWS:
                return False
            elif v.IsTemplate:
                return False
            elif DB.ViewType.ThreeD == v.ViewType \
                    and '{3D}' == revit.query.get_name(v):
                return False
            elif '<' in revit.query.get_name(v):
                return False
            elif v.Id.IntegerValue in open_views:
                return False
            elif keep_referenced and is_referenced(v):
                return False
            else:
                return True
        else:
            return False

    print_header(header)
    remove_action(action_title,
                  action_cat,
                  views,
                  validity_func=confirm_removal)


@dependent
def remove_all_views():
    """Remove All Views (of any kind, except open views and sheets)"""

    # (View3D, ViewPlan, ViewDrafting, ViewSection, ViewSchedule)
    _purge_all_views(DB.View, None,
                     'REMOVING DRAFTING, PLAN, SECTION, AND ELEVATION VIEWS',
                     'Remove All Views', 'View')


@dependent
def remove_all_unreferenced_views():
    """Remove All Unreferenced Views (of any kind, except open views and sheets)"""

    # (View3D, ViewPlan, ViewDrafting, ViewSection, ViewSchedule)
    _purge_all_views(DB.View, None,
                     'REMOVING UNREFERENCED RAFTING, PLAN, '
                     'SECTION, AND ELEVATION VIEWS',
                     'Remove All Unreferenced Views', 'View',
                     keep_referenced=True)


@dependent
def remove_all_plans():
    """Remove All Views (Floor Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.FloorPlan,
                     'REMOVING PLAN VIEWS',
                     'Remove All Plan Views', 'Plan View')


@dependent
def remove_all_unreferenced_plans():
    """Remove All Unreferenced Views (Floor Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.FloorPlan,
                     'REMOVING UNREFERENCED PLAN VIEWS',
                     'Remove All Unreferenced Plan Views', 'Plan View',
                     keep_referenced=True)


@dependent
def remove_all_rcps():
    """Remove All Views (Reflected Ceiling Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.CeilingPlan,
                     'REMOVING RCP VIEWS',
                     'Remove All Reflected Ceiling Plans', 'Ceiling View')


@dependent
def remove_all_unreferenced_rcps():
    """Remove All Unreferenced Views (Reflected Ceiling Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.CeilingPlan,
                     'REMOVING UNREFERENCED RCP VIEWS',
                     'Remove All Unreferenced Reflected Ceiling Plans',
                     'Ceiling View',
                     keep_referenced=True)


@dependent
def remove_all_engplan():
    """Remove All Views (Engineering Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.EngineeringPlan,
                     'REMOVING ENGINEERING VIEWS',
                     'Remove All Engineering Plans', 'Engineering View')


@dependent
def remove_all_unreferenced_engplan():
    """Remove All Unreferenced Views (Engineering Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.EngineeringPlan,
                     'REMOVING UNREFERENCED ENGINEERING VIEWS',
                     'Remove All Unreferenced Engineering Plans',
                     'Engineering View',
                     keep_referenced=True)


@dependent
def remove_all_areaplans():
    """Remove All Views (Area Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.AreaPlan,
                     'REMOVING AREA VIEWS',
                     'Remove All Area Plans', 'Area View')


@dependent
def remove_all_unreferenced_areaplans():
    """Remove All Unreferenced Views (Area Plans only)"""

    _purge_all_views(DB.ViewPlan, DB.ViewType.AreaPlan,
                     'REMOVING UNREFERENCED AREA VIEWS',
                     'Remove All Unreferenced Area Plans', 'Area View',
                     keep_referenced=True)


@dependent
def remove_all_threed():
    """Remove All Views (3D Views only)"""

    _purge_all_views(DB.View3D, DB.ViewType.ThreeD,
                     'REMOVING 3D VIEWS',
                     'Remove All 3D Views', '3D View')


@dependent
def remove_all_unreferenced_threed():
    """Remove All Unreferenced Views (3D Views only)"""

    _purge_all_views(DB.View3D, DB.ViewType.ThreeD,
                     'REMOVING UNREFERENCED 3D VIEWS',
                     'Remove All Unreferenced 3D Views', '3D View',
                     keep_referenced=True)


@dependent
def remove_all_drafting():
    """Remove All Views (Drafting Views only)"""

    _purge_all_views(DB.ViewDrafting, None,
                     'REMOVING DRAFTING VIEWS',
                     'Remove All Drafting Views', 'Drafting View')


@dependent
def remove_all_unreferenced_drafting():
    """Remove All Unreferenced Views (Drafting Views only)"""

    _purge_all_views(DB.ViewDrafting, None,
                     'REMOVING UNREFERENCED DRAFTING VIEWS',
                     'Remove All Unreferenced Drafting Views',
                     'Drafting View',
                     keep_referenced=True)


@dependent
def remove_all_sections():
    """Remove All Views (Sections only)"""
    _purge_all_views(DB.ViewSection, DB.ViewType.Section,
                     'REMOVING SECTION VIEWS',
                     'Remove All Section Views', 'Section View')


@dependent
def remove_all_detailsection():
    """Remove All Views (Detail Views only)"""
    _purge_all_views(DB.ViewSection, DB.ViewType.Detail,
                     'REMOVING DETAIL VIEWS',
                     'Remove All Detail Views', 'Detail View')


@dependent
def remove_all_unreferenced_sections():
    """Remove All Unreferenced Views (Sections only)"""
    _purge_all_views(DB.ViewSection, DB.ViewType.Section,
                     'REMOVING UNREFERENCED SECTION VIEWS',
                     'Remove All Unreferenced Section Views', 'Section View',
                     keep_referenced=True)


@dependent
def remove_all_unreferenced_detailsection():
    """Remove All Unreferenced Views (Detail Views only)"""
    _purge_all_views(DB.ViewSection, DB.ViewType.Detail,
                     'REMOVING UNREFERENCED DETAIL VIEWS',
                     'Remove All Unreferenced Detail Views', 'Detail View',
                     keep_referenced=True)


@dependent
def remove_all_elevations():
    """Remove All Views (Elevations only)"""
    _purge_all_views(DB.ViewSection, DB.ViewType.Elevation,
                     'REMOVING SECTION VIEWS',
                     'Remove All Elevation Views', 'Elevation View')


@dependent
def remove_all_unreferenced_elevations():
    """Remove All Unreferenced Views (Elevations only)"""
    _purge_all_views(DB.ViewSection, DB.ViewType.Elevation,
                     'REMOVING UNREFERENCED SECTION VIEWS',
                     'Remove All Unreferenced Elevation Views', 'Elevation View',
                     keep_referenced=True)


@dependent
def remove_all_schedules():
    """Remove All Views (Schedules only)"""

    cl = DB.FilteredElementCollector(revit.doc)
    sched_views = set(cl.OfClass(DB.ViewSchedule)
                        .WhereElementIsNotElementType()
                        .ToElements())
    open_UIViews = revit.uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(v):
        if isinstance(v, DB.ViewSchedule):
            if v.ViewType in READONLY_VIEWS:
                return False
            elif v.IsTemplate:
                return False
            elif '<' in revit.query.get_name(v):
                return False
            elif v.Id.IntegerValue in open_views:
                return False
            elif v.Definition.CategoryId == \
                DB.Category.GetCategory(revit.doc,
                                        DB.BuiltInCategory.OST_KeynoteTags).Id:
                return False
            else:
                return True
        else:
            return False

    print_header('REMOVING SCHEDULES')
    remove_action('Remove All Schedules',
                  'Schedule',
                  sched_views,
                  validity_func=confirm_removal)


@dependent
def remove_all_legends():
    """Remove All Views (Legends only)"""

    cl = DB.FilteredElementCollector(revit.doc)
    legend_views = set(cl.OfClass(DB.View)
                         .WhereElementIsNotElementType()
                         .ToElements())

    open_UIViews = revit.uidoc.GetOpenUIViews()
    open_views = [ov.ViewId.IntegerValue for ov in open_UIViews]

    def confirm_removal(v):
        if isinstance(v, DB.View) and v.ViewType == DB.ViewType.Legend:
            if v.ViewType in READONLY_VIEWS:
                return False
            elif v.IsTemplate:
                return False
            elif '<' in revit.query.get_name(v):
                return False
            elif v.Id.IntegerValue in open_views:
                return False
            else:
                return True
        elif isinstance(v, DB.ViewSchedule) \
                and v.Definition.CategoryId == \
                DB.Category.GetCategory(revit.doc,
                                        DB.BuiltInCategory.OST_KeynoteTags).Id:
            return True
        else:
            return False

    print_header('REMOVING LEGENDS')
    remove_action('Remove All Legends',
                  'Legend',
                  legend_views,
                  validity_func=confirm_removal)


@notdependent
def remove_all_view_templates():
    """Remove All View Templates"""

    def confirm_removal(v):
        if isinstance(v, DB.View) \
                and v.IsTemplate \
                and v.ViewType not in READONLY_VIEWS:
            return True
        else:
            return False

    cl = DB.FilteredElementCollector(revit.doc)
    views = set(cl.OfClass(DB.View)
                  .WhereElementIsNotElementType()
                  .ToElements())

    print_header('REMOVING ALL VIEW TEMPLATES')
    remove_action('Remove All View Templates',
                  'View Templates',
                  views,
                  validity_func=confirm_removal)


@notdependent
def remove_all_elevation_markers():
    """Remove All Elevation Markers"""

    def confirm_removal(elev_marker):
        return elev_marker.CurrentViewCount == 0

    cl = DB.FilteredElementCollector(revit.doc)
    elev_markers = cl.OfClass(DB.ElevationMarker)\
                     .WhereElementIsNotElementType()\
                     .ToElements()

    print_header('REMOVING ELEVATION MARKERS')
    remove_action('Remove All Elevation Markers',
                  'Elevation Marker',
                  elev_markers,
                  validity_func=confirm_removal)


@notdependent
def remove_all_filters():
    """Remove All Filters"""

    cl = DB.FilteredElementCollector(revit.doc)
    filters = cl.OfClass(DB.FilterElement)\
                .WhereElementIsNotElementType()\
                .ToElements()

    print_header('REMOVING ALL FILTERS')
    remove_action('Remove All Filters', 'View Filter', filters)


@notdependent
def remove_all_model_patterns():
    """Remove All Patterns (Model)"""

    cl = DB.FilteredElementCollector(revit.doc)
    pattern_elements = cl.OfClass(DB.FillPatternElement)\
                         .WhereElementIsNotElementType()\
                         .ToElements()

    model_patterns = \
        [x for x in pattern_elements
         if x.GetFillPattern().Target == DB.FillPatternTarget.Model]

    print_header('REMOVING ALL MODEL PATTERNS')
    remove_action('Remove All Model Patterns',
                  'Model Pattern',
                  model_patterns)


@notdependent
def remove_all_drafting_patterns():
    """Remove All Patterns (Drafting)"""

    cl = DB.FilteredElementCollector(revit.doc)
    pattern_elements = cl.OfClass(DB.FillPatternElement)\
                         .WhereElementIsNotElementType()\
                         .ToElements()

    draft_patterns = \
        [x for x in pattern_elements
         if x.GetFillPattern().Target == DB.FillPatternTarget.Drafting]

    print_header('REMOVING ALL DRAFTING PATTERNS')
    remove_action('Remove All Drafting Patterns',
                  'Drafting Pattern',
                  draft_patterns)


# dynamically generate function that remove all elements on a workset,
# based on current model worksets
@notdependent
def template_workset_remover(workset_name=None):
    workset_list = DB.FilteredWorksetCollector(revit.doc)\
                     .OfKind(DB.WorksetKind.UserWorkset)
    workset_dict = {workset.Name: workset.Id for workset in workset_list}

    element_workset_filter = \
        DB.ElementWorksetFilter(workset_dict[workset_name], False)
    workset_elements = DB.FilteredElementCollector(revit.doc)\
                         .WherePasses(element_workset_filter)\
                         .ToElements()

    print_header('REMOVING ALL ELEMENTS ON WORKSET "{}"'.format(workset_name))
    remove_action('Remove All on WS: {}'.format(workset_name),
                  'Workset Element',
                  workset_elements)


WORKSET_FUNC_DOCSTRING_TEMPLATE = 'Remove All Elements on Workset "{}"'

WorksetFuncData = namedtuple('WorksetFuncData', ['func', 'docstring', 'args'])


def copy_func(f, workset_name):
    new_funcname = '{}_{}'.format(f.func_name, workset_name)
    new_func = \
        types.FunctionType(f.func_code,
                           f.func_globals,
                           new_funcname,
                           tuple([workset_name]),
                           f.func_closure)

    # set the docstring
    new_func.__doc__ = WORKSET_FUNC_DOCSTRING_TEMPLATE.format(workset_name)
    new_func.is_dependent = False
    return new_func


def get_worksetcleaners():
    workset_funcs = []
    # if model is workshared, get a list of current worksets
    if revit.doc.IsWorkshared:
        cl = DB.FilteredWorksetCollector(revit.doc)
        worksetlist = cl.OfKind(DB.WorksetKind.UserWorkset)
        # duplicate the workset element remover function for each workset
        for workset in worksetlist:
            # copying functions is not implemented in IronPython 2.7.3
            # this method initially used copy_func to create a func for
            # each workset but now passes on the template func
            # with appropriate arguments
            docstr = WORKSET_FUNC_DOCSTRING_TEMPLATE.format(workset.Name)
            workset_funcs.append(
                WorksetFuncData(
                    func=template_workset_remover,
                    docstring=docstr,
                    args=(workset.Name,)
                    )
                )

    return workset_funcs
