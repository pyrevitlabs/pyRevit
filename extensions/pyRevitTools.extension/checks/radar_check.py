# -*- coding: utf-8 -*-

# Read Me, you can download a test model from the following link:
# https://drive.google.com/file/d/1xt7IVmCh2_5MIVXrXWPPFJ50glG1RAEK/view?usp=sharing


#______________________________________________Imports

#General Imports
import sys
import math

#.NET Imports
import clr
clr.AddReference('System')
from System.Collections.Generic import List
clr.AddReference('RevitAPI')
from Autodesk.Revit.DB import *

#pyRevit
from pyrevit import DB, DOCS, HOST_APP
from pyrevit import script
from pyrevit.preflight import PreflightTestCase

#______________________________________________Global Variables
doc    = DOCS.doc #type:Document
intOrig = (0,0,0)
extentdistance = 52800 #Linear Feet

#______________________________________________3D to Bounding Box Analysis
class Get3DViewBoundingBox():
    def get_tempbbox(self, ToggleCAD, ToggleRVT, ToggleIFC, ToggleAll):
        violatingCAD = []
        violatingRVT = []
        badelements = []
        # Create a 3D view
        t = Transaction(doc, "Create 3D View")
        t.Start()
        view3Dtypes = DB.FilteredElementCollector(doc).OfClass(DB.ViewFamilyType).WhereElementIsElementType().ToElements()
        view3dtype = [v for v in view3Dtypes if v.ViewFamily == DB.ViewFamily.ThreeDimensional][0]
        view = DB.View3D.CreateIsometric(doc, view3dtype.Id)
        worksets = FilteredWorksetCollector(doc).OfKind(WorksetKind.UserWorkset).ToWorksets()
        for ws in worksets:
            view.SetWorksetVisibility(ws.Id, DB.WorksetVisibility.Visible)
        view.IsSectionBoxActive = True
        bb = view.GetSectionBox()
        if ToggleCAD:
            cads = FilteredElementCollector(doc).OfClass(ImportInstance).ToElements()
            if len(cads) == 0:
                print("No CAD Links in the model")
            else:
                for cad in cads:
                    cadbox = cad.get_BoundingBox(None)
                    cadmin = (cadbox.Min.X, cadbox.Min.Y, cadbox.Min.Z)
                    cadmax = (cadbox.Max.X, cadbox.Max.Y, cadbox.Max.Z)
                    if calculate_distance(cadmin, intOrig) > extentdistance or calculate_distance(cadmax, intOrig) > extentdistance:
                        violatingCAD.append(cad)
        if ToggleRVT:
            rvtlinks = FilteredElementCollector(doc).OfClass(RevitLinkInstance).ToElements()
            if len(rvtlinks) == 0:
                print("No RVT Links in the model")
            else:
                for rvt in rvtlinks:
                    rvtbox = rvt.get_BoundingBox(view)
                    rvtmin = (rvtbox.Min.X, rvtbox.Min.Y, rvtbox.Min.Z)
                    rvtmax = (rvtbox.Max.X, rvtbox.Max.Y, rvtbox.Max.Z)
                    if calculate_distance(rvtmin, intOrig) > extentdistance or calculate_distance(rvtmax, intOrig) > extentdistance:
                        violatingRVT.append(rvt)
        if ToggleIFC:
            pass
        allrvt = FilteredElementCollector(doc).OfClass(RevitLinkType).ToElements()
        allcad = FilteredElementCollector(doc).OfClass(ImportInstance).ToElements()
        if len(allrvt) > 0:
            view.HideElements(FilteredElementCollector(doc).OfClass(RevitLinkType).ToElementIds())
        if len(allcad) > 0:
            view.HideElements(FilteredElementCollector(doc).OfClass(ImportInstance).ToElementIds())
        view.IsSectionBoxActive = False
        view.IsSectionBoxActive = True
        bbh = view.GetSectionBox()
        if ToggleAll:
            elcollector = FilteredElementCollector(doc,view.Id).WhereElementIsNotElementType().ToElements()
            for el in elcollector:
                if el.get_BoundingBox(view) is not None and hasattr(el, 'Name') and hasattr(el, 'Category'):
                    bbox = el.get_BoundingBox(view)
                    if analyzebbox(bbox, intOrig, 52800) == 0:
                        badelements.append(el)

        t.Dispose()
        return bb, violatingCAD, violatingRVT, bbh, badelements
               
