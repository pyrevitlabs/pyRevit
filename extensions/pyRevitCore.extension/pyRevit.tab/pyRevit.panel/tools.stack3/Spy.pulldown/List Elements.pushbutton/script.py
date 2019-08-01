"""Lists specific elements from the model database."""
#pylint: disable=C0103,E0401,W0703
from collections import defaultdict

from pyrevit import HOST_APP
from pyrevit.framework import List
from pyrevit import coreutils
from pyrevit import revit, DB, UI
from pyrevit import forms
from pyrevit import script


output = script.get_output()

switches = ['Graphic Styles',
            'Grids',
            'Line Patterns',
            'Line Styles',
            'Selected Line Coordinates',
            'Model / Detail / Sketch Lines',
            'Project Parameters',
            'Unused Shared Parameters',
            'Data Schemas',
            'Data Schema Entities',
            'Sketch Planes',
            'Views',
            'View Templates',
            'Viewports',
            'Element Types',
            'Family Symbols',
            'Levels',
            'Scope Boxes',
            'Areas',
            'Rooms',
            'External References',
            'Revisions',
            'Revision Clouds',
            'Sheets',
            'Sheets with Hidden Characters',
            'System Categories',
            'System Postable Commands',
            'Worksets',
            'Fill Grids',
            'Connected Circuits',
            'Point Cloud Instances',
            'External Services',
            'Builtin Categories with No DB.Category',
            ]

selected_switch = \
    forms.CommandSwitchWindow.show(sorted(switches),
                                   message='List elements of type:')


if selected_switch == 'Graphic Styles':
    cl = DB.FilteredElementCollector(revit.doc)
    gstyles = [i for i in cl.OfClass(DB.GraphicsStyle).ToElements()]

    for gs in gstyles:
        if gs.GraphicsStyleCategory.Parent:
            parent = gs.GraphicsStyleCategory.Parent.Name
        else:
            parent = '---'
        if gs.GraphicsStyleCategory.GetHashCode() > 0:
            print('NAME: {0} CATEGORY:{2} PARENT: {3} ID: {1}'
                  .format(gs.Name.ljust(50),
                          gs.Id,
                          gs.GraphicsStyleCategory.Name.ljust(50),
                          parent.ljust(50)))

elif selected_switch == 'Grids':
    cl = DB.FilteredElementCollector(revit.doc)
    grid_list = cl.OfCategory(DB.BuiltInCategory.OST_Grids)\
                  .WhereElementIsNotElementType().ToElements()

    for el in grid_list:
        print('GRID: {0} ID: {1}'.format(el.Name,
                                         el.Id))

elif selected_switch == 'Line Patterns':
    cl = DB.FilteredElementCollector(revit.doc).OfClass(DB.LinePatternElement)
    for i in cl:
        print(i.Name)

elif selected_switch == 'Line Styles':
    for lineStyle in revit.query.get_line_styles(doc=revit.doc):
        print("STYLE NAME: {} ID: {} ({})".format(
            lineStyle.Name.ljust(40),
            lineStyle.Id.ToString(),
            lineStyle))

elif selected_switch == 'Model / Detail / Sketch Lines':
    cat_list = List[DB.BuiltInCategory]([DB.BuiltInCategory.OST_Lines,
                                         DB.BuiltInCategory.OST_SketchLines])
    elfilter = DB.ElementMulticategoryFilter(cat_list)
    cl = DB.FilteredElementCollector(revit.doc)
    cllines = cl.WherePasses(elfilter)\
                .WhereElementIsNotElementType().ToElements()

    for c in cllines:
        print('{0:<10} {1:<25}{2:<8} {3:<15} {4:<20}'
              .format(c.Id,
                      c.GetType().Name,
                      c.LineStyle.Id,
                      c.LineStyle.Name,
                      c.Category.Name))

