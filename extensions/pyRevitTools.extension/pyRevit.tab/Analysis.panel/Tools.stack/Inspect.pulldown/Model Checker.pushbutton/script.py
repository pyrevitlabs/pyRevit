# -*- coding: UTF-8 -*-
__title__ = 'Model\nChecker'
__doc__ = 'Revit model quality check.'
__author__ = 'David Vadkerti'

from pyrevit import coreutils, script, DB
from pyrevit import output
import unicodedata
import datetime

from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, ImportInstance
from Autodesk.Revit.DB import LinePatternElement, Family, TextNoteType, ScheduleSheetInstance, WorksetTable, TextNote, ReferencePlane
from Autodesk.Revit.UI import UIApplication
from pyrevit.coreutils import Timer

doc = __revit__.ActiveUIDocument.Document
uiapp = UIApplication(doc.Application)

timer = Timer()

# LISTS
# colors for chart.js graphs - chartCategories.randomize_colors() sometimes creates colors which are not distunguishable or visible
colors = 10*["#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb",
            "#4d4d4d","#000000","#fff0f2","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#e97800","#a6c844",
            "#4d4d4d","#fff0d9","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#e97800","#a6c844",
            "#fff0e6","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#fff0e6","#e97800","#a6c844",
            "#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#9988bb","#4d4d4d","#e97800","#a6c844",
            "#4d4d4d","#fff0d9","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#e97800","#a6c844",
            "#4d4d4d","#fff0d9","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#e97800","#a6c844",
            "#4d4d4d","#fff0d9","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#e97800","#a6c844",
            "#4d4d4d","#fff0d9","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#e97800","#a6c844",
            "#4d4d4d","#fff0d9","#ffc299","#ff751a","#cc5200","#ff6666","#ffd480","#b33c00","#ff884d","#d9d9d9","#9988bb","#4d4d4d","#e97800","#a6c844",]


# list of Warnings rated as critical (warnings which could distort quantities and schedules)
criticalWarnings = ['Elements have duplicate "Type Mark" values',
    'There are identical instances in the same place',
    'Room Tag is outside of its Room',
    'Multiple Rooms are in the same enclosed region',
    'Multiple Areas are in the same enclosed region',
    'One element is completely inside another',
    'Room is not in a properly enclosed region',
    'Room separation line is slightly off axis and may cause inaccuracies',
    'Area is not in a properly enclosed region',
    "Rectangular opening doesn't cut its host",
    'Elements have duplicate "Number" values',]

# webpage with explanations of bad practices in revit maybe it could be configurable in the future?
wikiArticle = "https://www.modelical.com/en/gdocs/revit-arc-best-practices/"
# dashboard HTMl maker - rectangle with large number
def dashboardRectMaker(value,description,treshold,wikiArticle):
        content = str(value)
        # normal button
        if value <= treshold:
            html_code = "<a class='dashboardLink' title='OK - maximum value "+str(int(treshold)) \
            +"'><p class='dashboardRectNormal'>"+content+"<br><span class='dashboardSmall'>"+description+"</span>""</p></a>"
            return coreutils.prepare_html_str(html_code)
        # mediocre button
        elif value < treshold*2:
            html_code = "<a class='dashboardLink' href='"+wikiArticle+"' title='Mediocre - goal value "+str(int(treshold)) \
                +"'><p class='dashboardRectMediocre'>" + content + "<br><span class='dashboardSmall'>"+description+"</span>""</p></a>"
            return coreutils.prepare_html_str(html_code)
        # critical button
        else:
            html_code = "<a class='dashboardLink' href='"+wikiArticle+"' title='Critical - goal value "+str(int(treshold)) \
                +"'><p class='dashboardRectCritical'>" + content + "<br><span class='dashboardSmall'>"+description+"</span>""</p></a>"
            return coreutils.prepare_html_str(html_code)


# dashboard HTMl maker - div for center aligning
def dashboardCenterMaker(value):
        content = str(value)
        html_code = "<div class='dashboardCenter'>"+content+"</div>"
        print(coreutils.prepare_html_str(html_code))

# returns file name - everything in path from "\\" or "/" to the end
def path2fileName(file_path,divider):
  lastDivider = file_path.rindex(divider)+1
  file_name = file_path[lastDivider:]
  # print file_name
  return file_name

