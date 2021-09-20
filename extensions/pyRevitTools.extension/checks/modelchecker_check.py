# -*- coding: UTF-8 -*-
#pylint: disable=import-error,invalid-name,broad-except,superfluous-parens
import datetime

from pyrevit import coreutils
from pyrevit import script
from pyrevit import revit, DB

from pyrevit.preflight import PreflightTestCase
from pyrevit.compat import safe_strtype


# webpage with explanations of bad practices in revit maybe it could be configurable in the future?
WIKI_ARTICLE = "https://www.modelical.com/en/gdocs/revit-arc-best-practices/"


# LISTS
# COLORS for chart.js graphs - chartCategories.randomize_colors() sometimes
# creates COLORS which are not distunguishable or visible
COLORS = 10 * [
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#000000",
    "#fff0f2",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#fff0e6",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#fff0e6",
    "#e97800",
    "#a6c844",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
    "#4d4d4d",
    "#fff0d9",
    "#ffc299",
    "#ff751a",
    "#cc5200",
    "#ff6666",
    "#ffd480",
    "#b33c00",
    "#ff884d",
    "#d9d9d9",
    "#9988bb",
    "#4d4d4d",
    "#e97800",
    "#a6c844",
]

# citical warnings Guids
CRITICAL_WARNINGS = [
    "6e1efefe-c8e0-483d-8482-150b9f1da21a",
    # 'Elements have duplicate "Number" values.',
    "6e1efefe-c8e0-483d-8482-150b9f1da21a",
    # 'Elements have duplicate "Type Mark" values.',
    "6e1efefe-c8e0-483d-8482-150b9f1da21a",
    # 'Elements have duplicate "Mark" values.',
    "b4176cef-6086-45a8-a066-c3fd424c9412",
    # 'There are identical instances in the same place',
    "4f0bba25-e17f-480a-a763-d97d184be18a",
    # 'Room Tag is outside of its Room',
    "505d84a1-67e4-4987-8287-21ad1792ffe9",
    # 'One element is completely inside another.',
    "8695a52f-2a88-4ca2-bedc-3676d5857af6",
    # 'Highlighted floors overlap.',
    "ce3275c6-1c51-402e-8de3-df3a3d566f5c",
    # 'Room is not in a properly enclosed region',
    "83d4a67c-818c-4291-adaf-f2d33064fea8",
    # 'Multiple Rooms are in the same enclosed region',
    "ce3275c6-1c51-402e-8de3-df3a3d566f5c",
    # 'Area is not in a properly enclosed region',
    "e4d98f16-24ac-4cbe-9d83-80245cf41f0a",
    # 'Multiple Areas are in the same enclosed region',
    "f657364a-e0b7-46aa-8c17-edd8e59683b9",
    # 'Room separation line is slightly off axis and may cause inaccuracies.''
]


def dashboardRectMaker(value, description, treshold):
    """dashboard HTMl maker - rectangle with large number"""
    content = str(value)
    # normal button
    if value <= treshold:
        html_code = (
            "<a class='dashboardLink' title='OK - maximum value "
            + str(int(treshold))
            + "'><p class='dashboardRectNormal'>"
            + content
            + "<br><span class='dashboardSmall'>"
            + description
            + "</span>"
            "</p></a>"
        )
        return coreutils.prepare_html_str(html_code)
    # mediocre button
    elif value < treshold * 2:
        html_code = (
            "<a class='dashboardLink' href='"
            + WIKI_ARTICLE
            + "' title='Mediocre - goal value "
            + str(int(treshold))
            + "'><p class='dashboardRectMediocre'>"
            + content
            + "<br><span class='dashboardSmall'>"
            + description
            + "</span>"
            "</p></a>"
        )
        return coreutils.prepare_html_str(html_code)
    # critical button
    else:
        html_code = (
            "<a class='dashboardLink' href='"
            + WIKI_ARTICLE
            + "' title='Critical - goal value "
            + str(int(treshold))
            + "'><p class='dashboardRectCritical'>"
            + content
            + "<br><span class='dashboardSmall'>"
            + description
            + "</span>"
            "</p></a>"
        )
        return coreutils.prepare_html_str(html_code)


def dashboardCenterMaker(value):
    """dashboard HTMl maker - div for center aligning"""
    content = str(value)
    html_code = "<div class='dashboardCenter'>" + content + "</div>"
    print(coreutils.prepare_html_str(html_code))

