from Autodesk.Revit.DB import ModelPathUtils
doc = __revit__.ActiveUIDocument.Document

if doc.GetWorksharingCentralModelPath():
	print(ModelPathUtils.ConvertModelPathToUserVisiblePath(doc.GetWorksharingCentralModelPath()))
else:
	print("Model is not work-shared.")