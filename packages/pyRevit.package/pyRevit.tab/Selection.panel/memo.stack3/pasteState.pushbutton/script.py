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

__doc__ = 'Applies the copied state to the active view. This works in conjunction with the copyState tool.'

import os
import os.path as op
import pickle
from collections import namedtuple

from Autodesk.Revit.DB import ElementId, TransactionGroup, Transaction, Viewport, ViewSheet, ViewPlan,          \
                              ViewDrafting, BoundingBoxXYZ, XYZ, View3D, ViewOrientation3D, BuiltInParameter,   \
                              FilteredElementCollector
from Autodesk.Revit.UI import TaskDialog

from System.Collections.Generic import List

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

__context__ = 'Selection'

import clr
clr.AddReferenceByPartialName('PresentationCore')
clr.AddReferenceByPartialName("PresentationFramework")
clr.AddReferenceByPartialName('System.Windows.Forms')
clr.AddReferenceByPartialName('WindowsBase')
import System.Windows


class BasePoint:
    def __init__(self):
        self.x = 0
        self.y = 0


class BBox:
    def __init__(self):
        self.minx = 0
        self.miny = 0
        self.minz = 0
        self.maxx = 0
        self.maxy = 0
        self.maxz = 0


class ViewOrient:
    def __init__(self):
        self.eyex = 0
        self.eyey = 0
        self.eyez = 0
        self.forwardx = 0
        self.forwardy = 0
        self.forwardz = 0
        self.upx = 0
        self.upy = 0
        self.upz = 0


class OriginalIsViewDrafting(Exception):
    pass


class OriginalIsViewPlan(Exception):
    pass


class TransformationMatrix:
    def __init__(self):
        self.sourcemin = None
        self.sourcemax = None
        self.destmin = None
        self.destmax = None


class commandSwitches:
    def __init__(self, switches, message = 'Pick a command option:'):
        # Create window
        self.my_window = System.Windows.Window()
        self.my_window.WindowStyle = System.Windows.WindowStyle.None
        self.my_window.AllowsTransparency = True
        self.my_window.Background = None
        self.my_window.Title = 'Command Options'
        self.my_window.Width = 600
        self.my_window.SizeToContent = System.Windows.SizeToContent.Height
        self.my_window.ResizeMode = System.Windows.ResizeMode.CanMinimize
        self.my_window.WindowStartupLocation = System.Windows.WindowStartupLocation.CenterScreen
        self.my_window.PreviewKeyDown += self.handleEsc
        border = System.Windows.Controls.Border()
        border.CornerRadius  = System.Windows.CornerRadius(15)
        border.Background = System.Windows.Media.SolidColorBrush(System.Windows.Media.Color.FromArgb(220,55,50,50))
        self.my_window.Content = border

        # Create StackPanel to Layout UI elements
        stack_panel = System.Windows.Controls.StackPanel()
        stack_panel.Margin = System.Windows.Thickness(5)
        border.Child = stack_panel

        label = System.Windows.Controls.Label()
        label.Foreground = System.Windows.Media.Brushes.White
        label.Content = message
        label.Margin = System.Windows.Thickness(2, 0, 0, 0)
        stack_panel.Children.Add(label)

        # Create WrapPanel for command options
        self.button_list = System.Windows.Controls.WrapPanel()
        self.button_list.Margin = System.Windows.Thickness(5)
        stack_panel.Children.Add(self.button_list)

        for switch in switches:
            my_button = System.Windows.Controls.Button()
            my_button.BorderBrush = System.Windows.Media.Brushes.Black
            my_button.BorderThickness = System.Windows.Thickness(0)
            my_button.Content = switch
            my_button.Margin = System.Windows.Thickness(5, 0, 5, 5)
            my_button.Padding = System.Windows.Thickness(5, 0, 5, 0)
            my_button.Click += self.processSwitch
            self.button_list.Children.Add(my_button)


    def handleEsc(self, sender, args):
        if (args.Key == System.Windows.Input.Key.Escape):
            self.my_window.Close()


    def processSwitch(self, sender, args):
        self.my_window.Close()
        global selected_switch
        selected_switch = sender.Content

    def pickCommandSwitch(self):
        self.my_window.ShowDialog()