def dashboardLeftMaker(value):
    """dashboard HTMl maker - div for left aligning"""
    content = str(value)
    html_code = "<div class='dashboardLeft'>" + content + "</div>"
    print(coreutils.prepare_html_str(html_code))

def path2fileName(file_path, divider):
    """returns file name - everything in path from "\\" or "/" to the end"""
    lastDivider = file_path.rindex(divider) + 1
    file_name = file_path[lastDivider:]
    # print file_name
    return file_name


def checkModel(doc, output):
    """Check given model"""

    # printing file name and heading
    name = doc.PathName
    project_info_collector = doc.ProjectInformation
    projectNumber = project_info_collector.Number
    projectName = project_info_collector.Name
    projectClient = project_info_collector.ClientName
    if len(name) == 0:
        # name = "Not saved file"
        printedName = "Not saved file"
    else:
        try:
            central_path = revit.query.get_central_path(doc)
            try:
                # for rvt server
                printedName = path2fileName(central_path, "/")
            except:
                # other locations
                printedName = path2fileName(central_path, "\\")
        # non workshared file
        except:
            file_path = doc.PathName
            try:
                printedName = path2fileName(file_path, "\\")
            except:
                # detached file
                printedName = file_path
    output.print_md("# **MODEL CHECKER**")
    output.print_md("---")

    # first JS to avoid error in IE output window when at first run
    # this is most likely not proper way
    try:
        chartOuputError = output.make_doughnut_chart()
        chartOuputError.data.labels = []
        set_E = chartOuputError.data.new_dataset("Not Standard")
        set_E.data = []
        set_E.backgroundColor = ["#fff"]
        chartOuputError.set_height(1)
        chartOuputError.draw()
    except:
        pass

    ### Collectors ###

    ### RVTLinks collector
    # RVTLinks
    rvtlinks_id_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_RvtLinks)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    rvtlinkdocs = [i.GetLinkDocument() for i in DB.FilteredElementCollector(doc).OfClass(DB.RevitLinkInstance)]

    rvtlinkdocsName, rvtlink_instance_name =  [], []
    if len(rvtlinks_id_collector):
        for i in rvtlinks_id_collector:
            rvtlinkdocsName.append(revit.query.get_name(i).split(' : ')[0])
            rvtlink_instance_name.append(revit.query.get_name(i).split(' : ')[1])

        rvtlinksCount = len(rvtlinks_id_collector)
        # output.print_md(str(rvtlinksCount) +" Revit Links")

        # RVTLinks pinned

        rvtlinkspinnedCount, rvtlink_instance_pinned = [], []
        for x in rvtlinks_id_collector:
            rvtlinkspinnedCount.append(x.Pinned)
        for i in rvtlinkspinnedCount:
            if i==True:
                rvtlink_instance_pinned.append('Pinned')
            else:
                rvtlink_instance_pinned.append('UnPinned')
        rvtlinkspinnedCountTrue = sum(rvtlinkspinnedCount)
        # print(str(rvtlinkspinnedCountTrue) +" Revit Links pinned")
    else:
        pass

    ### View collectors
    
    # views
    views_id_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Views)
        .WhereElementIsNotElementType()
    )
    view_elements = views_id_collector.ToElements()
    viewCount = len(view_elements)

    copiedView = 0
    for view in view_elements:
        viewNameString = revit.query.get_name(view)
        try:
            if (
                viewNameString[-6:-2] == "Copy"
                or viewNameString[-4:] == "Copy"
                or viewNameString[:7] == "Section"
                # to support french files
                or viewNameString[-7:-2] == "Copie"
                or viewNameString[-5:] == "Copie"
                or viewNameString[-5:] == "Coupe"

            ):
                copiedView += 1
        except:
            pass

    # sheets
    sheets_id_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
        .ToElementIds()
    )
    sheetCount = len(sheets_id_collector)
    # print(str(sheetCount)+" Sheets")

    sheets_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Sheets)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    # views not on sheets
    viewsOnSheet = []
    # schedulesOnSheet = []
    for sheet in sheets_collector:
        try:
            # scheduleslist = list()
            for item in sheet.GetAllPlacedViews():
                if item not in viewsOnSheet:
                    viewsOnSheet.append(item)
        except:
            pass
    viewsNotOnSheet = viewCount - len(viewsOnSheet)

    # view Templates
    views = DB.FilteredElementCollector(doc).OfClass(DB.View)
    appliedTemplates = [v.ViewTemplateId for v in views]
    viewTemplates = [v for v in views if v.IsTemplate == True]
    unusedViewTemplates = []
    for v in viewTemplates:
        if v.Id not in appliedTemplates:
            unusedViewTemplates.append(v.Name)
    unusedViewTemplatesCount = (len(unusedViewTemplates))


    # schedules
    schedules_id_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Schedules)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    scheduleCount = 0
    ### scheduleNames = []
    for schedule in schedules_id_collector:
        if not(schedule.IsTitleblockRevisionSchedule):
            scheduleCount += 1
    ###        scheduleNames.append((schedule.Name))
    ### output.print_md("<br />".join(scheduleNames))

    # schedules not on sheets
    schedulesOnSheet = []
    ScheduleCollectorInstances = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ScheduleSheetInstance)
        .WhereElementIsNotElementType()
    )
    scheduleCollector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Schedules)
        .WhereElementIsNotElementType()
    )
    # there is need to iterate class and category filter to get all schedule
    # it is something with schedules on more sheets maybe...
    for schedule in scheduleCollector:
        schedName = schedule.Name
        if (schedName[:19] != "<Revision Schedule>"            
            # to support french files
            or schedName[:28] != "<Nomenclature des révisions>"):
            if schedName not in schedulesOnSheet:
                if schedule.OwnerViewId.IntegerValue != -1:
                    # print schedName
                    # print schedule.Id
                    schedulesOnSheet.append(schedName)

    # there is need to iterate class and category filter to get all schedule - UnionWith didn't work
    for schedule in ScheduleCollectorInstances:
        schedName = schedule.Name
        if (schedName[:19] != "<Revision Schedule>"            
            # to support french files
            or schedName[:28] != "<Nomenclature des révisions>"):
            if schedName not in schedulesOnSheet:
                if schedule.OwnerViewId.IntegerValue != -1:
                    # print schedName
                    # print schedule.Id
                    schedulesOnSheet.append(schedName)
    scheduleNotOnSheet = scheduleCount - len(schedulesOnSheet)

    # warnings
    allWarnings_collector = doc.GetWarnings()
    allWarningsCount = len(allWarnings_collector)
    # critical warnings
    criticalWarningCount = 0
    warnDescription, warnDescriptionHeadings = [], []
    for warning in allWarnings_collector:
        warningGuid = warning.GetFailureDefinitionId().Guid
        warnDescription.append(warning.GetDescriptionText())
        # if warning Guid is in the list
        if str(warningGuid) in CRITICAL_WARNINGS:
            criticalWarningCount += 1
    for i in warnDescription:
        if i not in warnDescriptionHeadings:
            warnDescriptionHeadings.append(i)
    warnDescriptionHeadings.sort()
    warnSet = []
    for i in warnDescriptionHeadings:
        count = warnDescription.count(i)
        warnSet.append(count)

    # materials
    materialCount = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Materials)
        .GetElementCount()
    )
    # print(str(materialCount)+" Materials")

    # line patterns
    linePatternCount = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.LinePatternElement)
        .GetElementCount()
    )
    # print(str(linePatternCount)+" Line Patterns")

    # DWGs
    dwg_collector = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ImportInstance)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    importedDwg = 0
    dwgNotCurrentView = 0
    for dwg in dwg_collector:
        if not dwg.IsLinked:
            importedDwg += 1
        if not dwg.ViewSpecific:
            dwgNotCurrentView += 1

    # dwgCount = dwg_collector.GetElementCount()
    dwgCount = len(dwg_collector)
    linkedDwg = dwgCount - importedDwg


    # families
    graphFCatHeadings = []
    graphFCatData = []
    families = DB.FilteredElementCollector(doc).OfClass(DB.Family)
    inPlaceFamilyCount = 0
    NotParamFamiliesCount = 0
    for family in families:
        if family.IsInPlace:
            inPlaceFamilyCount += 1
            # for graph
            inPlaceFCategory = family.FamilyCategory.Name
            if inPlaceFCategory not in graphFCatHeadings:
                graphFCatHeadings.append(inPlaceFCategory)
            graphFCatData.append(inPlaceFCategory)
        if not family.IsParametric:
            NotParamFamiliesCount += 1
    familyCount = families.GetElementCount()

    # Text notes width factor != 1
    textNoteType_collector = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.TextNoteType)
        .ToElements()
    )
    textnoteWFcount = 0
    for textnote in textNoteType_collector:
        widthFactor = textnote.get_Parameter(
            DB.BuiltInParameter.TEXT_WIDTH_SCALE
        ).AsDouble()
        if widthFactor != 1:
            textnoteWFcount += 1

    # Text notes with allCaps applied in Revit
    textNote_collector = (
        DB.FilteredElementCollector(doc).OfClass(DB.TextNote).ToElements()
    )
    capsCount = 0
    for textN in textNote_collector:
        capsStatus = textN.GetFormattedText().GetAllCapsStatus()
        if str(capsStatus) != "None":
            capsCount += 1

    # Ramps
    ramp_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Ramps)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )

    # Architecural columns
    archColumn_collector = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_Columns)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )

    # Analytical model activated elements
    activated_analytical_model_elements_count = 0

    param = DB.BuiltInParameter.STRUCTURAL_ANALYTICAL_MODEL
    provider = DB.ParameterValueProvider( DB.ElementId( param ) )
    evaluator = DB.FilterNumericEquals()
    rule = DB.FilterIntegerRule( provider, evaluator, 1 )
    filter = DB.ElementParameterFilter( rule )

    analyticalCollector = DB.FilteredElementCollector( doc ).WherePasses( filter ).ToElements()

    activated_analytical_model_elements_count = str(len(analyticalCollector))

    # detail groups
    detailGroupCount = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )
    detailGroupTypeCount = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSDetailGroups)
        .GetElementCount()
        - detailGroupCount
    )

    # model groups
    modelGroup = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .WhereElementIsNotElementType()   
    )
    modelGroupCount = 0
    for element in modelGroup:
        if element.GroupId and element.GroupId != DB.ElementId.InvalidElementId:
            modelGroupCount += 1

    modelGroupTypeCount = (
        DB.FilteredElementCollector(doc)
        .OfCategory(DB.BuiltInCategory.OST_IOSModelGroups)
        .WhereElementIsElementType()
        .GetElementCount()
    )

    # reference plane without name
    refPlaneCollector = (
        DB.FilteredElementCollector(doc)
        .OfClass(DB.ReferencePlane)
        .ToElements()
    )
    RefPCount = len(refPlaneCollector)
    noNameRefPCount = 0
    for refPlane in refPlaneCollector:
        if (refPlane.Name == "Reference Plane" or refPlane.Name == "Plan de référence"): # for french compatibility
            noNameRefPCount += 1

    # Element Count
    elementCount = (
        DB.FilteredElementCollector(doc)
        .WhereElementIsNotElementType()
        .GetElementCount()
    )

    def inner_lists(lst):
        if all(isinstance(x, list) for x in lst):
            return [x for inner in lst for x in inner_lists(inner)]
        else:
            return [lst]
    #Get list of phases in Doc and RVT Links
    #Get current document
    linkdocPhasesName = []

    def DocPhases(doc, links = []):
    	#Get document phases
    	docPhases = doc.Phases
    	#Get document phases names
    	docPhasesName = []
    	for i in docPhases:
    		docPhasesName.append(i.Name)
    	#Get links phases
        for x in links:
            linkdocPhases = []
            try:
                for y in x.Phases:
                    linkdocPhases.append(y.Name)
                linkdocPhasesName.append(linkdocPhases)
            except:
                linkdocPhasesName.append(['Link Unloaded'])
    	return docPhasesName, linkdocPhasesName

    #Call for phases definition
    phase = inner_lists(DocPhases(doc,rvtlinkdocs))

    ### tresholds ###
    # RVT links
    rvtlinksTres = 100
    rvtlinksPinnedTres =  -1 # The logic for threshold sometimes needs to be reverted

    if not len(rvtlinks_id_collector):
        pass
    else:
        if rvtlinksCount == rvtlinkspinnedCountTrue :
            rvtlinksPinnedTres = rvtlinksCount
        else :
            pass
    # Views
    viewTres = 500
    viewNotOnSheetTres = viewCount * 0.2
    copiedViewTres = viewCount * 0.2
    # View Templates
    viewTemplatesTres = 500
    unusedViewTemplateTres = len(viewTemplates) * 0.2
    # Sheets
    sheetsTres = 500
    # Schedules
    scheduleTres = 500
    schedulesNotOnSheetTres = scheduleCount * 0.3
    # Warnings
    warningsTres = 500
    criticalWarningsTres = 0
    # Materials
    materialsTres = 150
    # Line patterns
    linePatternsTres = 100
    # DWGs
    importedDwgTres = 0
    linkedDwgTres = viewCount / 2
    dwgNotCurrentViewTres = 0
    # Families
    familiesTres = 500
    if familyCount < 500:
        inPlaceFamilyTres = familyCount * 0.2
        genericModelTres = familyCount * 0.2
    else:
        inPlaceFamilyTres = familiesTres * 0.2
        genericModelTres = familiesTres * 0.2
    notParamFamiliesTres = familyCount * 0.3 
    #TextNotes
    textnoteWFtres = 0
    textnoteCaps = 0
     # Ramps
    rampTres = 0
    # Architectural columns
    archTres = 0
    # Analytical model activated elements
    activated_analytical_model_elements_count_tres = 0
    # Groups
    detailGroupTypeTres = 30
    detailGroupTres = 500
    modelGroupTypeTres = 30
    modelGroupTres = 200
    # Reference planes
    noNameRefPTres = 0
    RefPTres = 20
    # Elements count
    elementsTres = 1000000


    ### Dashaboard starts here ###

    ## RVT file dashboard section
    output.print_md("# RVT File<br />")
    projectInfo = "Current file name: "+ printedName + "<br />Project Name: " + projectName + "<br />Project Number: " + str(projectNumber) + "<br />Client Name: " + projectClient
    output.print_md(projectInfo)

    ## RVT Links dashboard section
    # print RVT links names
    output.print_md("---")
    output.print_md("# RVT Links")
    if not len(rvtlinks_id_collector):
        output.print_md("No links")
    else:
        rvtlinkdocsNameFormated, rvtlink_instance_name_formated = [], []
        for i, j in zip(rvtlinkdocsName, rvtlink_instance_name):
            rvtlinkdocsNameFormated.append(i)
            rvtlink_instance_name_formated.append(j)
        rvtlinks_data = zip(*[rvtlinkdocsNameFormated, rvtlink_instance_name_formated, rvtlink_instance_pinned])

        output.print_table(rvtlinks_data, columns=['Instance File Name', 'Instance Name', 'Pinned status'], formats=None, title='', last_line_style='')
        # Make row
        htmlRowRVTlinks = (
            dashboardRectMaker(rvtlinksCount, "RVTLinks", rvtlinksTres) + 
            dashboardRectMaker(rvtlinkspinnedCountTrue, "RVTLinks<br>pinned", rvtlinksPinnedTres)
        )
        dashboardLeftMaker(htmlRowRVTlinks)

    output.print_md("---")
    ## Views dashboard section
    # print Views section header
    output.print_md("# Views")

    # Make row
    htmlRowViews = (
        dashboardRectMaker(viewCount, "Views", viewTres)
        + dashboardRectMaker(
            copiedView, "Copied Views", copiedViewTres
        )
        + dashboardRectMaker(
            viewsNotOnSheet,
            "Views<br>not on Sheet",
            viewNotOnSheetTres
        )
    )
    dashboardLeftMaker(htmlRowViews)

    ## ViewTemplates dashboard section
    # print ViewTemplates section header
    output.print_md("# View Templates")

    # Make row
    htmlRowViews = (
        dashboardRectMaker(len(viewTemplates), "View Templates", viewTemplatesTres)
        + dashboardRectMaker(unusedViewTemplatesCount, "Unused View Templates", unusedViewTemplateTres)

    )
    dashboardLeftMaker(htmlRowViews)

    ## Schedule dashboard section
    # print Schedules section header
    output.print_md("# Schedules")

    # Make row
    htmlRowSchedules = (
        dashboardRectMaker(
            scheduleCount, "Schedules", scheduleTres
        )
        + dashboardRectMaker(
            scheduleNotOnSheet,
            "Schedules<br>not on Sheet",
            schedulesNotOnSheetTres
        )
    )
    dashboardLeftMaker(htmlRowSchedules)

    ## Sheets dashboard section
    # print Sheets section header
    output.print_md("# Sheets")

    # Make row
    htmlRowSheets = (
        dashboardRectMaker(sheetCount, "Sheets", sheetsTres)
    )
    dashboardLeftMaker(htmlRowSheets)

    ## Warnings dashboard section
    # print Warnings section header
    output.print_md("# Warnings")
    # Make row
    if allWarningsCount != 0:
        htmlRowWarnings = (
            dashboardRectMaker(
                allWarningsCount, "Warnings", warningsTres
            )
            + dashboardRectMaker(
                criticalWarningCount,
                "Critical <br>Warnings",
                criticalWarningsTres
            )
        )
        dashboardLeftMaker(htmlRowWarnings)
        # warnings count per type doughnut
        chartWarnings = output.make_doughnut_chart()
        chartWarnings.options.title = {
            "display": True,
            "text": "Warning Count by Type",
            "fontSize": 25,
            "fontColor": "#000",
            "fontStyle": "bold",
            "position": "left"
        }
        chartWarnings.options.legend = {"position": "top", "fullWidth": False}
        chartWarnings.data.labels = [x.encode('UTF-8') for x in warnDescriptionHeadings]
        set_w = chartWarnings.data.new_dataset("Not Standard")
        set_w.data = warnSet
        set_w.backgroundColor = COLORS
        chartWarnings.draw()
    else:
        output.print_md("No warnings, good job!")

    ## Materials dashboard section
    # print Materials section header
    output.print_md("# Materials")

    # Make row
    htmlRowMaterials = (
        dashboardRectMaker(
            materialCount, "Materials", materialsTres
        )
    )
    dashboardLeftMaker(htmlRowMaterials)

    ## Line patterns dashboard section
    # print Line patterns section header
    output.print_md("# Line patterns")

    # Make row
    htmlRowLinePatterns = (dashboardRectMaker(
            linePatternCount, "Line Patterns", linePatternsTres
        )
    )
    dashboardLeftMaker(htmlRowLinePatterns)

    ## DWGs dashboard section
    # print DWGs section header
    output.print_md("# DWGs")

    # Make row
    htmlRowDWGs = (dashboardRectMaker(
            importedDwg, "Imported DWGs", importedDwgTres
        )
        + dashboardRectMaker(
            linkedDwg, "Linked DWGs", linkedDwgTres
        )
        + dashboardRectMaker(
            dwgNotCurrentView, "DWGs in 3D", dwgNotCurrentViewTres
        )
    )
    dashboardLeftMaker(htmlRowDWGs)

    ## Loadable Families dashboard section
    # print Loadable Families section header
    output.print_md("# Loadable Families")

    # data for category graph
    graphCatHeadings = []
    graphCatData = []
    elements = (
        DB.FilteredElementCollector(doc)
        .WhereElementIsNotElementType()
        .ToElements()
    )

    catBanlist = [
        -2000110,
        -2003101,
        -2005210,
        -2009609,
        -2000552,
        -2008107,
        -2008121,
        -2008120,
        -2008119,
        -2001272,
        -2001271,
        -2008142,
        -2008143,
        -2008145,
        -2008147,
        -2008146,
        -2008148,
        -2000261,
    ]
    generic_model_elements = []
    generic_model_elements_count = 0
    for element in elements:
        try:
            category = element.Category.Name
            categoryId = element.Category.Id.IntegerValue
            # filtering out DWGs and DXFs, categories from banlist
            # filtering out categories in catBanlist
            # DB.BuiltInCategory Ids are negative integers
            if categoryId < 0 and categoryId not in catBanlist:
                if category not in graphCatHeadings:
                    graphCatHeadings.append(category)
                graphCatData.append(category)
            if categoryId == -2000151:
                generic_model_elements.append(category)
        except:
            pass
    # Generic model count
    generic_model_elements_count = len(generic_model_elements)
    catSet = []
    # sorting results in chart legend
    graphCatHeadings.sort()
    for i in graphCatHeadings:
        count = graphCatData.count(i)
        catSet.append(count)
    

    graphCatHeadings = [x.encode("UTF8") for x in graphCatHeadings]

    # Make row
    htmlRowLoadableFamilies = (
        dashboardRectMaker(familyCount, "Families", familiesTres)
        + dashboardRectMaker(
            inPlaceFamilyCount,
            "In Place <br>Families",
            inPlaceFamilyTres
        )
        + dashboardRectMaker(
            NotParamFamiliesCount,
            "Families <br>not parametric",
            notParamFamiliesTres
        )
        + dashboardRectMaker(
            generic_model_elements_count, 
            "Generic models", 
            genericModelTres    
        )
    )
    dashboardLeftMaker(htmlRowLoadableFamilies)


    if inPlaceFamilyCount != 0:
            # INPLACE CATEGORY GRAPH
        fCatSet = []
        # sorting results in chart legend
        graphFCatHeadings.sort()
        for i in graphFCatHeadings:
            count = graphFCatData.count(i)
            fCatSet.append(count)

        graphFCatData = [x.encode("utf8") for x in graphFCatData]
        graphFCatHeadings = [x.encode("utf8") for x in graphFCatHeadings]

        # categories OUTPUT
        chartFCategories = output.make_doughnut_chart()
        chartFCategories.options.title = {
            "display": True,
            "text": "InPlace Family Count by Category",
            "fontSize": 25,
            "fontColor": "#000",
            "fontStyle": "bold",
            "position": "left"
        }
        chartFCategories.data.labels = graphFCatHeadings
        set_a = chartFCategories.data.new_dataset("Not Standard")
        set_a.data = fCatSet

        set_a.backgroundColor = COLORS
        # chartFCategories.randomize_colors()
        # scaling graph according to categories count - size of graph is
        # measured with legend which can be quite complex
        catFCount = len(graphFCatHeadings)
        if catFCount < 15:
            chartFCategories.set_height(100)
        elif catFCount < 30:
            chartFCategories.set_height(160)
        else:
            chartFCategories.set_height(200)

        chartFCategories.draw()
    else:
        pass

    ## Text Notes dashboard section
    # print Text Notes section header
    output.print_md("# Text Notes")

    # Make row
    htmlRowTextNotes = (dashboardRectMaker(
            textnoteWFcount,
            "Text - Width <br>Factor changed",
            textnoteWFtres
        )
        + dashboardRectMaker(
            capsCount, "Text - AllCaps", textnoteCaps
        )
    )
    dashboardLeftMaker(htmlRowTextNotes)

    ## System families dashboard section
    # print System families section header
    output.print_md("# System Families")

    # Make row
    htmlRowTextNotes = (dashboardRectMaker(
            ramp_collector, "Ramps", rampTres)
        + dashboardRectMaker(
            archColumn_collector,
            "Architecural <br>Columns",
            archTres
        )
        + dashboardRectMaker(
            activated_analytical_model_elements_count, 
            "elements with analytical model activated", 
            activated_analytical_model_elements_count_tres   
        )
    )
    dashboardLeftMaker(htmlRowTextNotes)


    ## Groups dashboard section
    # print Groups section header
    output.print_md("# Groups")
    # Make row
    htmlRowGroupsTypes = (
        dashboardRectMaker(
            detailGroupTypeCount,
            "Detail Group <br>Types",
            detailGroupTypeTres
        )
        + dashboardRectMaker(
            modelGroupTypeCount,
            "Model Group <br>Types",
            modelGroupTypeTres
        )
    )
    dashboardLeftMaker(htmlRowGroupsTypes)

    htmlRowGroups = (dashboardRectMaker(
            detailGroupCount, "Detail Groups", detailGroupTres
        )
        + dashboardRectMaker(
            modelGroupCount, "Model Groups", modelGroupTres
        )
    )
    dashboardLeftMaker(htmlRowGroups)

    ## Reference Planes dashboard section
    # print Reference Planes section header
    output.print_md("# Reference Planes")
    # Make row
    htmlRowRefPlanes = (
        dashboardRectMaker(
            noNameRefPCount,
            "NoName <br>Reference Planes",
            noNameRefPTres
        )
        + dashboardRectMaker(
            RefPCount,
            "Reference Planes",
            RefPTres
        )
    )
    dashboardLeftMaker(htmlRowRefPlanes)

    ## Phases dashboard section
    # print Phases section header
    output.print_md("# Phases\n")
    rvtlinkdocsName.insert(0,printedName)
    filePhases = rvtlinkdocsName,[','.join(i) for i in phase]
    output.print_table(zip(*filePhases), columns=["Instance File Name","Phases"], formats=None, title='', last_line_style='')

    ## Elements count dashboard section
    # print Elements count section header
    output.print_md("# Elements count")

    # Make row
    htmlRowElementsCount = (dashboardRectMaker(
            elementCount, "Elements", elementsTres
        )
    )
    dashboardLeftMaker(htmlRowElementsCount)

    # divider
    print("\n\n\n\n")

    # categories OUTPUT
    chartCategories = output.make_doughnut_chart()
    chartCategories.options.title = {
        "display": True,
        "text": "Element Count by Category",
        "fontSize": 25,
        "fontColor": "#000",
        "fontStyle": "bold",
    }
    chartCategories.data.labels = graphCatHeadings
    set_a = chartCategories.data.new_dataset("Not Standard")
    set_a.data = catSet

    set_a.backgroundColor = COLORS
    # chartCategories.randomize_colors()
    # scaling graph according to categories count - size of graph is measured
    # with legend which can be quite complex
    catCount = len(graphCatHeadings)
    if catCount < 60:
        chartCategories.set_height(150)
    elif catCount < 85:
        chartCategories.set_height(200)
    elif catCount < 100:
        chartCategories.set_height(250)
    else:
        chartCategories.set_height(300)

    chartCategories.draw()

    # divider
    print("\n\n\n\n")

    # elements by workset graph
    worksetIds = []
    worksetNames = []
    graphWorksetsData = []

    elcollector = (
        DB.FilteredElementCollector(doc)
        .WhereElementIsNotElementType()
        .ToElements()
    )
    worksetTable = doc.GetWorksetTable()
    for element in elcollector:
        worksetId = element.WorksetId
        worksetKind = str(worksetTable.GetWorkset(worksetId).Kind)
        if worksetKind == "UserWorkset":
            worksetName = worksetTable.GetWorkset(worksetId).Name
            if worksetName not in worksetNames:
                worksetNames.append(worksetName)
            graphWorksetsData.append(worksetName)
    # print worksetNames
    # sorting results in chart legend
    worksetNames.sort()

    worksetsSet = []
    for i in worksetNames:
        count = graphWorksetsData.count(i)
        worksetsSet.append(count)
    worksetNames = [x.encode("utf8") for x in worksetNames]

    # Worksets OUTPUT print chart only when file is workshared
    if len(worksetNames) > 0:
        chartWorksets = output.make_doughnut_chart()
        chartWorksets.options.title = {
            "display": True,
            "text": "Element Count by Workset",
            "fontSize": 25,
            "fontColor": "#000",
            "fontStyle": "bold",
        }
        chartWorksets.data.labels = worksetNames
        set_a = chartWorksets.data.new_dataset("Not Standard")
        set_a.data = worksetsSet

        set_a.backgroundColor = COLORS

        worksetsCount = len(worksetNames)
        if worksetsCount < 15:
            chartWorksets.set_height(100)
        elif worksetsCount < 30:
            chartWorksets.set_height(160)
        else:
            chartWorksets.set_height(200)

        chartWorksets.draw()

