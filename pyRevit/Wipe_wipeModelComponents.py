"""
Copyright (c) 2014-2016 Ehsan Iran-Nejad
Python scripts for Autodesk Revit

This file is part of pyRevit repository at https://github.com/eirannejad/pyRevit

pyRevit is a free set of scripts for Autodesk Revit: you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

See this link for a copy of the GNU General Public License protecting this package.
https://github.com/eirannejad/pyRevit/blob/master/LICENSE
"""

__window__.Hide()

import clr
import StringIO

clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
import System.Windows

from Autodesk.Revit.DB import *
from Autodesk.Revit.UI import TaskDialog, TaskDialogCommonButtons, TaskDialogResult

outputs = StringIO.StringIO()
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document


class purgeWindow:
    def __init__(self):
        # Initialization Constants
        Window = System.Windows.Window
        Application = System.Windows.Application
        Button = System.Windows.Controls.Button
        StackPanel = System.Windows.Controls.StackPanel
        Label = System.Windows.Controls.Label
        Thickness = System.Windows.Thickness
        Checkbox = System.Windows.Controls.CheckBox

        # Create window
        my_window = Window()
        my_window.Title = 'Purge Model'
        my_window.Width = 400
        my_window.Height = 410

        # Create StackPanel to Layout UI elements
        my_stack = StackPanel()
        my_stack.Margin = Thickness(15)
        my_window.Content = my_stack

        promptLabel = Label()
        promptLabel.Content = 'Select categories to be purged:'
        my_stack.AddChild(promptLabel)

        self.systemWindow = my_window

        self.explodeAndRemoveAllGroupsCheckBox = Checkbox()
        self.explodeAndRemoveAllGroupsCheckBox.Content = 'Explode And Remove All Groups'
        self.explodeAndRemoveAllGroupsCheckBox.IsChecked = True

        self.removeAllExternalLinksCheckBox = Checkbox()
        self.removeAllExternalLinksCheckBox.Content = 'Remove All External Links'
        self.removeAllExternalLinksCheckBox.IsChecked = False

        self.removeAllConstraintsCheckBox = Checkbox()
        self.removeAllConstraintsCheckBox.Content = 'Remove All Constraints'
        self.removeAllConstraintsCheckBox.IsChecked = True

        self.removeAllRoomsCheckBox = Checkbox()
        self.removeAllRoomsCheckBox.Content = 'Remove All Rooms'
        self.removeAllRoomsCheckBox.IsChecked = False

        self.removeAllAreasCheckBox = Checkbox()
        self.removeAllAreasCheckBox.Content = 'Remove All Areas'
        self.removeAllAreasCheckBox.IsChecked = True

        self.removeAllScopeBoxesCheckBox = Checkbox()
        self.removeAllScopeBoxesCheckBox.Content = 'Remove All Scope Boxes'
        self.removeAllScopeBoxesCheckBox.IsChecked = True

        self.removeAllSheetsCheckBox = Checkbox()
        self.removeAllSheetsCheckBox.Content = 'Remove All Sheets (Except for sheets currently open)'
        self.removeAllSheetsCheckBox.IsChecked = True

        self.removeAllViewsCheckBox = Checkbox()
        self.removeAllViewsCheckBox.Content = 'Remove All Views (Except for views currently open)'
        self.removeAllViewsCheckBox.IsChecked = True

        self.removeAllViewTemplatesCheckBox = Checkbox()
        self.removeAllViewTemplatesCheckBox.Content = 'Remove All View Templates'
        self.removeAllViewTemplatesCheckBox.IsChecked = True

        self.removeAllFiltersCheckBox = Checkbox()
        self.removeAllFiltersCheckBox.Content = 'Remove All Filters'
        self.removeAllFiltersCheckBox.IsChecked = True

        self.removeAllMaterialsCheckBox = Checkbox()
        self.removeAllMaterialsCheckBox.Content = 'Remove All Materials'
        self.removeAllMaterialsCheckBox.IsChecked = False

        self.callPurgeCommandCheckbox = Checkbox()
        self.callPurgeCommandCheckbox.Content = 'Call Revit "Purge Unused" after completion.'
        self.callPurgeCommandCheckbox.Margin = Thickness(40, 10, 30, 0)
        self.callPurgeCommandCheckbox.IsChecked = True

        my_stack.AddChild(self.explodeAndRemoveAllGroupsCheckBox)
        my_stack.AddChild(self.removeAllExternalLinksCheckBox)
        my_stack.AddChild(self.removeAllConstraintsCheckBox)
        my_stack.AddChild(self.removeAllRoomsCheckBox)
        my_stack.AddChild(self.removeAllAreasCheckBox)
        my_stack.AddChild(self.removeAllScopeBoxesCheckBox)
        my_stack.AddChild(self.removeAllSheetsCheckBox)
        my_stack.AddChild(self.removeAllViewsCheckBox)
        my_stack.AddChild(self.removeAllViewTemplatesCheckBox)
        my_stack.AddChild(self.removeAllFiltersCheckBox)
        my_stack.AddChild(self.removeAllMaterialsCheckBox)

        # Create Button and add a Button Click event handler
        my_button_checkAll = Button()
        my_button_checkAll.Content = 'Check All'
        my_button_checkAll.Margin = Thickness(30, 10, 30, 0)
        my_stack.Children.Add(my_button_checkAll)

        my_button_checkNone = Button()
        my_button_checkNone.Content = 'Check None'
        my_button_checkNone.Margin = Thickness(30, 10, 30, 0)
        my_stack.Children.Add(my_button_checkNone)

        my_button_purge = Button()
        my_button_purge.Content = 'Purge Model'
        my_button_purge.Margin = Thickness(0, 20, 0, 0)
        my_stack.Children.Add(my_button_purge)

        my_button_checkAll.Click += self.checkAllAction
        my_button_checkNone.Click += self.checkNoneAction
        my_button_purge.Click += self.purgeProcess

        my_stack.AddChild(self.callPurgeCommandCheckbox)

    def purgeProcess(self, sender, args):
        if doc.GetWorksharingCentralModelPath():
            centralPath = ModelPathUtils.ConvertModelPathToUserVisiblePath(doc.GetWorksharingCentralModelPath())
            res = TaskDialog.Show('pyRevit',
                                  'The central model is located at:\n {0}\n\nAre you sure you want to wipe?'.format(
                                      centralPath), TaskDialogCommonButtons.Yes | TaskDialogCommonButtons.Cancel)
            if res == TaskDialogResult.Cancel:
                __window__.Close()
                return

        self.systemWindow.Hide()
        __window__.Show()
        report('\n\n')
        report('                                PRINTING FULL REPORT', title=True)
        report('\n\n')
        tg = TransactionGroup(doc, "Purge Model for GC")
        tg.Start()

        if self.removeAllExternalLinksCheckBox.IsChecked:
            removeAllExternalLinks()
        if self.removeAllRoomsCheckBox.IsChecked:
            removeAllRooms()
            removeAllRoomSeparationLines()
        if self.removeAllAreasCheckBox.IsChecked:
            removeAllAreas()
            removeAllAreaSeparationLines()
        if self.explodeAndRemoveAllGroupsCheckBox.IsChecked:
            explodeAndRemoveAllGroups()
        if self.removeAllScopeBoxesCheckBox.IsChecked:
            removeAllScopeBoxes()
        if self.removeAllConstraintsCheckBox.IsChecked:
            removeAllConstraints()
        if self.removeAllSheetsCheckBox.IsChecked:
            removeAllSheets()
        if self.removeAllViewsCheckBox.IsChecked:
            removeAllViews()
            removeAllElevationMarkers()
        if self.removeAllViewTemplatesCheckBox.IsChecked:
            removeAllViewTemplates()
        if self.removeAllFiltersCheckBox.IsChecked:
            removeAllFilters()
        if self.removeAllMaterialsCheckBox.IsChecked:
            removeAllMaterials()

        tg.Commit()
        self.systemWindow.Close()

        if self.callPurgeCommandCheckbox.IsChecked:
            from Autodesk.Revit.UI import PostableCommand as pc
            from Autodesk.Revit.UI import RevitCommandId as rcid
            cid_PurgeUnused = rcid.LookupPostableCommandId(pc.PurgeUnused)
            __revit__.PostCommand(cid_PurgeUnused)

        print(outputs.getvalue())

    def checkNoneAction(self, sender, args):
        self.explodeAndRemoveAllGroupsCheckBox.IsChecked = False
        self.removeAllExternalLinksCheckBox.IsChecked = False
        self.removeAllConstraintsCheckBox.IsChecked = False
        self.removeAllRoomsCheckBox.IsChecked = False
        self.removeAllAreasCheckBox.IsChecked = False
        self.removeAllScopeBoxesCheckBox.IsChecked = False
        self.removeAllSheetsCheckBox.IsChecked = False
        self.removeAllViewsCheckBox.IsChecked = False
        self.removeAllViewTemplatesCheckBox.IsChecked = False
        self.removeAllFiltersCheckBox.IsChecked = False
        self.removeAllMaterialsCheckBox.IsChecked = False

    def checkAllAction(self, sender, args):
        self.explodeAndRemoveAllGroupsCheckBox.IsChecked = True
        self.removeAllExternalLinksCheckBox.IsChecked = True
        self.removeAllConstraintsCheckBox.IsChecked = True
        self.removeAllRoomsCheckBox.IsChecked = True
        self.removeAllAreasCheckBox.IsChecked = True
        self.removeAllScopeBoxesCheckBox.IsChecked = True
        self.removeAllSheetsCheckBox.IsChecked = True
        self.removeAllViewsCheckBox.IsChecked = True
        self.removeAllViewTemplatesCheckBox.IsChecked = True
        self.removeAllFiltersCheckBox.IsChecked = True
        self.removeAllMaterialsCheckBox.IsChecked = True

    def showAndPurge(self):
        self.systemWindow.ShowDialog()


