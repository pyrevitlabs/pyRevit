from Autodesk.Revit.DB import Element, FilteredElementCollector, ImportInstance, ModelPathUtils,TransmissionData, Transaction, CADLinkType, RevitLinkType
import clr
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = list(__revit__.ActiveUIDocument.Selection.Elements)

location = doc.PathName
modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath( location )
transData = TransmissionData.ReadTransmissionData( modelPath )
externalReferences = transData.GetAllExternalFileReferenceIds()

cl = FilteredElementCollector( doc )
impInstances = list( cl.OfClass( clr.GetClrType( ImportInstance )).ToElements() )

imported = []

t = Transaction( doc, 'Remove All External Links' )
t.Start()

for refId in externalReferences:
	lnk = doc.GetElement( refId )
	extRef = transData.GetLastSavedReferenceData( refId )
	path = ModelPathUtils.ConvertModelPathToUserVisiblePath( extRef.GetPath() )
	if isinstance( lnk, RevitLinkType):
		print('REMOVED REF TO:{0}'.format( path ))
		doc.Delete( refId )
	elif isinstance( lnk, CADLinkType ):
		for inst in impInstances:
			if inst.IsLinked and inst.GetTypeId() == refId:
				print('REMOVED REF TO:{0}'.format( path ))
				doc.Delete( inst.Id )
			else:
				imported.append( inst )
	else:
		print('-SKIPPED: {0}'.format( path ))

for inst in imported:
	if not inst.IsLinked:
		impType = doc.GetElement( inst.GetTypeId() )
		print('-SKIPPED IMPORTED: {0}'.format( Element.Name.GetValue( impType )))


t.Commit()