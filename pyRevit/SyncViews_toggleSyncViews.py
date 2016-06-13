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

__doc__ = 'Keep views synchronized.'

import os
import os.path as op
import pickle as pl
import clr
clr.AddReference('PresentationCore')

from System import EventHandler
from Autodesk.Revit.DB import ElementId, XYZ, ViewPlan
from Autodesk.Revit.UI.Events import ViewActivatedEventArgs, ViewActivatingEventArgs

from System import Uri
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption

from Autodesk.Revit.UI import PulldownButton, SplitButton, RadioButtonGroup


class Point:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

# todo: sync views - 3D


class ButtonIcon:
    def __init__(self, uri):
        self.smallIcon = BitmapImage()
        self.smallIcon.BeginInit()
        self.smallIcon.UriSource = uri
        self.smallIcon.CacheOption = BitmapCacheOption.OnLoad
        self.smallIcon.DecodePixelHeight = 16
        self.smallIcon.DecodePixelWidth = 16
        self.smallIcon.EndInit()
        self.largeIcon = BitmapImage()
        self.largeIcon.BeginInit()
        self.largeIcon.UriSource = uri
        self.largeIcon.CacheOption = BitmapCacheOption.OnLoad
        self.largeIcon.EndInit()


class ToggleButtonIcons:
    def __init__(self, scriptfulladdress):
        enableduri = Uri(scriptfulladdress.replace('.py', 'ON.png'))
        disableduri = Uri(scriptfulladdress.replace('.py', 'OFF.png'))
        self.enabledIcon = ButtonIcon(enableduri)
        self.disabledIcon = ButtonIcon(disableduri)


def findribbonsubitem(ribbonitem, itemname):
    for item in ribbonitem.GetItems():
        if isinstance(item, PulldownButton) or isinstance(item, SplitButton) or isinstance(item, RadioButtonGroup):
            item = findribbonsubitem(item, itemname)
            if item:
                return item
        elif item.Name == itemname:
            return item


def getcommandbutton(__rvt__, scriptaddress):
    scriptname= op.splitext(op.basename(scriptaddress))[0]
    tabname = op.basename(op.dirname(scriptaddress))
    itemname = tabname + scriptname.split('_')[0] + scriptname.split('_')[1]
    ribbonpanels = __rvt__.GetRibbonPanels(tabname)
    for panel in ribbonpanels:
        item = findribbonsubitem(panel, itemname)
        if item:
            return item


def copyzoomstate(sender, args):
    usertemp = os.getenv('Temp')
    if op.isfile(op.join(usertemp, 'syncviewsactive.pys')):
        eventuidoc = sender.ActiveUIDocument
        eventdoc = sender.ActiveUIDocument.Document
        auiviews = eventuidoc.GetOpenUIViews()
        curuiview = None
        for aview in auiviews:
            if aview.ViewId == args.CurrentActiveView.Id:
                curuiview = aview

        if isinstance(args.CurrentActiveView, ViewPlan):
            prjname = op.splitext(op.basename(eventdoc.PathName))[0]
            datafile = usertemp + '\\' + prjname + '_pySyncRevitActiveViewZoomState.pym'

            cornerlist = curuiview.GetZoomCorners()

            vc1 = cornerlist[0]
            vc2 = cornerlist[1]
            p1 = Point()
            p2 = Point()
            p1.x = vc1.X
            p1.y = vc1.Y
            p2.x = vc2.X
            p2.y = vc2.Y

            f = open(datafile, 'w')
            pl.dump(p1, f)
            pl.dump(p2, f)
            f.close()


def applyzoomstate(sender, args):
    usertemp = os.getenv('Temp')
    if op.isfile(op.join(usertemp, 'syncviewsactive.pys')):
        eventuidoc = sender.ActiveUIDocument
        eventdoc = sender.ActiveUIDocument.Document
        auiviews = eventuidoc.GetOpenUIViews()
        curuiview = None
        for aview in auiviews:
            if aview.ViewId == args.CurrentActiveView.Id:
                curuiview = aview

        if isinstance(args.CurrentActiveView, ViewPlan):
            prjname = op.splitext(op.basename(eventdoc.PathName))[0]
            datafile = usertemp + '\\' + prjname + '_pySyncRevitActiveViewZoomState.pym'
            f = open(datafile, 'r')
            p2 = pl.load(f)
            p1 = pl.load(f)
            f.close()
            vc1 = XYZ(p1.x, p1.y, 0)
            vc2 = XYZ(p2.x, p2.y, 0)
            curuiview.ZoomAndCenterRectangle(vc1, vc2)


def togglestate():
    usertemp = os.getenv('Temp')
    activestatefile = op.join(usertemp, 'syncviewsactive.pys')
    inactivestatefile = op.join(usertemp, 'syncviewsinactive.pys')

    commandbutton = getcommandbutton(__revit__, __file__)
    icon = ToggleButtonIcons(__file__)

    if op.isfile(activestatefile):
        os.rename(activestatefile, inactivestatefile)
        commandbutton.Image = icon.disabledIcon.smallIcon
        commandbutton.LargeImage = icon.disabledIcon.largeIcon
    elif op.isfile(inactivestatefile):
        os.rename(inactivestatefile, activestatefile)
        commandbutton.Image = icon.enabledIcon.smallIcon
        commandbutton.LargeImage = icon.enabledIcon.largeIcon
    else:
        open(activestatefile, 'a').close()
        commandbutton.Image = icon.enabledIcon.smallIcon
        commandbutton.LargeImage = icon.enabledIcon.largeIcon


def clearstate():
    usertemp = os.getenv('Temp')
    activestatefile = op.join(usertemp, 'syncviewsactive.pys')
    inactivestatefile = op.join(usertemp, 'syncviewsinactive.pys')
    if op.isfile(activestatefile):
        os.rename(activestatefile, inactivestatefile)
    else:
        open(inactivestatefile, 'a').close()


def selfInit(__rvt__, scriptaddress, commandbutton):
    clearstate()
    __revit__.ViewActivating += EventHandler[ViewActivatingEventArgs](copyzoomstate)
    __revit__.ViewActivated += EventHandler[ViewActivatedEventArgs](applyzoomstate)
    icon = ToggleButtonIcons(scriptaddress)
    commandbutton.Image = icon.disabledIcon.smallIcon
    commandbutton.LargeImage = icon.disabledIcon.largeIcon

if __name__ == '__main__':
    __window__.Close()
    togglestate()