def report(message, title=False):
    if title:
        outputs.write('-' * 88 + '\n' + message + '\n' + '-' * 88)
    else:
        outputs.write(message)
        outputs.write('\n')


def reportAndPrint(message):
    print(message)
    outputs.write(message)
    outputs.write('\n')


def reportAndPrintError(elType='', elId=0, exception=None):
    print('< ERROR DELETING ELEMENT > ID: {0}\tTYPE: {1}'.format(elId, elType))
    outputs.write('< ERROR DELETING ELEMENT > ID: {0}\tTYPE: {1}\n'.format(elId, elType))
    if exception:
        print('EXCEPTION: {0}'.format(exception))
        outputs.write('EXCEPTION: {0}\n'.format(exception))


def removeAllConstraints():
    t = Transaction(doc, 'Remove All Constraints')
    t.Start()
    reportAndPrint('------------------------------- REMOVING ALL CONSTRAINTS -------------------------------\n')
    cl = FilteredElementCollector(doc)
    clconst = list(cl.OfCategory(BuiltInCategory.OST_Constraints).WhereElementIsNotElementType())
    for cnst in clconst:
        if cnst.View is not None:
            try:
                doc.Delete(cnst.Id)
            except Exception as e:
                reportAndPrintError('Constraint', cnst.Id, e)
                continue
    t.Commit()


