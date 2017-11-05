"""Reload all xref CAD links."""

from pyrevit import revit, DB, UI


location = revit.doc.PathName

try:
    modelPath = DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
    transData = DB.TransmissionData.ReadTransmissionData(modelPath)
    externalReferences = transData.GetAllExternalFileReferenceIds()
    for refId in externalReferences:
        extRef = transData.GetLastSavedReferenceData(refId)
        if 'CADLink' == str(extRef.ExternalFileReferenceType):
            link = revit.doc.GetElement(refId)
            # link = clr.Convert( link, ElementType )
            path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
                extRef.GetPath()
                )

            if '' == path:
                path = '--NOT ASSIGNED--'

            fref = str(str(extRef.ExternalFileReferenceType) + ':').ljust(20)
            print("Reloading...\n{0}{1}".format(fref, path))

            # link.Reload()
            # print('Done\n')
            print('Sorry. Revit API does not have a reload method yet')
except Exception:
    UI.TaskDialog.Show('pyRevit',
                       'Model is not saved yet. Can not aquire location.')
