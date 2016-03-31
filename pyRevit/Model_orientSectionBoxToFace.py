'''
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
'''
__doc__ = 'Aligns the section box of the current 3D view to selected face.'

__window__.Close()
from Autodesk.Revit.DB import Transaction, View3D, SketchPlane, Plane, UV, XYZ, Transform
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.UI import TaskDialog

from System import Math

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

curview = doc.ActiveView

if isinstance( curview, View3D ) and curview.IsSectionBoxActive:
	ref = uidoc.Selection.PickObject( ObjectType.Face )
	el = doc.GetElement( ref.ElementId )
	face = el.GetGeometryObjectFromReference( ref )
	box = curview.GetSectionBox()
	norm = face.ComputeNormal( UV(0,0) ).Normalize()
	boxNormal = box.Transform.Basis[0].Normalize()
	angle = norm.AngleTo( boxNormal )
	axis = XYZ( 0, 0, 1.0 )
	origin = XYZ( box.Min.X + (box.Max.X - box.Min.X)/2 , box.Min.Y + (box.Max.Y - box.Min.Y)/2 , 0.0 )
	if norm.Y < boxNormal.X:
		rotate = Transform.CreateRotationAtPoint( axis, Math.PI/2 - angle, origin)
	else:
		rotate = Transform.CreateRotationAtPoint( axis, angle, origin)
	box.Transform  = box.Transform.Multiply( rotate )
	t = Transaction( doc, 'Orient Section Box to Face')
	t.Start()
	curview.SetSectionBox( box )
	uidoc.RefreshActiveView()
	t.Commit()
elif isinstance( curview, View3D ) and not curview.IsSectionBoxActive:
	TaskDialog.Show("pyRevit","The section box for View3D isn't active.")
else:
	TaskDialog.Show("pyRevit","You must be on a 3D view for this tool to work.")
