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
