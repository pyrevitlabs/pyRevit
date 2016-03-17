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

from Autodesk.Revit.DB import Element, FilteredElementCollector, ImportInstance, ModelPathUtils,TransmissionData, Transaction, CADLinkType, RevitLinkType
import clr
uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

location = doc.PathName
try:
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
except:
	print('Model is not saved yet. Can not aquire location.')