from Autodesk.Revit.DB import ModelPathUtils,TransmissionData
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = list(__revit__.ActiveUIDocument.Selection.Elements)

location = doc.PathName
modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath( location )
transData = TransmissionData.ReadTransmissionData( modelPath )
externalReferences = transData.GetAllExternalFileReferenceIds()
for refId in externalReferences:
	extRef = transData.GetLastSavedReferenceData( refId )
	if 'RevitLink' == str(extRef.ExternalFileReferenceType):
		link = doc.GetElement( refId )
		path = ModelPathUtils.ConvertModelPathToUserVisiblePath( extRef.GetPath() )
		if '' == path:
			path = '--NOT ASSIGNED--'
		print( "Reloading...\n{0}{1}".format( str( str( extRef.ExternalFileReferenceType )+':').ljust(20), path ))
		link.Reload()
		print('Done\n')