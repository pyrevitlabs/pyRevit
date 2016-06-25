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

__doc__ = 'Lists all Extensible Storage schemas loaded in memory.'

# from Autodesk.Revit.DB import FilteredElementCollector, LinePatternElement
from Autodesk.Revit.DB.ExtensibleStorage import Schema

uidoc = __revit__.ActiveUIDocument
doc = __revit__.ActiveUIDocument.Document

for sc in Schema.ListSchemas():
    print('\n' + '-' * 100)
    print('SCHEMA NAME: {0}'
          '\tGUID:               {6}\n'
          '\tDOCUMENTATION:      {1}\n'
          '\tVENDOR ID:          {2}\n'
          '\tAPPLICATION GUID:   {3}\n'
          '\tREAD ACCESS LEVEL:  {4}\n'
          '\tWRITE ACCESS LEVEL: {5}'.format(sc.SchemaName,
                                             sc.Documentation,
                                             sc.VendorId,
                                             sc.ApplicationGUID,
                                             sc.ReadAccessLevel,
                                             sc.WriteAccessLevel,
                                             sc.GUID
                                             ))
    if sc.ReadAccessGranted():
        for fl in sc.ListFields():
            print('\t\tFIELD NAME: {0}\n'
                  '\t\t\tDOCUMENTATION:      {1}\n'
                  '\t\t\tCONTAINER TYPE:     {2}\n'
                  '\t\t\tKEY TYPE:           {3}\n'
                  '\t\t\tUNIT TYPE:          {4}\n'
                  '\t\t\tVALUE TYPE:         {5}\n'.format(fl.FieldName,
                                                           fl.Documentation,
                                                           fl.ContainerType,
                                                           fl.KeyType,
                                                           fl.UnitType,
                                                           fl.ValueType
                                                           ))