def explodeAndRemoveAllGroups():
    t = Transaction(doc, 'Remove All Groups')
    t.Start()
    reportAndPrint('---------------------------- EXPLODING AND REMOVING GROUPS -----------------------------\n')
    # grpTypesDetail = list( FilteredElementCollector( doc ).OfCategory( BuiltInCategory.OST_IOSDetailGroups ) )
    # grpTypesModel = list( FilteredElementCollector( doc ).OfCategory( BuiltInCategory.OST_IOSModelGroups ) )
    grpTypes = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(GroupType)).ToElementIds())
    groups = list(FilteredElementCollector(doc).OfClass(clr.GetClrType(Group)).ToElements())

    # ungroup all groups
    for grp in groups:
        grp.UngroupMembers()

    # delete group types
    for gtid in grpTypes:
        gtype = doc.GetElement(gtid)
        if gtype:
            if gtype.Category.Name != 'Attached Detail Groups':
                try:
                    doc.Delete(gtid)
                except Exception as e:
                    reportAndPrintError('Group Type', None, e)
                    continue
    t.Commit()


def removeAllExternalLinks():
    t = Transaction(doc, 'Remove All External Links')
    t.Start()
    reportAndPrint('------------------------------ REMOVE ALL EXTERNAL LINKS -------------------------------\n')
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
                reportAndPrintError('External Link', refId, e)
                continue
    else:
        reportAndPrintError('Model must be saved for external links to be removed.')
    t.Commit()


