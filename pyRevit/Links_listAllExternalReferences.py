from Autodesk.Revit.DB import ModelPathUtils,TransmissionData
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

location = doc.PathName
try:
	modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath( location )
	transData = TransmissionData.ReadTransmissionData( modelPath )
	externalReferences = transData.GetAllExternalFileReferenceIds()
	for refId in externalReferences:
		extRef = transData.GetLastSavedReferenceData( refId )
		path = ModelPathUtils.ConvertModelPathToUserVisiblePath( extRef.GetPath() )
		if '' == path:
			path = '--NOT ASSIGNED--'
		print( "{0}{1}".format( str( str( extRef.ExternalFileReferenceType )+':').ljust(20), path ))
except:
	print('Model is not saved yet. Can not aquire location.')