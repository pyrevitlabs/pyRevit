"""Reload all xref CAD links."""

from Autodesk.Revit.DB import ModelPathUtils, TransmissionData, RevitLinkType, ElementType
import clr

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
# selection = [ doc.GetElement( elId ) for elId in __revit__.ActiveUIDocument.Selection.GetElementIds() ]

location = doc.PathName
try:
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
    transData = TransmissionData.ReadTransmissionData(modelPath)
    externalReferences = transData.GetAllExternalFileReferenceIds()
    for refId in externalReferences:
        extRef = transData.GetLastSavedReferenceData(refId)
        if 'CADLink' == str(extRef.ExternalFileReferenceType):
            link = doc.GetElement(refId)
            # link = clr.Convert( link, ElementType )
            path = ModelPathUtils.ConvertModelPathToUserVisiblePath(extRef.GetPath())
            if '' == path:
                path = '--NOT ASSIGNED--'
            print("Reloading...\n{0}{1}".format(str(str(extRef.ExternalFileReferenceType) + ':').ljust(20), path))
            # link.Reload()
            # print('Done\n')
            print('Sorry. Revit API does not have a CADLinkType.Reload method yet')
except:
    print('Model is not saved yet. Can not aquire location.')
