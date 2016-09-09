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

__doc__ = 'Exports all original imported images to user desktop.'

import os.path as op
from Autodesk.Revit.DB import FilteredElementCollector, Element, ImageType

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
selection = [doc.GetElement(elId) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds()]

destDir = op.expandvars('%userprofile%\\desktop')

cl = FilteredElementCollector(doc)
list = cl.OfClass(ImageType).ToElements()

for el in list:
    image = el.GetImage()
    imageName = op.basename(el.Path)
    # imageName = Element.Name.GetValue( el )
    print('EXPORTING: {0}'.format(imageName))
    image.Save(op.join(destDir, imageName))