def removeAllSheets():
    t = Transaction(doc, 'Remove All Sheets')
    t.Start()
    reportAndPrint('----------------------------------- REMOVING SHEETS ------------------------------------\n')
    cl = FilteredElementCollector(doc)
    sheets = cl.OfCategory(BuiltInCategory.OST_Sheets).WhereElementIsNotElementType().ToElements()
    openUIViews = uidoc.GetOpenUIViews()
    openViews = [x.ViewId.IntegerValue for x in openUIViews]
    for s in sheets:
        if s.Id.IntegerValue in openViews:
            continue
        else:
            try:
                report('{2}{0}  {1}'.format(s.LookupParameter('Sheet Number').AsString().rjust(10),
                                            s.LookupParameter('Sheet Name').AsString().ljust(50), s.Id))
                doc.Delete(s.Id)
            except Exception as e:
                reportAndPrintError('Sheet', s.Id, e)
                continue
    t.Commit()


def removeAllRooms():
    t = Transaction(doc, 'Remove All Rooms')
    t.Start()
    reportAndPrint('----------------------------------- REMOVING ROOMS -------------------------------------\n')
    cl = FilteredElementCollector(doc)
    rooms = cl.OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType().ToElements()
    for r in rooms:
        try:
            report('{2}{1}{0}'.format(
                r.LookupParameter('Name').AsString().ljust(30),
                r.LookupParameter('Number').AsString().ljust(20),
                r.Id
            ))
            doc.Delete(r.Id)
        except Exception as e:
            reportAndPrintError('Room', r.Id, e)
            continue
    t.Commit()


def removeAllAreas():
    t = Transaction(doc, 'Remove All Areas')
    t.Start()
    reportAndPrint('----------------------------------- REMOVING AREAS -------------------------------------\n')
    cl = FilteredElementCollector(doc)
    areas = cl.OfCategory(BuiltInCategory.OST_Areas).WhereElementIsNotElementType().ToElements()
    for a in areas:
        try:
            report('{2}{1}{0}'.format(
                a.ParametersMap['Name'].AsString().ljust(30),
                a.ParametersMap['Number'].AsString().ljust(10),
                a.Id))
            doc.Delete(a.Id)
        except Exception as e:
            reportAndPrintError('Area', a.Id, e)
            continue
    t.Commit()


def removeAllRoomSeparationLines():
    t = Transaction(doc, 'Remove All Room Separation Lines')
    t.Start()
    reportAndPrint('------------------------- REMOVING ROOM SEPARATIONS LINES ------------------------------\n')
    cl = FilteredElementCollector(doc)
    rslines = cl.OfCategory(BuiltInCategory.OST_RoomSeparationLines).WhereElementIsNotElementType().ToElements()
    for line in rslines:
        try:
            # report('ID: {0}'.format( line.Id ))
            doc.Delete(line.Id)
        except Exception as e:
            reportAndPrintError('Room Separation Line', line.Id, e)
            continue
    t.Commit()