elif selected_switch == 'Project Parameters':
    output.print_md('## Project Parameters')
    for pp in revit.query.get_project_parameters():
        if not pp.shared:
            output.print_md('#### {}'.format(pp.name))
            print('\tUNIT: {}\n\tTYPE: {}\n\tGROUP: {}'
                  '\n\tBINDING: {}\n\tAPPLIED TO: {}\n'.format(
                      pp.unit_type,
                      pp.param_type,
                      pp.param_group,
                      pp.param_binding_type,
                      [x.Name for x in pp.param_binding.Categories]
                      ))

    output.print_md('# Shared Parameters')
    for pp in revit.query.get_project_parameters():
        if pp.shared:
            output.print_md('#### {} : {}'.format(pp.name, pp.param_guid))
            print('\tUNIT: {}\n\tTYPE: {}\n\tGROUP: {}'
                  '\n\tBINDING: {}\n\tAPPLIED TO: {}\n'.format(
                      pp.unit_type,
                      pp.param_type,
                      pp.param_group,
                      pp.param_binding_type,
                      [x.Name for x in pp.param_binding.Categories]
                      ))

elif selected_switch == 'Unused Shared Parameters':
    shared_params = \
        set([x.Name + ':' + x.GUID.ToString()
             for x in revit.query.get_defined_sharedparams()])
    project_params = \
        set([x.name + ':' + x.param_guid
             for x in revit.query.get_project_parameters() if x.shared])
    for unused_shared_param in shared_params - project_params:
        print(unused_shared_param)

elif selected_switch == 'Data Schemas':
    for sc in DB.ExtensibleStorage.Schema.ListSchemas():
        print('\n' + '-' * 100)
        print('SCHEMA NAME: {0}'
              '\tGUID:               {6}\n'
              '\tDOCUMENTATION:      {1}\n'
              '\tVENDOR ID:          {2}\n'
              '\tAPPLICATION GUID:   {3}\n'
              '\tREAD ACCESS LEVEL:  {4}\n'
              '\tWRITE ACCESS LEVEL: {5}'.format(sc.SchemaName,
                                                 sc.Documentation,
                                                 sc.VendorId,
                                                 sc.ApplicationGUID,
                                                 sc.ReadAccessLevel,
                                                 sc.WriteAccessLevel,
                                                 sc.GUID))
        if sc.ReadAccessGranted():
            for fl in sc.ListFields():
                print('\t\tFIELD NAME: {0}\n'
                      '\t\t\tDOCUMENTATION:      {1}\n'
                      '\t\t\tCONTAINER TYPE:     {2}\n'
                      '\t\t\tKEY TYPE:           {3}\n'
                      '\t\t\tUNIT TYPE:          {4}\n'
                      '\t\t\tVALUE TYPE:         {5}\n'
                      .format(fl.FieldName,
                              fl.Documentation,
                              fl.ContainerType,
                              fl.KeyType,
                              fl.UnitType,
                              fl.ValueType))

elif selected_switch == 'Sketch Planes':
    cl = DB.FilteredElementCollector(revit.doc)
    skechplanelist = [i for i in cl.OfClass(DB.SketchPlane).ToElements()]

    for gs in skechplanelist:
        print('NAME: {0} ID: {1}'.format(gs.Name.ljust(50), gs.Id))

elif selected_switch == 'Viewports':
    vps = DB.FilteredElementCollector(revit.doc)\
          .OfCategory(DB.BuiltInCategory.OST_Viewports)\
          .WhereElementIsNotElementType().ToElements()

    for v in vps:
        print('ID: {1}TYPE: {0}VIEWNAME: {2}'
              .format(v.Name.ljust(30),
                      str(v.Id).ljust(10),
                      revit.query.get_name(revit.doc.GetElement(v.ViewId))))

elif selected_switch == 'Element Types':
    all_types = \
        revit.query.get_types_by_class(DB.ElementType, doc=revit.doc)
    etypes_dict = defaultdict(list)
    for etype in all_types:
        if etype.FamilyName:
            etypes_dict[str(etype.FamilyName).strip()].append(etype)

    for etype_name in sorted(etypes_dict.keys()):
        etypes = etypes_dict[etype_name]
        output.print_md('**{}**'.format(etype_name))
        for et in etypes:
            print('\t{} {}'.format(output.linkify(et.Id),
                                   revit.query.get_name(et)))

elif selected_switch == 'Family Symbols':
    cl = DB.FilteredElementCollector(revit.doc)
    eltype_list = cl.OfClass(DB.ElementType).ToElements()

    for et in eltype_list:
        print(revit.query.get_name(et), et.FamilyName)

