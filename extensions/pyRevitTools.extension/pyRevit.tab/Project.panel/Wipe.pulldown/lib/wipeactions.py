import clr
from scriptutils import this_script, logger
from revitutils import doc, uidoc

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


def print_info(message):
    logger.debug(message)


def print_error(el_type='', el_id=0, delete_err=None):
    err_msg = str(delete_err).replace('\n', ' ').replace('\r', '')
    logger.error('Error Removing Element with Id: {} Type: {} | {}'.format(el_type, el_id, err_msg))


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
    t = Transaction(doc, 'Remove All Constraints')
    t.Start()
    print_header('REMOVING ALL CONSTRAINTS')
    cl = FilteredElementCollector(doc)
    clconst = list(cl.OfCategory(BuiltInCategory.OST_Constraints).WhereElementIsNotElementType())
    for cnst in clconst:
        if cnst.View is not None:
            try:
                doc.Delete(cnst.Id)
            except Exception as e:
                print_error('Constraint', cnst.Id, e)
                continue
    t.Commit()


@notdependent
def remove_all_groups():
    """Remove (and Explode) All Groups"""
    t = Transaction(doc, 'Remove All Groups')
    t.Start()
    grpTypes = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(GroupType)).ToElementIds())
    groups = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(Group)).ToElements())

    print_header('EXPLODING GROUPS')
    # ungroup all groups
    for grp in groups:
        grp.UngroupMembers()

    print_header('REMOVING GROUPS')
    # delete group types
    for gtid in grpTypes:
        gtype = doc.GetElement(gtid)
        if gtype:
            if gtype.Category.Name != 'Attached Detail Groups':
                try:
                    doc.Delete(gtid)
                except Exception as e:
                    print_error('Group Type', None, e)
                    continue
    t.Commit()


@notdependent
def remove_all_external_links():
    """Remove All External Links"""
    t = Transaction(doc, 'Remove All External Links')
    t.Start()
    print_header('REMOVE ALL EXTERNAL LINKS')
    if doc.PathName:
        modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(doc.PathName)
        transData = TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        cl = FilteredElementCollector(doc)
        impInstances = list(cl.OfClass(clr.GetClrType(ImportInstance)).ToElements())
        imported = []
        for refId in externalReferences:
            try:
                lnk = doc.GetElement(refId)
                if isinstance(lnk, RevitLinkType) or isinstance(lnk, CADLinkType):
                    doc.Delete(refId)
            except Exception as e:
                print_error('External Link', refId, e)
                continue
    else:
        print_error('Model must be saved for external links to be removed.')
    t.Commit()


@notdependent
def remove_all_sheets():
    """Remove All Sheets"""
    t = Transaction(doc, 'Remove All Sheets')
    t.Start()
    print_header('REMOVING SHEETS')
    cl = FilteredElementCollector(doc)
    sheets = cl.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
    openUIViews = uidoc.GetOpenUIViews()
    openViews = [x.ViewId.IntegerValue for x in openUIViews]
    for s in sheets:
        if s.Id.IntegerValue in openViews:
            continue
        else:
            try:
                print_info('{2}{0}  {1}'.format(s.LookupParameter('Sheet Number').AsString().rjust(10),
                                            s.LookupParameter('Sheet Name').AsString().ljust(50), s.Id))
                doc.Delete(s.Id)
            except Exception as e:
                print_error('Sheet', s.Id, e)
                continue
    t.Commit()


@dependent
def remove_all_rooms():
    """Remove All Rooms"""
    t = Transaction(doc, 'Remove All Rooms')
    t.Start()
    print_header('REMOVING ROOMS')
    cl = FilteredElementCollector(doc)
    rooms = cl.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
    for r in rooms:
        try:
            print_info('{2}{1}{0}'.format(
                r.LookupParameter('Name').AsString().ljust(30),
                r.LookupParameter('Number').AsString().ljust(20),
                r.Id
            ))
            doc.Delete(r.Id)
        except Exception as e:
            print_error('Room', r.Id, e)
            continue
    t.Commit()


@dependent
def remove_all_areas():
    """Remove All Areas"""
    t = Transaction(doc, 'Remove All Areas')
    t.Start()
    print_header('REMOVING AREAS')
    cl = FilteredElementCollector(doc)
    areas = cl.OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElements()
    for a in areas:
        try:
            print_info('{2}{1}{0}'.format(
                a.ParametersMap['Name'].AsString().ljust(30),
                a.ParametersMap['Number'].AsString().ljust(10),
                a.Id))
            doc.Delete(a.Id)
        except Exception as e:
            print_error('Area', a.Id, e)
            continue
    t.Commit()


@notdependent
def remove_all_room_separation_lines():
    """Remove All Room Separation Lines"""
    t = Transaction(doc, 'Remove All Room Separation Lines')
    t.Start()
    print_header('REMOVING ROOM SEPARATIONS LINES')
    cl = FilteredElementCollector(doc)
    rslines = cl.OfCategory(BuiltInCategory.OST_RoomSeparationLines).WhereElementIsNotElementType().ToElements()
    for line in rslines:
        try:
            # print_info('ID: {0}'.format( line.Id ))
            doc.Delete(line.Id)
        except Exception as e:
            print_error('Room Separation Line', line.Id, e)
            continue
    t.Commit()


@notdependent
def remove_all_area_separation_lines():
    """Remove All Area Separation Lines"""
    t = Transaction(doc, 'Remove All Area Separation Lines')
    t.Start()
    print_header('REMOVING AREA SEPARATIONS LINES')
    cl = FilteredElementCollector(doc)
    aslines = cl.OfCategory(BuiltInCategory.OST_AreaSchemeLines).WhereElementIsNotElementType().ToElements()
    for line in aslines:
        try:
            doc.Delete(line.Id)
        except Exception as e:
            print_error('Area Separation Line', line.Id, e)
            continue
    t.Commit()


