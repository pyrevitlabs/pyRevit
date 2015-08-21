'''
exportImage.py
Export the currently visible view as a PNG image to a location specified by the user.
'''

import clr
clr.AddReference('RevitAPI')
clr.AddReference('RevitAPIUI')
from Autodesk.Revit.DB import *

doc = __revit__.ActiveUIDocument.Document

# collect file location from user
clr.AddReference('System.Windows.Forms')
from System.Windows.Forms import DialogResult, SaveFileDialog
dialog = SaveFileDialog()
dialog.Title = 'Export current view as PNG'
dialog.Filter = 'PNG files (*.PNG)|*.PNG'

if dialog.ShowDialog() == DialogResult.OK:
	# set up the export options
	options = ImageExportOptions()
	options.ExportRange = ExportRange.VisibleRegionOfCurrentView
	options.FilePath = dialog.FileName
	options.HLRandWFViewsFileType = ImageFileType.PNG
	options.ImageResolution = ImageResolution.DPI_72
	options.ZoomType = ZoomFitType.Zoom
	options.ShadowViewsFileType = ImageFileType.PNG

	doc.ExportImage(options)

__window__.Close()
