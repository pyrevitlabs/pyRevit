"""
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
"""

__doc__ = 'Report the username of whoever reloaded the keynotes last.'

__window__.Hide()
from Autodesk.Revit.DB import ModelPathUtils, TransmissionData, ExternalFileReferenceType, BuiltInParameter
from Autodesk.Revit.UI import TaskDialog

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

location = doc.PathName
if doc.IsWorkshared:
    try:
        modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
        transData = TransmissionData.ReadTransmissionData(modelPath)
        externalReferences = transData.GetAllExternalFileReferenceIds()
        for refId in externalReferences:
            extRef = transData.GetLastSavedReferenceData(refId)
            path = ModelPathUtils.ConvertModelPathToUserVisiblePath(extRef.GetPath())
            if extRef.ExternalFileReferenceType == ExternalFileReferenceType.KeynoteTable and '' != path:
                ktable = doc.GetElement(extRef.GetReferencingId())
                editedByParam = ktable.Parameter[BuiltInParameter.EDITED_BY]
                if editedByParam and editedByParam.AsString() != '':
                    TaskDialog.Show('pyrevit', 'Keynote table has been reloaded by:\n{0}\nTable Id is: {1}'.format(
                        editedByParam.AsString(), ktable.Id))
                else:
                    TaskDialog.Show('pyrevit',
                                    'No one own the keynote table. You can make changes and reload.\n'
                                    'Table Id is: {0}'.format(ktable.Id))
    except Exception as e:
        __window__.Show()
        print('Model is not saved yet. Can not aquire keynote file location.')
        print(e)
else:
    TaskDialog.Show('pyrevit', 'Model is not workshared.')

__window__.Close()