elif selected_switch == 'Levels':
    levelslist = DB.FilteredElementCollector(revit.doc)\
                 .OfCategory(DB.BuiltInCategory.OST_Levels)\
                 .WhereElementIsNotElementType()

    for i in levelslist:
        print('Level ID:\t{1}\t'
              'ELEVATION:{2}\t\t'
              'Name:\t{0}'.format(i.Name,
                                  i.Id.IntegerValue,
                                  i.Elevation))

elif selected_switch == 'Scope Boxes':
    scopeboxes = DB.FilteredElementCollector(revit.doc)\
                 .OfCategory(DB.BuiltInCategory.OST_VolumeOfInterest)\
                 .WhereElementIsNotElementType().ToElements()

    for el in scopeboxes:
        print('{} SCOPEBOX: {}'.format(output.linkify(el.Id), el.Name))

elif selected_switch == 'Areas':
    cl = DB.FilteredElementCollector(revit.doc)
    arealist = cl.OfCategory(DB.BuiltInCategory.OST_Areas)\
                 .WhereElementIsNotElementType().ToElements()

    for el in arealist:
        print('AREA NAME: {0} '
              'AREA NUMBER: {1} '
              'AREA ID: {2} '
              'LEVEL: {3} '
              'AREA: {4}'
              .format(el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString().ljust(30),
                      el.Parameter[DB.BuiltInParameter.ROOM_NUMBER].AsString().ljust(10),
                      el.Id,
                      str(el.Level.Name).ljust(50),
                      el.Area))

    print('\n\nTOTAL AREAS FOUND: {0}'.format(len(arealist)))

elif selected_switch == 'Rooms':
    cl = DB.FilteredElementCollector(revit.doc)
    roomlist = cl.OfCategory(DB.BuiltInCategory.OST_Rooms)\
                 .WhereElementIsNotElementType().ToElements()

    for el in roomlist:
        print('ROOM NAME: {0} '
              'ROOM NUMBER: {1} '
              'ROOM ID: {2}'
              .format(el.Parameter[DB.BuiltInParameter.ROOM_NAME].AsString().ljust(30),
                      el.Parameter[DB.BuiltInParameter.ROOM_NUMBER].AsString().ljust(20),
                      el.Id))

    print('\n\nTOTAL ROOMS FOUND: {0}'.format(len(roomlist)))

elif selected_switch == 'External References':
    location = revit.doc.PathName
    try:
        modelPath = \
            DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
        transData = DB.TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        for refId in externalReferences:
            extRef = transData.GetLastSavedReferenceData(refId)
            refpath = extRef.GetPath()
            path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(refpath)
            if not path:
                path = '--NOT ASSIGNED--'
            reftype = str(extRef.ExternalFileReferenceType) + ':'
            print("{0}{1}".format(reftype.ljust(20), path))
    except Exception:
        print('Model is not saved yet. Can not aquire location.')

elif selected_switch == 'Revisions':
    cl = DB.FilteredElementCollector(revit.doc)
    revs = cl.OfCategory(DB.BuiltInCategory.OST_Revisions)\
             .WhereElementIsNotElementType()

    for rev in revs:
        revit.report.print_revision(rev)

elif selected_switch == 'Sheets':
    cl_sheets = DB.FilteredElementCollector(revit.doc)
    sheetsnotsorted = cl_sheets.OfCategory(DB.BuiltInCategory.OST_Sheets)\
                               .WhereElementIsNotElementType().ToElements()
    sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

    for s in sheets:
        print('NUMBER: {0}   '
              'NAME:{1}'
              .format(s.Parameter[DB.BuiltInParameter.SHEET_NUMBER].AsString().rjust(10),
                      s.Parameter[DB.BuiltInParameter.SHEET_NAME].AsString().ljust(50)))

elif selected_switch == 'System Categories':
    for cat in revit.doc.Settings.Categories:
        print(cat.Name)

elif selected_switch == 'System Postable Commands':
    for pc in UI.PostableCommand.GetValues(UI.PostableCommand):
        try:
            rcid = UI.RevitCommandId.LookupPostableCommandId(pc)
            if rcid:
                print('{0} {1} {2}'.format(str(pc).ljust(50),
                                           str(rcid.Name).ljust(70),
                                           rcid.Id))
            else:
                print('{0}'.format(str(pc).ljust(50)))
        except Exception:
            print('{0}'.format(str(pc).ljust(50)))