def removeAllAreaSeparationLines():
    t = Transaction(doc, 'Remove All Area Separation Lines')
    t.Start()
    reportAndPrint('------------------------- REMOVING AREA SEPARATIONS LINES ------------------------------\n')
    cl = FilteredElementCollector(doc)
    aslines = cl.OfCategory(BuiltInCategory.OST_AreaSchemeLines).WhereElementIsNotElementType().ToElements()
    for line in aslines:
        try:
            # report('ID: {0}'.format( line.Id ))
            doc.Delete(line.Id)
        except Exception as e:
            reportAndPrintError('Area Separation Line', line.Id, e)
            continue
    t.Commit()


def removeAllScopeBoxes():
    t = Transaction(doc, 'Remove All ScopeBoxes')
    t.Start()
    reportAndPrint('------------------------------- REMOVING SCOPE BOXES -----------------------------------\n')
    cl = FilteredElementCollector(doc)
    scopeboxes = cl.OfCategory(BuiltInCategory.OST_VolumeOfInterest).WhereElementIsNotElementType().ToElements()
    for s in scopeboxes:
        try:
            report('ID: {0}'.format(s.Id))
            doc.Delete(s.Id)
        except Exception as e:
            reportAndPrintError('Scope Box', s.Id)
            continue
    t.Commit()


def removeAllMaterials():
    t = Transaction(doc, 'Remove All Materials')
    t.Start()
    reportAndPrint('-------------------------------- REMOVING MATERIALS ------------------------------------\n')
    cl = FilteredElementCollector(doc)
    mats = cl.OfCategory(BuiltInCategory.OST_Materials).WhereElementIsNotElementType().ToElements()
    for m in mats:
        if 'poche' in m.Name.lower():
            continue
        try:
            # report('ID: {0}'.format( m.Id ))
            doc.Delete(m.Id)
        except Exception as e:
            reportAndPrintError('Material', m.Id, e)
            continue
    t.Commit()


def removeAllViews():
    t = Transaction(doc, 'Remove All Views')
    t.Start()
    reportAndPrint('---------------------- REMOVING VIEWS / LEGENDS / SCHEDULES ----------------------------\n')
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
                report('{2}{1}{0}'.format(v.ViewName.ljust(50), str(v.ViewType).ljust(15), str(v.Id).ljust(10)))
                try:
                    doc.Delete(v.Id)
                except Exception as e:
                    reportAndPrintError('View', v.Id, e)
                    continue
    t.Commit()


def removeAllViewTemplates():
    t = Transaction(doc, 'Remove All View Templates')
    t.Start()
    reportAndPrint('---------------------------- REMOVING VIEW TEMPLATES -----------------------------------\n')
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
                report('{2}{1}{0}'.format(v.ViewName.ljust(50), str(v.ViewType).ljust(15), str(v.Id).ljust(10)))
                try:
                    doc.Delete(v.Id)
                except Exception as e:
                    reportAndPrintError('View Template', v.Id, e)
                    continue
    t.Commit()


def removeAllElevationMarkers():
    t = Transaction(doc, 'Remove All Elevation Markers')
    t.Start()
    reportAndPrint('---------------------------- REMOVING ELEVATION MARKERS --------------------------------\n')
    cl = FilteredElementCollector(doc)
    elevMarkers = cl.OfClass(ElevationMarker).WhereElementIsNotElementType().ToElements()
    for em in elevMarkers:
        try:
            # report('ID: {0}'.format( em.Id ))
            doc.Delete(em.Id)
        except Exception as e:
            reportAndPrintError('Elevation Marker', em.Id, e)
            continue
    t.Commit()


def removeAllFilters():
    t = Transaction(doc, 'Remove All Filters')
    t.Start()
    reportAndPrint('------------------------------- REMOVING ALL FILTERS -----------------------------------\n')
    cl = FilteredElementCollector(doc)
    filters = cl.OfClass(FilterElement).WhereElementIsNotElementType().ToElements()
    for f in filters:
        try:
            report('ID: {0}'.format(f.Id))
            doc.Delete(f.Id)
        except Exception as e:
            reportAndPrintError('View Filter', f.Id, e)
            continue
    t.Commit()


purgeWindow().showAndPurge()