#____________________________________________ Calculate Distance
def calculate_distance(point1, point2):
    # Unpack the tuples
    x1, y1, z1 = point1
    x2, y2, z2 = point2

    # Calculate the distance using the Euclidean distance formula
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 + (z2 - z1)**2)

    return distance

def convert_units(doc, distance):


    if HOST_APP.is_newer_than(2021):
        UIunits = DB.UnitFormatUtils.Format(units=doc.GetUnits(),
                                            specTypeId=DB.SpecTypeId.Length,
                                            value=distance,
                                            forEditing=False)


    else:
        UIunits = DB.UnitFormatUtils(units=doc.GetUnits(),
                                     unitType=DB.UnitType.UT_Length,
                                        value=distance,
                                        maxAccuracy=False,
                                        forEditing=False)

    return UIunits


#____________________________________________ Calculate Horizontal Distance
def calculate_Horizontal_Distance(point1, point2):
    # Unpack the tuples
    x1, y1, z1 = point1
    x2, y2, z2 = point2

    # Calculate the distance using the Euclidean distance formula
    distance = math.sqrt((x2 - x1)**2 + (y2 - y1)**2 )
    deltaX = (x2 - x1)
    deltaY = (y2 - y1)

    return distance, deltaX, deltaY

#____________________________________________ Get Bounding Box
def get_bounding_box(view):
    bb = view.CropBox
    min = bb.Min
    max = bb.Max
    return min, max

#____________________________________________ Analyze Bounding Box
def analyzebbox(bbox, intOrig, extentdistance):
    min = (bbox.Min.X, bbox.Min.Y, bbox.Min.Z)
    max = (bbox.Max.X, bbox.Max.Y, bbox.Max.Z)
    if calculate_distance(min, intOrig) > extentdistance or calculate_distance(max, intOrig) > extentdistance:
        Status = 0
    else:
        Status = 1
    return Status

#____________________________________________ Get ProjectBase and Survey Points
def get_project_base_and_survey_points(doc):
    basept = DB.BasePoint.GetProjectBasePoint(doc).Position
    basept_tuple = (basept.X, basept.Y, basept.Z)
    survpt = DB.BasePoint.GetSurveyPoint(doc).Position
    survpt_tuple = (survpt.X, survpt.Y, survpt.Z)
    intOrig = (0,0,0)
    return basept_tuple, survpt_tuple, intOrig

#____________________________________________ Get Design Options & Objects
def getalldesignoptionobjects(doc):
    dbobjs = []
    design_options = FilteredElementCollector(doc).OfClass(DesignOption).ToElements()
    for do in design_options:
        do_filter = ElementDesignOptionFilter(do.Id)
        x = FilteredElementCollector(doc).WherePasses(do_filter).ToElements()
        dbobjs.append(x)

    return design_options, dbobjs

#__________________________________________________________
#____________________________________________ MAIN FUNCTION
#__________________________________________________________