# converts accented string to nonaccented string
def accents2ascii(s):
   return ''.join(c for c in unicodedata.normalize('NFD', s)
                  if unicodedata.category(c) != 'Mn')

output = script.get_output()
output.set_height(1000)

# printing file name and heading
name = doc.PathName
if len(name) == 0:
    # name = "Not saved file"
    printedName = "Not saved file"
else:
    # workshared file
    try:
        central_path = revit.query.get_central_path(doc)
        try:
            # for rvt server
            printedName = path2fileName(central_path,"/")
        except:
            # other locations
            printedName = path2fileName(central_path,"\\")
    # non workshared file
    except:
        file_path = doc.PathName
        try:
            printedName = path2fileName(file_path,"\\")
        except:
            # detached file
            printedName = file_path
output.print_md("# MODEL CHECKER")
output.print_md("## " + printedName)

# first JS to avoid error in IE output window when at first run
# this is most likely not proper way
try:
    chartOuputError = output.make_doughnut_chart()
    chartOuputError.data.labels = []
    set_E = chartOuputError.data.new_dataset('Not Standard')
    set_E.data = []
    set_E.backgroundColor = ["#fff"]
    chartOuputError.set_height(1)
    chartOuputError.draw()
except:
    pass

# sheets
sheets_id_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Sheets) \
.WhereElementIsNotElementType() \
.ToElementIds()
sheetCount = len(sheets_id_collector)
# print(str(sheetCount)+" Sheets")


# schedules
schedules_id_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Schedules) \
.WhereElementIsNotElementType() \
.ToElements()
scheduleCount = 0
for schedule in schedules_id_collector:
    if schedule.Name[:19] != "<Revision Schedule>":
        scheduleCount += 1
# print(str(scheduleCount)+" Schedules")


# views
views_id_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Views) \
.WhereElementIsNotElementType()
view_elements = views_id_collector.ToElements()
viewCount = len(view_elements)

copiedView = 0
for view in view_elements:
    viewName = view.LookupParameter('View Name')
    try:
        viewNameString = viewName.AsString()
        # print(viewNameString)
        if viewNameString[-6:-2] == "Copy" or viewNameString[-4:] == "Copy" or viewNameString[:7] == "Section":
        # if viewNameString[:7] == "Section":
            copiedView += 1
    except:
        pass

sheets_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Sheets) \
.WhereElementIsNotElementType().ToElements()

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
viewsNotOnSheet = viewCount-len(viewsOnSheet)

# schedules not on sheets
schedulesOnSheet = []
scheduleCollector1 = FilteredElementCollector(doc).OfClass(ScheduleSheetInstance).WhereElementIsNotElementType()
scheduleCollector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Schedules) \
.WhereElementIsNotElementType()
# there is need to iterate class and category filter to get all schedule
# it is something with schedules on more sheets maybe...
for schedule in scheduleCollector:
    schedName = schedule.Name
    if schedName[:19] != "<Revision Schedule>":
        if schedName not in schedulesOnSheet:
            if schedule.OwnerViewId.IntegerValue != -1:
                # print schedName
                # print schedule.Id
                schedulesOnSheet.append(schedName)

# there is need to iterate class and category filter to get all schedule - UnionWith didn't work
for schedule in scheduleCollector1:
    schedName = schedule.Name
    if schedName[:19] != "<Revision Schedule>":
        if schedName not in schedulesOnSheet:
            if schedule.OwnerViewId.IntegerValue != -1:
                # print schedName
                # print schedule.Id
                schedulesOnSheet.append(schedName)
scheduleNotOnSheet = scheduleCount-len(schedulesOnSheet)

# tresholds
viewTres = 500
viewNotOnSheetTres = viewCount*0.2
copiedViewTres = viewCount*0.2
sheetsTres = 500
scheduleTres = 500
schedulesNotOnSheetTres = scheduleCount*0.3

htmlRow1 = (dashboardRectMaker(viewCount,"Views",viewTres,wikiArticle)
     + dashboardRectMaker(copiedView,"Copied Views",copiedViewTres,wikiArticle)
     + dashboardRectMaker(sheetCount,"Sheets",sheetsTres,wikiArticle)
     + dashboardRectMaker(scheduleCount,"Schedules",scheduleTres,wikiArticle)
     + dashboardRectMaker(viewsNotOnSheet,"Views <br>not on Sheet",viewNotOnSheetTres,wikiArticle) 
     + dashboardRectMaker(scheduleNotOnSheet,"Schedules <br>not on Sheet",schedulesNotOnSheetTres,wikiArticle))
