"""
Copyright (c) 2014-2017 PyMapes
Python scripts for Autodesk Revit

you can redistribute it and/or modify
it under the terms of the GNU General Public License version 3, as published by
the Free Software Foundation.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

"""

__doc__ = 'Opens keynote source file used in this model.'

from Autodesk.Revit.DB import FilteredElementCollector, ElementMulticategoryFilter, BuiltInCategory, Element, ElementType, \
    GraphicsStyle, LinePatternElement, SketchPlane, View,\
                              ViewSheet, ModelArc, ModelLine, DetailArc, DetailLine, LogicalOrFilter, ModelPathUtils, \
                              TransmissionData, InstanceBinding, TypeBinding, FilteredWorksetCollector, \
                              WorksetKind
import os

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document
location = doc.PathName

try:
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
    transData = TransmissionData.ReadTransmissionData(modelPath)
    externalReferences = transData.GetAllExternalFileReferenceIds()

    for refId in externalReferences:
        extRef = transData.GetLastSavedReferenceData(refId)
        path = ModelPathUtils.ConvertModelPathToUserVisiblePath(extRef.GetPath())
        if '' == path:
            path = '--NOT ASSIGNED--'
        print(path(1))
except:
    print("pyMapes is opening Key note file located at " + (path) + " Have a Nice Day!")

kn_path = path

os.system('start winword "{0}"'.format(kn_path))