@notdependent
def remove_all_scope_boxes():
    """Remove All Scope Boxes"""
    t = Transaction(doc, 'Remove All ScopeBoxes')
    t.Start()
    print_header('REMOVING SCOPE BOXES')
    cl = FilteredElementCollector(doc)
    scopeboxes = cl.OfCategory(BuiltInCategory.OST_VolumeOfInterest).WhereElementIsNotElementType().ToElements()
    for s in scopeboxes:
        try:
            print_info('ID: {0}'.format(s.Id))
            doc.Delete(s.Id)
        except Exception as e:
            print_error('Scope Box', s.Id)
            continue
    t.Commit()


@notdependent
def remove_all_reference_planes():
    """Remove All Reference Planes"""
    t = Transaction(doc, 'Remove All Reference Planes')
    t.Start()
    print_header('REMOVING REFERENCE PLANES')
    cl = FilteredElementCollector(doc)
    refplanes = cl.OfCategory(BuiltInCategory.OST_CLines).WhereElementIsNotElementType().ToElements()
    for s in refplanes:
        try:
            print_info('ID: {0}'.format(s.Id))
            doc.Delete(s.Id)
        except Exception as e:
            print_error('Reference Plane', s.Id)
            continue
    t.Commit()


@notdependent
def remove_all_materials():
    """Remove All Materials"""
    t = Transaction(doc, 'Remove All Materials')
    t.Start()
    print_header('REMOVING MATERIALS')
    cl = FilteredElementCollector(doc)
    mats = cl.OfCategory(BuiltInCategory.OST_Materials).WhereElementIsNotElementType().ToElements()
    for m in mats:
        if 'poche' in m.Name.lower():
            continue
        try:
            doc.Delete(m.Id)
        except Exception as e:
            print_error('Material', m.Id, e)
            continue
    t.Commit()


@notdependent
def remove_all_views():
    """Remove All Views"""
    t = Transaction(doc, 'Remove All Views')
    t.Start()
    print_header('REMOVING VIEWS / LEGENDS / SCHEDULES')
    cl = FilteredElementCollector(doc)
    views = set(cl.OfClass(View).WhereElementIsNotElementType().ToElementIds())
    openUIViews = uidoc.GetOpenUIViews()
    openViews = [x.ViewId.IntegerValue for x in openUIViews]
    for vid in views:
        v = doc.GetElement(vid)
        if isinstance(v, View):
            if v.ViewType in [ViewType.ProjectBrowser,
                              ViewType.SystemBrowser,
                              ViewType.Undefined,
                              ViewType.DrawingSheet,
                              ViewType.Internal,
                              ]:
                continue
            elif ViewType.ThreeD == v.ViewType and '{3D}' == v.ViewName:
                continue
            elif '<' in v.ViewName or v.IsTemplate:
                continue
            elif vid.IntegerValue in openViews:
                continue
            else:
                print_info('{2}{1}{0}'.format(v.ViewName.ljust(50), str(v.ViewType).ljust(15), str(v.Id).ljust(10)))
                try:
                    doc.Delete(v.Id)
                except Exception as e:
                    print_error('View', v.Id, e)
                    continue
    t.Commit()


@notdependent
def remove_all_view_templates():
    """Remove All View Templates"""
    t = Transaction(doc, 'Remove All View Templates')
    t.Start()
    print_header('REMOVING VIEW TEMPLATES')
    cl = FilteredElementCollector(doc)
    views = set(cl.OfClass(View).WhereElementIsNotElementType().ToElementIds())
    for vid in views:
        v = doc.GetElement(vid)
        if isinstance(v, View):
            if v.ViewType in [ViewType.ProjectBrowser,
                              ViewType.SystemBrowser,
                              ViewType.Undefined,
                              ViewType.DrawingSheet,
                              ViewType.Internal,
                              ]:
                continue
            elif v.IsTemplate:
                print_info('{2}{1}{0}'.format(v.ViewName.ljust(50), str(v.ViewType).ljust(15), str(v.Id).ljust(10)))
                try:
                    doc.Delete(v.Id)
                except Exception as e:
                    print_error('View Template', v.Id, e)
                    continue
    t.Commit()


@notdependent
def remove_all_elevation_markers():
    """Remove All Elevation Markers"""
    t = Transaction(doc, 'Remove All Elevation Markers')
    t.Start()
    print_header('REMOVING ELEVATION MARKERS')
    cl = FilteredElementCollector(doc)
    elevMarkers = cl.OfClass(ElevationMarker).WhereElementIsNotElementType().ToElements()
    for em in elevMarkers:
        try:
            if em.CurrentViewCount == 0:
                doc.Delete(em.Id)
        except Exception as e:
            print_error('Elevation Marker', em.Id, e)
            continue
    t.Commit()


@notdependent
def remove_all_filters():
    """Remove All Filters"""
    t = Transaction(doc, 'Remove All Filters')
    t.Start()
    print_header('REMOVING ALL FILTERS')
    cl = FilteredElementCollector(doc)
    filters = cl.OfClass(FilterElement).WhereElementIsNotElementType().ToElements()
    for f in filters:
        try:
            print_info('ID: {0}'.format(f.Id))
            doc.Delete(f.Id)
        except Exception as e:
            print_error('View Filter', f.Id, e)
            continue
    t.Commit()