selected_switch = ''
usertemp = os.getenv('Temp')
prjname = op.splitext(op.basename(doc.PathName))[0]

commandSwitches(['View Zoom/Pan State',
                 '3D Section Box State',
                 'Viewport Placement on Sheet',
                 'Visibility Graphics',
                 ], 'Select property to be applied to current view:').pickCommandSwitch()

if selected_switch == 'View Zoom/Pan State':
    datafile = usertemp + '\\' + prjname + '_pySaveRevitActiveViewZoomState.pym'
    try:
        f = open(datafile, 'r')
        p2 = pickle.load(f)
        p1 = pickle.load(f)
        f.close()
        vc1 = XYZ(p1.x, p1.y, 0)
        vc2 = XYZ(p2.x, p2.y, 0)
        av = uidoc.GetOpenUIViews()[0]
        av.ZoomAndCenterRectangle(vc1, vc2)
    except:
        __window__.Show()
        print('CAN NOT FIND ZOOM STATE FILE:\n{0}'.format(datafile))

elif selected_switch == '3D Section Box State':
    datafile = usertemp + '\\' + prjname + '_pySaveSectionBoxState.pym'

    try:
        f = open(datafile, 'r')
        sbox = pickle.load(f)
        vo = pickle.load(f)
        f.close()

        sb = BoundingBoxXYZ()
        sb.Min = XYZ(sbox.minx, sbox.miny, sbox.minz)
        sb.Max = XYZ(sbox.maxx, sbox.maxy, sbox.maxz)

        vor = ViewOrientation3D(XYZ(vo.eyex, vo.eyey, vo.eyez),
                                XYZ(vo.upx, vo.upy, vo.upz),
                                XYZ(vo.forwardx, vo.forwardy, vo.forwardz))

        av = uidoc.ActiveGraphicalView
        avui = uidoc.GetOpenUIViews()[0]
        if isinstance(av, View3D):
            with Transaction(doc, 'Paste Section Box Settings') as t:
                t.Start()
                av.SetSectionBox(sb)
                av.SetOrientation(vor)
                t.Commit()
            avui.ZoomToFit()
        else:
            TaskDialog.Show('pyrevit', 'You must be on a 3D view to paste Section Box settings.')
    except:
        TaskDialog.Show('pyrevit', 'Can not find any section box settings in memory:\n{0}'.format(datafile))

