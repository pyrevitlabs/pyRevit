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

__doc__ = 'Exports the current view to a 600DPI PNG image.'

__window__.Close()
import clr

clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import DialogResult, SaveFileDialog
from Autodesk.Revit.DB import ImageExportOptions, ExportRange, ImageFileType, ImageResolution, ZoomFitType

doc = __revit__.ActiveUIDocument.Document

# collect file location from user
dialog = SaveFileDialog()
dialog.Title = 'Export current view as PNG'
dialog.Filter = 'PNG files (*.PNG)|*.PNG'

if dialog.ShowDialog() == DialogResult.OK:
    # set up the export options
    options = ImageExportOptions()
    options.ExportRange = ExportRange.VisibleRegionOfCurrentView
    options.FilePath = dialog.FileName
    options.HLRandWFViewsFileType = ImageFileType.PNG
    options.ImageResolution = ImageResolution.DPI_600
    options.ZoomType = ZoomFitType.Zoom
    options.ShadowViewsFileType = ImageFileType.PNG

    doc.ExportImage(options)
