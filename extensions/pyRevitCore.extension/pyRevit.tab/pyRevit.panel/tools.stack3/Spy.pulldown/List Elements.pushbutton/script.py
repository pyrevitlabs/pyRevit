__doc__ = 'Lists specific elements from the model database.'

from pyrevit.framework import List
from pyrevit import revit, DB, UI
from pyrevit.forms import userinput


switches = ['Graphic Styles',
            'Grids',
            'Line Patterns',
            'Line Styles',
            'Selected Line Coordinates',
            'Model / Detail / Sketch Lines',
            'Project Parameters',
            'Data Schemas',
            'Data Schema Entities',
            'Sketch Planes',
            'Views',
            'View Templates',
            'Viewports',
            'Viewport Types',
            'Family Symbols',
            'Levels',
            'Scope Boxes',
            'Areas',
            'Rooms',
            'External References',
            'Revisions',
            'Revision Clouds',
            'Sheets',
            'System Categories',
            'System Postable Commands',
            'Worksets',
            ]

selected_switch = \
    userinput.CommandSwitchWindow(sorted(switches),
                                  'List elements of type:').pick_cmd_switch()


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
    c = revit.doc.Settings.Categories.get_Item(DB.BuiltInCategory.OST_Lines)
    subcats = c.SubCategories

    for lineStyle in subcats:
        print("STYLE NAME: {0} ID: {1}".format(lineStyle.Name.ljust(40),
                                               lineStyle.Id.ToString()))

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
    pm = revit.doc.ParameterBindings
    it = pm.ForwardIterator()
    it.Reset()
    while it.MoveNext():
        p = it.Key
        b = pm[p]
        if isinstance(b, DB.InstanceBinding):
            bind = 'Instance'
        elif isinstance(b, DB.TypeBinding):
            bind = 'Type'
        else:
            bind = 'Uknown'

        print('PARAM: {0:<10} UNIT: {1:<10} TYPE: {2:<10} '
              'GROUP: {3:<20} BINDING: {4}'
              '\nAPPLIED TO: {5}\n'.format(p.Name,
                                           str(p.UnitType),
                                           str(p.ParameterType),
                                           str(p.ParameterGroup),
                                           bind,
                                           [c.Name for c in b.Categories]))

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
                      revit.doc.GetElement(v.ViewId).ViewName))

elif selected_switch == 'Viewport Types':
    vps = []

    cl_views = DB.FilteredElementCollector(revit.doc)
    vptypes = cl_views.OfClass(DB.ElementType).ToElements()

    for tp in vptypes:
        wrapperd_tp = revit.ElementWrapper(tp)
        if tp.FamilyName == 'Viewport':
            print('ID: {1} TYPE: {0}'.format(wrapperd_tp.name,
                                             str(tp.Id).ljust(10)))

elif selected_switch == 'Family Symbols':
    cl = DB.FilteredElementCollector(revit.doc)
    eltype_list = cl.OfClass(DB.ElementType).ToElements()

    for et in eltype_list:
        wrapperd_et = revit.ElementWrapper(et)
        print(wrapperd_et.name, et.FamilyName)

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
        print('SCOPEBOX: {0}'.format(el.Name))

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
              .format(el.LookupParameter('Name').AsString().ljust(30),
                      el.LookupParameter('Number').AsString().ljust(10),
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
              .format(el.LookupParameter('Name').AsString().ljust(30),
                      el.LookupParameter('Number').AsString().ljust(20),
                      el.Id))

    print('\n\nTOTAL ROOMS FOUND: {0}'.format(len(roomlist)))

elif selected_switch == 'External References':
    location = revit.doc.PathName
    try:
        modelPath = DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
        transData = DB.TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        for refId in externalReferences:
            extRef = transData.GetLastSavedReferenceData(refId)
            refpath = extRef.GetPath()
            path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(refpath)
            if '' == path:
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
        print('{0}\t'
              'REV#: {1}'
              'DATE: {2}'
              'TYPE:{3}'
              'DESC: {4}'
              .format(rev.SequenceNumber,
                      str(rev.RevisionNumber).ljust(5),
                      str(rev.RevisionDate).ljust(10),
                      str(rev.NumberType.ToString()).ljust(15),
                      str(rev.Description).replace('\n', '').replace('\r', '')
                      )
              )

