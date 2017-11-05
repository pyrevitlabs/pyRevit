"""Report the username of whoever reloaded the keynotes last."""

from pyrevit import revit, DB, UI

location = revit.doc.PathName
if revit.doc.IsWorkshared:
    try:
        modelPath = \
            DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
        transData = DB.TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        for refId in externalReferences:
            extRef = transData.GetLastSavedReferenceData(refId)
            path = DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
                extRef.GetPath()
                )

            if extRef.ExternalFileReferenceType == \
                    DB.ExternalFileReferenceType.KeynoteTable \
                    and '' != path:
                ktable = revit.doc.GetElement(extRef.GetReferencingId())
                editedByParam = ktable.Parameter[DB.BuiltInParameter.EDITED_BY]
                if editedByParam and editedByParam.AsString() != '':
                    UI.TaskDialog.Show('pyrevit',
                                       'Keynote table has been reloaded by:\n'
                                       '{0}\nTable Id is: {1}'
                                       .format(editedByParam.AsString(),
                                               ktable.Id))
                else:
                    UI.TaskDialog.Show('pyrevit',
                                       'No one own the keynote table. '
                                       'You can make changes and reload.\n'
                                       'Table Id is: {0}'.format(ktable.Id))
    except Exception as e:
        UI.TaskDialog.Show('pyrevit',
                           'Model is not saved yet. '
                           'Can not aquire keynote file location.')
else:
    UI.TaskDialog.Show('pyrevit', 'Model is not workshared.')