dashboardCenterMaker(htmlRow1)


# warnings
allWarnings_collector = doc.GetWarnings()
allWarningsCount = len(allWarnings_collector)
# print(str(allWarningsCount)+" Warnings")


# critical warnings
criticalWarningCount = 0
for criticalWarning in allWarnings_collector:
    description = criticalWarning.GetDescriptionText()
    # for warning type heading
    try:
        descLen = description.index(".")
    # Few warnings have mistakenly no dot in the end.
    except:
        descLen = len(description)
    descHeading = description[:descLen]
    if descHeading in criticalWarnings:
        criticalWarningCount += 1


# materials
materialCount = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Materials).GetElementCount()
# print(str(materialCount)+" Materials")


# line patterns
linePatternCount = FilteredElementCollector(doc).OfClass(LinePatternElement).GetElementCount()
# print(str(linePatternCount)+" Line Patterns")


# DWGs
dwg_collector = FilteredElementCollector(doc).OfClass(ImportInstance).WhereElementIsNotElementType().ToElements()

importedDwg = 0
dwgNotCurrentView = 0
for dwg in dwg_collector:
    if dwg.IsLinked != True:
        importedDwg += 1
    if dwg.ViewSpecific == False:
        dwgNotCurrentView += 1

# print("\nDWGs")
# print(str(importedDwg)+" Imported DWG files")

# dwgCount = dwg_collector.GetElementCount()
dwgCount = len(dwg_collector)
linkedDwg = (dwgCount-importedDwg)

# tresholds
warningsTres = 500
criticalWarningsTres = 0
materialsTres = 150
linePatternsTres = 100
importedDwgTres = 0
linkedDwgTres = viewCount/2
dwgNotCurrentViewTres = 0

# dashboard row 2
htmlRow2 = (dashboardRectMaker(allWarningsCount,"Warnings",warningsTres,wikiArticle)
    + dashboardRectMaker(criticalWarningCount,"Critical <br>Warnings",criticalWarningsTres,wikiArticle)
    + dashboardRectMaker(materialCount,"Materials",materialsTres,wikiArticle)
    + dashboardRectMaker(linePatternCount,"Line Patterns",linePatternsTres,wikiArticle)
    + dashboardRectMaker(importedDwg,"Imported DWGs",importedDwgTres,wikiArticle)
    + dashboardRectMaker(linkedDwg,"Linked DWGs",linkedDwgTres,wikiArticle)
    + dashboardRectMaker(dwgNotCurrentView,"DWGs in 3D",dwgNotCurrentViewTres,wikiArticle))
dashboardCenterMaker(htmlRow2)


# families
graphFCatHeadings = []
graphFCatData = []
families = FilteredElementCollector(doc).OfClass(Family)
inPlaceFamilyCount = 0
NotParamFamiliesCount = 0
for family in families:
    if family.IsInPlace == True:
        inPlaceFamilyCount += 1
        # for graph
        inPlaceFCategory = family.FamilyCategory.Name
        if inPlaceFCategory not in graphFCatHeadings:
            graphFCatHeadings.append(inPlaceFCategory)
        graphFCatData.append(inPlaceFCategory)
    if family.IsParametric == False:
        NotParamFamiliesCount += 1
familyCount = families.GetElementCount()

# print(str(familyCount)+" Families")
# print(str(inPlaceFamilyCount)+" In Place Families")
# print(str(NotParamFamiliesCount)+" Families are not parametric")

# tresholds
familiesTres = 500
if familyCount < 500:
    inPlaceFamilyTres = familyCount*0.2
else:
    inPlaceFamilyTres = 500*0.2
notParamFamiliesTres = familyCount*0.3
textnoteWFtres = 0
textnoteCaps = 0
rampTres = 0
archTres = 0

# Text notes width factor != 1
textNoteType_collector = FilteredElementCollector(doc).OfClass(TextNoteType).ToElements()
textnoteWFcount = 0
for textnote in textNoteType_collector:
    widthFactor = textnote.LookupParameter('Width Factor').AsDouble()
    if widthFactor != 1:
        textnoteWFcount += 1

