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

__doc__ = 'Lists all standard postable commands with their Ids in Revit.'


__window__.Width = 1000
from Autodesk.Revit.UI import PostableCommand, RevitCommandId

for pc in PostableCommand.GetValues(PostableCommand):
    try:
        rcid = RevitCommandId.LookupPostableCommandId(pc)
        if rcid:
            print('{0} {1} {2}'.format(str(pc).ljust(50), str(rcid.Name).ljust(70), rcid.Id))
        else:
            print('{0}'.format(str(pc).ljust(50)))
    except:
        print('{0}'.format(str(pc).ljust(50)))
