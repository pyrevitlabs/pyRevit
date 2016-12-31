"""
Copyright (c) 2014-2017 Ehsan Iran-Nejad
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

__doc__ = 'Removes all external links from current project. This obviously will delete all their instances.'

from Autodesk.Revit.DB import Element, FilteredElementCollector, ImportInstance, ModelPathUtils, TransmissionData, \
    Transaction, CADLinkType, RevitLinkType, ElementId
import clr

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

tobeDeleted = set()

try:
    location = doc.PathName
    modelPath = ModelPathUtils.ConvertUserVisiblePathToModelPath(location)
    transData = TransmissionData.ReadTransmissionData(modelPath)
    externalReferences = transData.GetAllExternalFileReferenceIds()

    cl = FilteredElementCollector(doc)
    impInstances = list(cl.OfClass(clr.GetClrType(ImportInstance)).ToElements())

    for refId in externalReferences:
        lnk = doc.GetElement(refId)
        extRef = transData.GetLastSavedReferenceData(refId)
        path = ModelPathUtils.ConvertModelPathToUserVisiblePath(extRef.GetPath())
        if isinstance(lnk, RevitLinkType):
            print('REMOVING REVIT LINK\nID: {1}\tADDRESS: {0}\n'.format(path, refId))
            # tobeDeleted.append( refId )
            tobeDeleted.add(lnk.Id.IntegerValue)
        elif isinstance(lnk, CADLinkType):
            for inst in impInstances:
                if inst.GetTypeId() == refId and not inst.IsLinked:
                    impType = doc.GetElement(inst.GetTypeId())
                    print('--- SKIPPING IMPORTED INSTANCE ---\n{0}'.format(Element.Name.GetValue(impType)))
                elif inst.GetTypeId() == refId and inst.IsLinked:
                    print('REMOVING CAD LINK\nID: {1}\tADDRESS: {0}\n'.format(path, refId))
                    tobeDeleted.add(lnk.Id.IntegerValue)
        else:
            print('--- SKIPPING NON REVIT OR CAD LINK ---\nTYPE: {1} ADDRESS: {0}\n'.format(path, str(
                extRef.ExternalFileReferenceType).ljust(20)))
except:
    print('Model is not saved yet. Can not aquire location.')

t = Transaction(doc, 'Remove All External Links')
t.Start()
for elid in tobeDeleted:
    try:
        doc.Delete(ElementId(elid))
    except Exception as e:
        print(e)
t.Commit()
print('ALL DONE............')