elif selected_switch == 'Sheets':
    cl_sheets = DB.FilteredElementCollector(revit.doc)
    sheetsnotsorted = cl_sheets.OfCategory(DB.BuiltInCategory.OST_Sheets)\
                               .WhereElementIsNotElementType().ToElements()
    sheets = sorted(sheetsnotsorted, key=lambda x: x.SheetNumber)

    for s in sheets:
        print('NUMBER: {0}   '
              'NAME:{1}'
              .format(s.LookupParameter('Sheet Number').AsString().rjust(10),
                      s.LookupParameter('Sheet Name').AsString().ljust(50)))

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
    element_ids = revit.uidoc.Selection.GetElementIds()
    selection = [revit.doc.GetElement(elId) for elId in element_ids]

    views = []

    if len(selection) == 0:
        cl_views = DB.FilteredElementCollector(revit.doc)
        views = cl_views.OfCategory(DB.BuiltInCategory.OST_Views)\
                        .WhereElementIsNotElementType().ToElements()
    else:
        for sel in selection:
            if isinstance(sel, DB.View):
                views.append(sel)

    for v in views:
        phasep = v.LookupParameter('Phase')
        underlayp = v.LookupParameter('Underlay')
        print('TYPE: {1}'
              'ID: {2}'
              'TEMPLATE: {3}'
              'PHASE:{4} '
              'UNDERLAY:{5}  '
              '{0}'
              .format(v.ViewName,
                      str(v.ViewType).ljust(20),
                      str(v.Id).ljust(10),
                      str(v.IsTemplate).ljust(10),
                      phasep.AsValueString().ljust(25)
                      if phasep else '---'.ljust(25),
                      underlayp.AsValueString().ljust(25)
                      if underlayp else '---'.ljust(25)))

elif selected_switch == 'View Templates':
    cl_views = DB.FilteredElementCollector(revit.doc)
    views = cl_views.OfCategory(DB.BuiltInCategory.OST_Views)\
                    .WhereElementIsNotElementType().ToElements()

    for v in views:
        if v.IsTemplate:
            print('ID: {1}		{0}'.format(v.ViewName, str(v.Id).ljust(10)))

elif selected_switch == 'Worksets':
    cl = DB.FilteredWorksetCollector(revit.doc)
    worksetlist = cl.OfKind(DB.WorksetKind.UserWorkset)

    if revit.doc.IsWorkshared:
        for ws in worksetlist:
            print('WORKSET: {0} ID: {1}'.format(ws.Name.ljust(50), ws.Id))
    else:
        UI.TaskDialog.Show('pyRevit', 'Model is not workshared.')

elif selected_switch == 'Revision Clouds':
    cl = DB.FilteredElementCollector(revit.doc)
    revs = cl.OfCategory(DB.BuiltInCategory.OST_RevisionClouds)\
             .WhereElementIsNotElementType()

    for rev in revs:
        parent = revit.doc.GetElement(rev.OwnerViewId)
        revnum = revit.doc.GetElement(rev.RevisionId).RevisionNumber
        if isinstance(parent, DB.ViewSheet):
            print('REV#: {0}\t\t'
                  'ID: {3}\t\t'
                  'ON SHEET: {1} {2}'
                  .format(revnum,
                          parent.SheetNumber,
                          parent.Name,
                          rev.Id))
        else:
            print('REV#: {0}\t\t'
                  'ID: {2}\t\t'
                  'ON VIEW: {1}'
                  .format(revnum,
                          parent.ViewName,
                          rev.Id))

elif selected_switch == 'Selected Line Coordinates':
    def isline(line):
        if isinstance(line, DB.ModelArc)\
                or isinstance(line, DB.ModelLine) \
                or isinstance(line, DB.DetailArc) \
                or isinstance(line, DB.DetailLine):
            return True
        return False


    for elId in revit.uidoc.Selection.GetElementIds():
        el = revit.doc.GetElement(elId)
        if isline(el):
            print('Line ID: {0}'.format(el.Id))
            print('Start:\t {0}'.format(el.GeometryCurve.GetEndPoint(0)))
            print('End:\t {0}\n'.format(el.GeometryCurve.GetEndPoint(1)))
        else:
            print('Elemend with ID: {0} is a not a line.\n'.format(el.Id))

elif selected_switch == 'Data Schema Entities':
    allElements = \
        list(DB.FilteredElementCollector(revit.doc)
               .WherePasses(
                   DB.LogicalOrFilter(DB.ElementIsElementTypeFilter(False),
                                      DB.ElementIsElementTypeFilter(True))
            )
        )

    guids = {sc.GUID.ToString(): sc.SchemaName
             for sc in DB.ExtensibleStorage.Schema.ListSchemas()}

    for el in allElements:
        schemaGUIDs = el.GetEntitySchemaGuids()
        for guid in schemaGUIDs:
            if guid.ToString() in guids.keys():
                print('ELEMENT ID: {0}\t\t'
                      'SCHEMA NAME: {1}'
                      .format(el.Id.IntegerValue,
                              guids[guid.ToString()]))

    print('Iteration completed over {0} elements.'.format(len(allElements)))