# Text notes with allCaps applied in Revit
textNote_collector = FilteredElementCollector(doc).OfClass(TextNote).ToElements()
capsCount = 0
for textN in textNote_collector:
    capsStatus = textN.GetFormattedText().GetAllCapsStatus()
    if str(capsStatus) != "None":
        capsCount +=1

# Ramps
ramp_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Ramps).WhereElementIsNotElementType().GetElementCount()

# Architecural columns
archColumn_collector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Columns).WhereElementIsNotElementType().GetElementCount()

# dashboard row3
htmlRow3 = (dashboardRectMaker(familyCount,"Families",familiesTres,wikiArticle)
        + dashboardRectMaker(inPlaceFamilyCount,"In Place <br>Families",inPlaceFamilyTres,wikiArticle)
        + dashboardRectMaker(NotParamFamiliesCount,"Families <br>not parametric",notParamFamiliesTres,wikiArticle)
        + dashboardRectMaker(textnoteWFcount,"Text - Width <br>Factor changed",textnoteWFtres,wikiArticle)
        + dashboardRectMaker(capsCount,"Text - AllCaps",textnoteCaps,wikiArticle)
        + dashboardRectMaker(ramp_collector,"Ramps",rampTres,wikiArticle)
        + dashboardRectMaker(archColumn_collector,"Architecural <br>Columns",archTres,wikiArticle))
dashboardCenterMaker(htmlRow3)

# detail groups
detailGroupCount = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_IOSDetailGroups).WhereElementIsNotElementType().GetElementCount()
detailGroupTypeCount = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_IOSDetailGroups).GetElementCount() - detailGroupCount
# print(str(detailGroupTypeCount)+" Detail Group Types")
# print(str(detailGroupCount)+" Detail Groups")


# model groups
modelGroupCount = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_IOSModelGroups).WhereElementIsNotElementType().GetElementCount()
modelGroupTypeCount = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_IOSModelGroups).GetElementCount() - modelGroupCount
# print(str(modelGroupTypeCount)+" Model Group Types")
# print(str(modelGroupCount)+" Model Groups")

# reference plane without name
refPlaneCollector = FilteredElementCollector(doc).OfClass(ReferencePlane).ToElements()
noNameRefPCount = 0
for refPlane in refPlaneCollector:
    if refPlane.Name == "Reference Plane":
        noNameRefPCount += 1

# Element Count
elementCount = FilteredElementCollector(doc).WhereElementIsNotElementType().GetElementCount()
# _2DelementCount = FilteredElementCollector(doc).OwnedByView().GetElementCount()

# print(str(elementCount)+" Elements")

# tresholds
detailGroupTypeTres = 30
detailGroupTres = 500
modelGroupTypeTres = 30
modelGroupTres = 200
noNameRefPTres = 0
elementsTres = 1000000

# dashboard
htmlRow4 = (dashboardRectMaker(detailGroupTypeCount,"Detail Group <br>Types",detailGroupTypeTres,wikiArticle)
    + dashboardRectMaker(detailGroupCount,"Detail Groups",detailGroupTres,wikiArticle) 
    + dashboardRectMaker(modelGroupTypeCount,"Model Group <br>Types",modelGroupTypeTres,wikiArticle)
    +dashboardRectMaker(modelGroupCount,"Model Groups",modelGroupTres,wikiArticle) 
    + dashboardRectMaker(noNameRefPCount,"NoName <br>Reference Planes",noNameRefPTres,wikiArticle)
    + dashboardRectMaker(elementCount,"Elements",elementsTres,wikiArticle))
dashboardCenterMaker(htmlRow4)


# divider
print("\n\n\n\n")

# data for category graph
graphCatHeadings = []
graphCatData = []
elements = FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements()
# categories we dont want to see since they are mostly not user created
catBanlist = ['Shared Site','Project Information','Structural Load Cases','Sun Path','Color Fill Schema','HVAC Zones','HVAC Load Schedules','Building Type Settings',
    'Space Type Settings','Survey Point','Project Base Point','Electrical Demand Factor Definitions','Electrical Load Classifications','Panel Schedule Templates - Branch Panel',
    'Panel Schedule Templates - Data Panel','Panel Schedule Templates - Switchboard','Electrical Load Classification Parameter Element','Automatic Sketch Dimensions',]