elif selected_switch == 'Views':
    selection = revit.get_selection()

    views = []

    if selection:
        cl_views = DB.FilteredElementCollector(revit.doc)
        views = cl_views.OfCategory(DB.BuiltInCategory.OST_Views)\
                        .WhereElementIsNotElementType().ToElements()
    else:
        for el in selection:
            if isinstance(el, DB.View):
                views.append(el)

    for v in views:
        phasep = v.Parameter[DB.BuiltInParameter.VIEW_PHASE]
        if HOST_APP.is_older_than(2016):
            underlayp = v.Parameter[DB.BuiltInParameter.VIEW_UNDERLAY_ID]
            print('TYPE: {1} ID: {2} TEMPLATE: {3} PHASE:{4} UNDERLAY:{5} {0}'
                  .format(revit.query.get_name(v),
                          str(v.ViewType).ljust(20),
                          str(v.Id).ljust(10),
                          str(v.IsTemplate).ljust(10),
                          phasep.AsValueString().ljust(25)
                          if phasep else '---'.ljust(25),
                          underlayp.AsValueString().ljust(25)
                          if underlayp else '---'.ljust(25)))
        else:
            underlaytp = v.Parameter[DB.BuiltInParameter.VIEW_UNDERLAY_TOP_ID]
            underlaybp = \
                v.Parameter[DB.BuiltInParameter.VIEW_UNDERLAY_BOTTOM_ID]
            print('TYPE: {1} ID: {2} TEMPLATE: {3} PHASE:{4} '
                  'UNDERLAY TOP:{5} UNDERLAY BOTTOM:{6} {0}'
                  .format(revit.query.get_name(v),
                          str(v.ViewType).ljust(20),
                          str(v.Id).ljust(10),
                          str(v.IsTemplate).ljust(10),
                          phasep.AsValueString().ljust(25)
                          if phasep else '---'.ljust(25),
                          underlaytp.AsValueString().ljust(25)
                          if underlaytp else '---'.ljust(25),
                          underlaybp.AsValueString().ljust(25)
                          if underlaybp else '---'.ljust(25)))

elif selected_switch == 'View Templates':
    cl_views = DB.FilteredElementCollector(revit.doc)
    views = cl_views.OfCategory(DB.BuiltInCategory.OST_Views)\
                    .WhereElementIsNotElementType().ToElements()

    for v in views:
        if v.IsTemplate:
            print('ID: {1}		{0}'.format(revit.query.get_name(v),
                                            str(v.Id).ljust(10)))

elif selected_switch == 'Worksets':
    cl = DB.FilteredWorksetCollector(revit.doc)
    worksetlist = cl.OfKind(DB.WorksetKind.UserWorkset)

    if revit.doc.IsWorkshared:
        for ws in worksetlist:
            print('WORKSET: {0} ID: {1}'.format(ws.Name.ljust(50), ws.Id))
    else:
        forms.alert('Model is not workshared.')

elif selected_switch == 'Revision Clouds':
    cl = DB.FilteredElementCollector(revit.doc)
    revs = cl.OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
             .WhereElementIsNotElementType()

    for rev in revs:
        parent = revit.doc.GetElement(rev.OwnerViewId)
        rev = revit.doc.GetElement(rev.RevisionId)
        revnum = revit.query.get_param(rev, 'RevisionNumber', None)

        if revnum:
            revnumstr = 'REV#: {0}'.format(revnum)
        else:
            revnumstr = 'SEQ#: {0}'.format(rev.SequenceNumber)

        if isinstance(parent, DB.ViewSheet):
            print('{0}\t\t'
                  'ID: {3}\t\t'
                  'ON SHEET: {1} {2}'
                  .format(revnumstr,
                          parent.SheetNumber,
                          parent.Name,
                          rev.Id))
        else:
            print('{0}\t\t'
                  'ID: {2}\t\t'
                  'ON VIEW: {1}'
                  .format(revnumstr,
                          revit.query.get_name(parent),
                          rev.Id))

