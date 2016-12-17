"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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
import os
import os.path as op
import pickle as pl
import clr

import scriptutils

clr.AddReference('PresentationCore')

# noinspection PyUnresolvedReferences
from System import EventHandler, Uri
# noinspection PyUnresolvedReferences
from Autodesk.Revit.DB import ElementId, XYZ, ViewPlan
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI.Events import ViewActivatedEventArgs, ViewActivatingEventArgs
# noinspection PyUnresolvedReferences
from System.Windows.Media.Imaging import BitmapImage, BitmapCacheOption
# noinspection PyUnresolvedReferences
from Autodesk.Revit.UI import PulldownButton, SplitButton, RadioButtonGroup


__doc__ = 'Keep views synchronized. This means that as you pan and zoom and switch between Plan and RCP views, this ' \
          'tool will keep the views in the same zoomed area so you can keep working in the same area without '        \
          'the need to zoom and pan again.\n This tool works best when the views are maximized.'


class Point:
    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y


# todo: sync views - 3D


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



def __selfinit__(script_cmp, commandbutton, __rvt__):
    __rvt__.ViewActivating += EventHandler[ViewActivatingEventArgs](copyzoomstate)
    __rvt__.ViewActivated += EventHandler[ViewActivatedEventArgs](applyzoomstate)


if __name__ == '__main__':
    togglestate()