for i in elements:
    try:
        category = i.Category.Name
        # filtering out DWGs and DXFs, categories from banlist
        # filtering out categories with "<" and ")" since it makes errors in chart.js output and we dont need them
        if category[-4:-2] != ".d" and category[-4:-2] != ".D" and category[0] != "<" and category[-1] != ")" and category not in catBanlist:
            # category = accents2ascii(category)
            if category not in graphCatHeadings:
                graphCatHeadings.append(category)
            graphCatData.append(category)
    except:
        pass

catSet=[]
# sorting results in chart legend
graphCatHeadings.sort()
for i in graphCatHeadings:
    count=graphCatData.count(i)        
    catSet.append(count)

# for debugging
# print graphCatHeadings
# print catSet

# categories OUTPUT
chartCategories = output.make_doughnut_chart()
chartCategories.options.title = {'display': True, 'text':'Element Count by Category', 'fontSize': 18, 'fontColor': '#000', 'fontStyle': 'bold'}
chartCategories.data.labels = graphCatHeadings
set_a = chartCategories.data.new_dataset('Not Standard')
set_a.data = catSet

set_a.backgroundColor = colors
# chartCategories.randomize_colors()
# scaling graph according to categories count - size of graph is measured with legend which can be quite complex
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
# elcollector = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Walls).WhereElementIsNotElementType().ToElements()
elcollector = FilteredElementCollector(doc).WhereElementIsNotElementType().ToElements()
worksetTable = doc.GetWorksetTable()
for element in elcollector:
    worksetId = element.WorksetId
    worksetKind = str(worksetTable.GetWorkset(worksetId).Kind)
    if worksetKind == "UserWorkset":
        worksetNameAcc = worksetTable.GetWorkset(worksetId).Name
        # nonaccented version for chart
        worksetName = accents2ascii(worksetNameAcc)
        if worksetName not in worksetNames:
            worksetNames.append(worksetName)
        graphWorksetsData.append(worksetName)
# print worksetNames
# sorting results in chart legend
worksetNames.sort()
worksetsSet=[]
for i in worksetNames:
    count=graphWorksetsData.count(i)        
    worksetsSet.append(count)

# Worksets OUTPUT print chart only when file is workshared
if len(worksetNames) > 0:
    chartWorksets = output.make_doughnut_chart()
    chartWorksets.options.title = {'display': True, 'text':'Element Count by Workset', 'fontSize': 18, 'fontColor': '#000', 'fontStyle': 'bold'}
    chartWorksets.data.labels = worksetNames
    set_a = chartWorksets.data.new_dataset('Not Standard')
    set_a.data = worksetsSet

    set_a.backgroundColor = colors

    worksetsCount = len(worksetNames)
    if worksetsCount < 15:
        chartWorksets.set_height(100)
    elif worksetsCount < 30:
        chartWorksets.set_height(160)
    else:
        chartWorksets.set_height(200)

    chartWorksets.draw()

# divider
print("\n\n\n\n")

# INPLACE CATEGORY GRAPH
fCatSet=[]
# sorting results in chart legend
graphFCatHeadings.sort()
for i in graphFCatHeadings:
    count=graphFCatData.count(i)        
    fCatSet.append(count)


# categories OUTPUT
chartFCategories = output.make_doughnut_chart()
chartFCategories.options.title = {'display': True, 'text':'InPlace Family Count by Category', 'fontSize': 18, 'fontColor': '#000', 'fontStyle': 'bold'}
chartFCategories.data.labels = graphFCatHeadings
set_a = chartFCategories.data.new_dataset('Not Standard')
set_a.data = fCatSet

set_a.backgroundColor = colors
# chartFCategories.randomize_colors()
# scaling graph according to categories count - size of graph is measured with legend which can be quite complex
catFCount = len(graphFCatHeadings)
if catFCount < 15:
    chartFCategories.set_height(100)
elif catFCount < 30:
    chartFCategories.set_height(160)
else:
    chartFCategories.set_height(200)

chartFCategories.draw()


# for timing------
endtime = timer.get_time()
endtime_hms = str(datetime.timedelta(seconds=endtime))
endtime_hms_claim = "Transaction took "+ endtime_hms
print(endtime_hms_claim)