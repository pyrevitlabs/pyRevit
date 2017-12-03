"""Reloads all linked Revit models."""

from pyrevit import HOST_APP
from pyrevit import revit, DB, UI
from pyrevit import forms


def reload_links(linktype=DB.ExternalFileReferenceType.RevitLink):
    location = revit.doc.PathName
    try:
        modelPath = \
            DB.ModelPathUtils.ConvertUserVisiblePathToModelPath(location)

        transData = DB.TransmissionData.ReadTransmissionData(modelPath)

        externalReferences = transData.GetAllExternalFileReferenceIds()
        for refId in externalReferences:
            extRef = transData.GetLastSavedReferenceData(refId)
            if extRef.ExternalFileReferenceType == \
                    DB.ExternalFileReferenceType.RevitLink:
                link = revit.doc.GetElement(refId)
                path = \
                    DB.ModelPathUtils.ConvertModelPathToUserVisiblePath(
                        extRef.GetPath()
                        )

                if not path:
                    path = '--NOT ASSIGNED--'

                fref = str(extRef.ExternalFileReferenceType) + ':'
                print("Reloading...\n{0}{1}".format(fref, path))
                link.Reload()
                print('Done\n')
    except Exception:
        forms.alert('Model is not saved yet. Can not acquire location.')


linktypes = {'Revit Links': DB.ExternalFileReferenceType.RevitLink,
             'Keynote Table': DB.ExternalFileReferenceType.KeynoteTable,
             'Images': DB.ExternalFileReferenceType.Decal}

if HOST_APP.is_newer_than(2017):
    linktypes['CAD Links'] = DB.ExternalFileReferenceType.CADLink

selected_option = \
    forms.CommandSwitchWindow.show(linktypes.keys(),
                                   message='Select link type:')

if selected_option:
    reload_links(linktypes[selected_option])