elif selected_switch == 'Viewport Placement on Sheet':
    """
    Copyright (c) 2016 Gui Talarico

    CopyPasteViewportPlacemenet
    Copy and paste the placement of viewports across sheets
    github.com/gtalarico | gtalarico@gmail.com

    --------------------------------------------------------
    pyrevit Notice:
    pyrevit: repository at https://github.com/eirannejad/pyrevit
    """
    PINAFTERSET = False
    Point = namedtuple('Point', ['X', 'Y','Z'])
    originalviewtype = ''

    selview = selvp = None
    vpboundaryoffset = 0.01
    activeSheet = uidoc.ActiveGraphicalView
    transmatrix = TransformationMatrix()
    revtransmatrix = TransformationMatrix()

    def sheet_to_view_transform(sheetcoord):
        global transmatrix
        newx = transmatrix.destmin.X + (
            ((sheetcoord.X - transmatrix.sourcemin.X) * (transmatrix.destmax.X - transmatrix.destmin.X)) / (
                transmatrix.sourcemax.X - transmatrix.sourcemin.X))
        newy = transmatrix.destmin.Y + (
            ((sheetcoord.Y - transmatrix.sourcemin.Y) * (transmatrix.destmax.Y - transmatrix.destmin.Y)) / (
                transmatrix.sourcemax.Y - transmatrix.sourcemin.Y))
        return XYZ(newx, newy, 0.0)


    def view_to_sheet_transform(modelcoord):
        global revtransmatrix
        newx = revtransmatrix.destmin.X + (
            ((modelcoord.X - revtransmatrix.sourcemin.X) * (revtransmatrix.destmax.X - revtransmatrix.destmin.X)) / (
                revtransmatrix.sourcemax.X - revtransmatrix.sourcemin.X))
        newy = revtransmatrix.destmin.Y + (
            ((modelcoord.Y - revtransmatrix.sourcemin.Y) * (revtransmatrix.destmax.Y - revtransmatrix.destmin.Y)) / (
                revtransmatrix.sourcemax.Y - revtransmatrix.sourcemin.Y))
        return XYZ(newx, newy, 0.0)


    def set_tansform_matrix(selvp, selview):
        # making sure the cropbox is active.
        cboxactive = selview.CropBoxActive
        cboxvisible = selview.CropBoxVisible
        cboxannoparam = selview.get_Parameter(BuiltInParameter.VIEWER_ANNOTATION_CROP_ACTIVE)
        cboxannostate = cboxannoparam.AsInteger()
        curviewelements = FilteredElementCollector(doc).OwnedByView(selview.Id).WhereElementIsNotElementType().ToElements()
        viewspecificelements = []
        for el in curviewelements:
            if  el.ViewSpecific                   \
                and (not el.IsHidden(selview))   \
                and el.CanBeHidden               \
                and el.Category != None:
                viewspecificelements.append(el.Id)

        with TransactionGroup(doc, 'Activate and Read Cropbox Boundary') as tg:
            tg.Start()
            with Transaction(doc, 'Hiding all 2d elements') as t:
                t.Start()
                if viewspecificelements:
                    for elid in viewspecificelements:
                        try:
                            selview.HideElements(List[ElementId](elid))
                        except:
                            pass
                t.Commit()

            with Transaction(doc, 'Activate and Read Cropbox Boundary') as t:
                t.Start()
                selview.CropBoxActive = True
                selview.CropBoxVisible = False
                cboxannoparam.Set(0)

                # get view min max points in modelUCS.
                modelucsx = []
                modelucsy = []
                crsm = selview.GetCropRegionShapeManager()

                cllist = crsm.GetCropShape()
                if len(cllist) == 1:
                    cl = cllist[0]
                    for l in cl:
                        modelucsx.append(l.GetEndPoint(0).X)
                        modelucsy.append(l.GetEndPoint(0).Y)
                    cropmin = XYZ(min(modelucsx), min(modelucsy), 0.0)
                    cropmax = XYZ(max(modelucsx), max(modelucsy), 0.0)

                    # get vp min max points in sheetUCS
                    ol = selvp.GetBoxOutline()
                    vptempmin = ol.MinimumPoint
                    vpmin = XYZ(vptempmin.X + vpboundaryoffset, vptempmin.Y + vpboundaryoffset, 0.0)
                    vptempmax = ol.MaximumPoint
                    vpmax = XYZ(vptempmax.X - vpboundaryoffset, vptempmax.Y - vpboundaryoffset, 0.0)

                    transmatrix.sourcemin = vpmin
                    transmatrix.sourcemax = vpmax
                    transmatrix.destmin = cropmin
                    transmatrix.destmax = cropmax

                    revtransmatrix.sourcemin = cropmin
                    revtransmatrix.sourcemax = cropmax
                    revtransmatrix.destmin = vpmin
                    revtransmatrix.destmax = vpmax

                    selview.CropBoxActive = cboxactive
                    selview.CropBoxVisible = cboxvisible
                    cboxannoparam.Set(cboxannostate)

                    if viewspecificelements:
                        selview.UnhideElements(List[ElementId](viewspecificelements))

                t.Commit()
            tg.Assimilate()

    datafile = usertemp + '\\' + prjname + '_pySaveViewportLocation.pym'

    selected_ids = uidoc.Selection.GetElementIds()

    if selected_ids.Count == 1:
        vport_id = selected_ids[0]
        try:
            vport = doc.GetElement(vport_id)
        except:
            TaskDialog.Show('pyrevit', 'Select at least one viewport. No more, no less!')
        if isinstance(vport, Viewport):
            view = doc.GetElement(vport.ViewId)
            if view is not None and isinstance(view, ViewPlan):
                with TransactionGroup(doc, 'Paste Viewport Location') as tg:
                    tg.Start()
                    set_tansform_matrix(vport, view)
                    try:
                        with open(datafile, 'rb') as fp:
                            originalviewtype = pickle.load(fp)
                            if originalviewtype == 'ViewPlan':
                                savedcen_pt = pickle.load(fp)
                                savedmdl_pt = pickle.load(fp)
                            else:
                                raise OriginalIsViewDrafting
                    except IOError:
                        TaskDialog.Show('pyrevit',
                                        'Could not find saved viewport placement.\nCopy a Viewport Placement first.')
                    except OriginalIsViewDrafting:
                        TaskDialog.Show('pyrevit',
                                        'Viewport placement info is from a drafting view and can not be applied here.')
                    else:
                        savedcenter_pt = XYZ(savedcen_pt.X, savedcen_pt.Y, savedcen_pt.Z)
                        savedmodel_pt = XYZ(savedmdl_pt.X, savedmdl_pt.Y, savedmdl_pt.Z)
                        with Transaction(doc, 'Apply Viewport Placement') as t:
                            t.Start()
                            center = vport.GetBoxCenter()
                            centerdiff = view_to_sheet_transform(savedmodel_pt) - center
                            vport.SetBoxCenter(savedcenter_pt - centerdiff)
                            if PINAFTERSET:
                                vport.Pinned = True
                            t.Commit()
                    tg.Assimilate()
            elif view is not None and isinstance(view, ViewDrafting):
                try:
                    with open(datafile, 'rb') as fp:
                        originalviewtype = pickle.load(fp)
                        if originalviewtype == 'ViewDrafting':
                            savedcen_pt = pickle.load(fp)
                        else:
                            raise OriginalIsViewPlan
                except IOError:
                    TaskDialog.Show('pyrevit',
                                    'Could not find saved viewport placement.\nCopy a Viewport Placement first.')
                except OriginalIsViewPlan:
                    TaskDialog.Show('pyrevit',
                                    'Viewport placement info is from a model view and can not be applied here.')
                else:
                    savedcenter_pt = XYZ(savedcen_pt.X, savedcen_pt.Y, savedcen_pt.Z)
                    with Transaction(doc, 'Apply Viewport Placement') as t:
                        t.Start()
                        vport.SetBoxCenter(savedcenter_pt)
                        if PINAFTERSET:
                            vport.Pinned = True
                        t.Commit()
            else:
                TaskDialog.Show('pyrevit', 'This tool only works with Plan, RCP, and Detail views and viewports.')
    else:
        TaskDialog.Show('pyrevit', 'Select at least one viewport. No more, no less!')

elif selected_switch == 'Visibility Graphics':
    datafile = usertemp + '\\' + prjname + '_pySaveVisibilityGraphicsState.pym'

    try:
        f = open(datafile, 'r')
        id = pickle.load(f)
        f.close()
        with Transaction(doc, 'Paste Visibility Graphics') as t:
            t.Start()
            uidoc.ActiveGraphicalView.ApplyViewTemplateParameters(doc.GetElement(ElementId(id)))
            t.Commit()
        __window__.Close()
    except:
        __window__.Show()
        print('CAN NOT FIND ANY VISIBILITY GRAPHICS SETTINGS IN MEMORY:\n{0}'.format(datafile))
