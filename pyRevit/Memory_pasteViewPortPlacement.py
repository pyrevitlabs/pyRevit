"""
Copyright (c) 2016 Gui Talarico

CopyPasteViewportPlacemenet
Copy and paste the placement of viewports across sheets
github.com/gtalarico | gtalarico@gmail.com

--------------------------------------------------------
pyRevit Notice:
pyRevit: repository at https://github.com/eirannejad/pyRevit

"""

__doc__ = 'Paste a Viewport Placement from memory'
__author__ = 'Gui Talarico | gtalarico@gmail.com'
__version__ = '0.1.0'

import os
import pickle
from tempfile import gettempdir
from collections import namedtuple

from Autodesk.Revit.DB import Transaction
from Autodesk.Revit.DB import Viewport, XYZ
from Autodesk.Revit.UI import TaskDialog

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

temp = os.path.join(gettempdir(), 'ViewPlacement')
Point = namedtuple('Point', ['X', 'Y', 'Z'])


selected_ids = uidoc.Selection.GetElementIds()

if selected_ids.Count == 1:
    for element_id in selected_ids:
        element = doc.GetElement(element_id)
        if isinstance(element, Viewport):
            try:
                with open(temp, 'rb') as fp:
                    pt = pickle.load(fp)
            except IOError:
                TaskDialog.Show('pyRevitPlus', 'Could not find saved viewport placement.\nCopy a Viewport Placement first.')
            else:
                saved_pt = XYZ(pt.X, pt.Y, pt.Z)
                t = Transaction(doc, 'Paste Viewport Placement')
                t.Start()
                element.SetBoxCenter(saved_pt)
                element.Pinned = True
                t.Commit()

else:
    TaskDialog.Show('pyRevitPlus', 'Select 1 Viewport. No more, no less!')

__window__.Close()