class ModelChecker(PreflightTestCase):
    """
    Revit model quality check
    The QC tools returns you with the following data:
        Revit file: Name and Project Information
        Revit links: list, count and pinned status
        Views: number, number of copied views, number of views not on sheet
        Schedules: number and not on sheet number
        Sheets: number
        Warnings: Total number, Critical warnings list based on predefined list of critical warnings
        Materials count
        Line patterns count
        DWGs: Imported count, linked count, dwgs in 3D count
        Loadable families: count, in place family count, non parametric families count
        Text notes: with factor changed count, all caps text notes count
        System families: ramps count, architectural columns count, elements with analytical model option enabled
        Groups: detail group types count, detail group instances count, model group types count, model groups instances count
        Reference planes: not named count, ref planes count
        Elements count
        Phases: list of phases for current document and linked files
        Element count per category donut chart
        Element count per workset donut chart
        In place family count per category donut chart
    """

    name = "Model Checker"
    author = "David Vadkerti, Jean-Marc Couffin"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        timer = coreutils.Timer()
        checkModel(doc, output)
        endtime = timer.get_time()
        endtime_hms = str(datetime.timedelta(seconds=endtime))
        endtime_hms_claim = "Transaction took " + endtime_hms
        print(endtime_hms_claim)

    def tearDown(self, doc, output):
        pass

    def doCleanups(self, doc, output):
        pass