def check_model_extents(doc, output):
    #______________________________________________HTML Styles
    output = script.get_output()
    output.add_style('cover {color:black; font-size:24pt; font-weight:bold;}')
    output.add_style('header {color:black; font-size:15pt;}')
    stringseperator = "_________________________________________________________________________________________________"
    TestScore = 0
    #__________________________________________check the distnaces of base and survey points
    output.print_html('<cover>__________:satellite_antenna:__10-Mile Radar___________</cover>')
    print(stringseperator)
    print("")
    
    output.print_md('# Checking model placement and coordinates')
    print(stringseperator)
    intOrig = (0,0,0)
    basept, survpt, intOrig = get_project_base_and_survey_points(doc)
    baseptdistance = abs(calculate_distance(basept, intOrig))
    surveydistance = abs(calculate_distance(survpt, intOrig))
    if baseptdistance > extentdistance:
        output.print_md('### :thumbs_down_medium_skin_tone: ............Project Base Point is more than 10 miles (16KM) away from the Internal Origin.***')
    if surveydistance > extentdistance:
        output.print_md('### :thumbs_down_medium_skin_tone: ............Survey Point is more than 10 miles (16KM) away from the Internal Origin.***')
    else:
            output.print_md('### :OK_hand_medium_skin_tone: ............Survey Point is less than 10 miles (16KM) away from the Internal Origin.***')
    baseptdistance = calculate_distance(basept, intOrig)

    tabledata = [['InternaL Origin Coordinates', str(intOrig)], 
                  ['Project Base Point Coordinates', str(basept)], 
                  ['Survey Point Coordinates', str(survpt)],
                    ['Project Base Point Distance from Internal Origin', str(convert_units(doc, baseptdistance))],
                    ['Survey Point Distance from Internal Origin', str(convert_units(doc, surveydistance))],
                    ['Project Base Point to Survey Delta X', str(convert_units(doc, calculate_Horizontal_Distance(basept, survpt)[1]))],
                    ['Project Base Point to Survey Delta Y', str(convert_units(doc, calculate_Horizontal_Distance(basept, survpt)[2]))],
                    ['Horizontal Distance between Project Base Point and Survey Point', str(convert_units(doc, calculate_Horizontal_Distance(basept, survpt)[0]))],
                    ['Project Elevation', str(convert_units(doc, (survpt[2] - basept[2])))]]

    # Print Table
    output.print_table(table_data=tabledata, 
                       title='Project Coordinates and Distances',
                       columns=['Coordinates', 'Values'],
                       formats=['', ''])

    #__________________________________________Get the bounding box of the 3D view
    print("")
    output.print_md('# Checking the extents of the 3D view bounding box')
    bbox_instance = Get3DViewBoundingBox()
    bbox = bbox_instance.get_tempbbox(0,0,0,0)[0]
    min = (bbox.Min.X, bbox.Min.Y, bbox.Min.Z)
    max = (bbox.Max.X, bbox.Max.Y, bbox.Max.Z)
    print("")
    print(stringseperator)
    print("")
    if calculate_distance(min, intOrig) > extentdistance or calculate_distance(max, intOrig) > extentdistance:
        output.print_md('### :thumbs_down_medium_skin_tone: ............3D View Bounding Box extends more than 10 miles (16KM) away from the Internal Origin.***')
    else:
        output.print_md('### :OK_hand_medium_skin_tone: ............3D View Bounding Box is located less than 10 miles (16KM) away from the Internal Origin.***')
        TestScore += 1

    #__________________________________________Get Objects in Design Options
    print("")
    print(stringseperator)
    output.print_md('# Checking the extents of the design option objects')
    print(stringseperator)
    design_option_objects = getalldesignoptionobjects(doc)
    violating_design_option_objects = []
    violating_options = []
    for x in design_option_objects[1]:
        for y in x:
            dbbox = y.get_BoundingBox(None)
            if dbbox is None:
                continue
            else:
                dbmin = (dbbox.Min.X, dbbox.Min.Y, dbbox.Min.Z)
                dbmax = (dbbox.Max.X, dbbox.Max.Y, dbbox.Max.Z)
                if calculate_distance(dbmin, intOrig) > extentdistance or calculate_distance(dbmax, intOrig) > extentdistance:
                    violating_design_option_objects.append(x)
                    if y.DesignOption.Name not in violating_options:
                        violating_options.append(y.DesignOption.Name)
    if len(violating_design_option_objects) > 0:
        output.print_md('### :thumbs_down_medium_skin_tone: ............Design Option Objects are located more than 10 miles (16KM) away from the Internal Origin.***')
        if len(violating_design_option_objects) > 10:
            output.print_md('### :warning: ............Showing the first 10 objects***')
            output.print_md('### :warning: ............Manual investigation is required***')
        counter = 0
        limit = 10
        for x in violating_design_option_objects:

            for y in x:
                if counter == limit:
                    break
                print(output.linkify(y.Id)+ str(y.Name)+ " - Is part of design option - "+ str(y.DesignOption.Name) )
                counter += 1
    else:
        output.print_md('### :OK_hand_medium_skin_tone: ............No object in any design option is located more than 10 miles (16KM) away from the Internal Origin.***')
        TestScore += 1
    #__________________________________________Check Test Score
    if TestScore >= 2:
        output.print_md('### :OK_hand_medium_skin_tone: ............All Tests Passed.***')
        sys.exit()
    else:
        output.print_md('### :thumbs_down_medium_skin_tone: ............Distant objects detected, Proceeding with additional analysis')

    #__________________________________________Check CAD and RVT Links
    print(stringseperator)
    output.print_md('# Checking the extents of the CAD and RVT links')
    print(stringseperator)
    bboxLink = bbox_instance.get_tempbbox(1,1,1,0)
    badcads = bboxLink[1]
    badrvts = bboxLink[2]
    cleanbbox = bboxLink[3]
    # print (bboxLink[1], bboxLink[2])
    # print(bbox.Min, cleanbbox.Min)
    counter = 0
    limit = 5
    if len(badcads) > 0 or len(badrvts) > 0:
        for x in badcads:
            print(output.linkify(x.Id)+"__" + str(x.Name) + '  ' + str(x.Category.Name))
            if counter == limit:
                break
            counter += 1
        counter = 0
        for x in badrvts:
            print(output.linkify(x.Id)+"__" + str(x.Name) + '  ' + str(x.Category.Name))
            if counter == limit:
                break
            counter += 1
    else:
        output.print_md('### :OK_hand_medium_skin_tone: ............All CAD and RVT Links are located less than 10 miles (16KM) away from the Internal Origin.***')
        TestScore += 1
        print(stringseperator)
    if analyzebbox(cleanbbox, intOrig, 5) == 0:
        output.print_md('### :thumbs_down_medium_skin_tone: ............Distant objects are still being detected!')
        output.print_md('### :warning: ............Further Analysis Required.')
    else:
        output.print_md('### :OK_hand_medium_skin_tone: ............All Objects are located less than 10 miles (16KM) away from the Internal Origin.***')
        sys.exit()
    print(stringseperator)
    output.print_md('# Checking everything, It is going to take a while.')
    output.print_md('# Please be patient.')
    #__________________________________________Check Bounding Box of Every Element in the Model
    print(stringseperator)
    getbadelements = bbox_instance.get_tempbbox(0,0,0,1)
    badelements = getbadelements[4]
    counter = 0
    limit = 10
    if len(badelements) > 0:
        if len(badelements) > limit:
            output.print_md('### :warning: ............Showing the first 10 objects***')
            output.print_md('### :warning: ............Manual investigation is required***')
        output.print_md('### :thumbs_down_medium_skin_tone: ............Elements below are located more than 10 miles (16KM) away from the Internal Origin')
        for x in badelements:
            print(output.linkify(x.Id)+ '  ' + str(x.Name) + '  ' + str(x.Category.Name))
            if counter == limit:
                break
            counter += 1
    else:
        output.print_md('### :OK_hand_medium_skin_tone: ............All Objects are located less than 10 miles (16KM) away from the Internal Origin.***')
        TestScore += 1

#______________________________________________Model Checker Class

class ModelChecker(PreflightTestCase):
    """
    Checks the extents of all elements in the model.
This Model Checker swiftly verifies the extents of the Revit model. 
Placing model extents more than 10 miles (16KM) from the project's 
internal origin can lead to issues with accuracy, tolerance, 
performance, and viewport display. This check ensures that the 
model remains within a 10-mile radius of the internal origin.

The test case examines the following, reporting extents 
concerning the project's internal origin. The script prioritizes 
based on the assumption that most model extent issues are
related to the following:

        - The distance between project basepoint and internal origin
        - The distance between survey point and  internal origin
        - The bounding box of the 3D view
        - The bounding box of the design option objects
        - The bounding box of the CAD and RVT links
        - The bounding box of all elements in the model
    """

    name = "10 Mile Radar"
    author = "Tay Othman"

    def setUp(self, doc, output):
        pass

    def startTest(self, doc, output):
        check_model_extents(doc, output)

    def tearDown(self, doc, output):
        pass
    
    def doCleanups(self, doc, output):
        pass