elif selected_switch == 'Selected Line Coordinates':
    def isline(line):
        if isinstance(line, DB.ModelArc)\
                or isinstance(line, DB.ModelLine) \
                or isinstance(line, DB.DetailArc) \
                or isinstance(line, DB.DetailLine):
            return True
        return False

    selection = revit.get_selection()

    for el in selection:
        if isline(el):
            print('Line ID: {0}'.format(el.Id))
            print('Start:\t {0}'.format(el.GeometryCurve.GetEndPoint(0)))
            print('End:\t {0}\n'.format(el.GeometryCurve.GetEndPoint(1)))
        else:
            print('Elemend with ID: {0} is a not a line.\n'.format(el.Id))

elif selected_switch == 'Data Schema Entities':
    schemas = {x.GUID.ToString(): x
               for x in revit.query.get_all_schemas()}

    for el in revit.query.get_all_elements(doc=revit.doc):
        schema_guids = el.GetEntitySchemaGuids()
        for guid_obj in schema_guids:
            guid = guid_obj.ToString()
            if guid in schemas:
                schema = schemas[guid]
                print(
                    '{}{}'.format(
                        '{} ({})'.format(
                            output.linkify(el.Id),
                            el.Category.Name if el.Category else "Unknown"
                            ).ljust(40),
                        schema.SchemaName
                        )
                    )
                for fname, fval in \
                    revit.query.get_schema_field_values(el, schema).items():
                    print('\t%s: %s' %(fname, fval))

elif selected_switch == 'Fill Grids':
    selection = revit.get_selection()
    for el in selection:
        if isinstance(el, DB.FilledRegion):
            frt = revit.doc.GetElement(el.GetTypeId())
            print('\n\n Filled Region Type: {}'
                  .format(revit.query.get_name(frt)))
            fre = revit.doc.GetElement(frt.FillPatternId)
            fp = fre.GetFillPattern()
            for fg in fp.GetFillGrids():
                print('FillGrid:')
                print('\tOrigin: {}'.format(fg.Origin))
                print('\tAngle: {}'.format(fg.Angle))
                print('\tOffset: {}'.format(fg.Offset))
                print('\tShift: {}'.format(fg.Shift))
                for seg in fg.GetSegments():
                    print('\tSegment: {}'.format(seg))

elif selected_switch == 'Connected Circuits':
    selection = revit.get_selection()
    for el in selection:
        esystems = revit.query.get_connected_circuits(el)
        for esys in esystems:
            print(esys.Name)

elif selected_switch == 'Point Cloud Instances':
    for pc in revit.query.get_pointclouds(doc=revit.doc):
        ws = revit.doc.GetElement(pc.WorksetId)
        print('Name: {}\tWorkset:{}'.format(pc.Name, ws.Name if ws else '---'))

elif selected_switch == 'Sheets with Hidden Characters':
    for sheet in revit.query.get_sheets(doc=revit.doc):
        sheetnum = sheet.SheetNumber
        sheetnum_repr = repr(str(sheet.SheetNumber).encode("utf-8"))
        if coreutils.has_nonprintable(sheetnum):
            output.print_md('**{}**: Unicode: {}  Bytes: {}'
                            .format(sheet.SheetNumber,
                                    repr(sheetnum),
                                    sheetnum_repr))

elif selected_switch == 'External Services':
    BExtSer = DB.ExternalService.ExternalServices.BuiltInExternalServices
    props = [x for x in dir(BExtSer) if 'Service' in x]
    bisrvids = {x: getattr(BExtSer, x).Guid for x in props}
    output.print_md('## Builtin Services')
    for bisrv, bisrvid in bisrvids.items():
        print('{} | {}'.format(bisrvid, bisrv))

    output.print_md('## Registered External Services')
    for esvc in DB.ExternalService.ExternalServiceRegistry.GetServices():
        output.insert_divider()
        output.print_md('{} | **{}**\n\n{} (by {}) (Builtin: {})'.format(
            esvc.ServiceId.Guid,
            esvc.Name,
            esvc.Description,
            esvc.VendorId,
            esvc.ServiceId.Guid in bisrvids))
        for sid in esvc.GetRegisteredServerIds():
            server = esvc.GetServer(sid)
            print('{} | {} ({}) (Builtin: {})'.format(
                sid,
                server.GetName(),
                server.GetDescription(),
                sid in bisrvids))

elif selected_switch == 'Builtin Categories with No DB.Category':
    for bic in coreutils.get_enum_values(DB.BuiltInCategory):
        dbcat = revit.query.get_category(bic)
        if not dbcat:
            print(bic)
