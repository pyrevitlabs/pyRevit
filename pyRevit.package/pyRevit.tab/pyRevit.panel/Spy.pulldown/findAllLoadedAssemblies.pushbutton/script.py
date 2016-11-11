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

__doc__ = 'List all currently loaded assemblies'

from System import AppDomain

__window__.Width = 1500

userScriptsAssemblies = []
for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
    loc = ''
    if 'pyRevit' in loadedAssembly.FullName:
        userScriptsAssemblies.append(loadedAssembly)
        continue
    try:
        loc = loadedAssembly.Location
    except:
        pass
    print('\n{0}{1}{2}'.format(loadedAssembly.GetName().Name.ljust(50),
                               str(loadedAssembly.GetName().Version).ljust(20),
                               loc
                               ))
    try:
        print('External Applications:')
        print([x.FullName for x in loadedAssembly.GetTypes() if x.GetInterface("IExternalApplication") is not None])
    except:
        pass
    try:
        print('External Commands:')
        print([x.FullName for x in loadedAssembly.GetTypes() if x.GetInterface("IExternalCommand") is not None])
    except:
        pass

print('\n\nPYREVIT ASSEMBLIES:')
for loadedAssembly in userScriptsAssemblies:
    loc = ''
    try:
        loc = loadedAssembly.Location
    except:
        pass
    print('{0}{1}{2}'.format(loadedAssembly.GetName().Name.ljust(50),
                             str(loadedAssembly.GetName().Version).ljust(20),
                             loc
                             ))
    try:
        print('External Commands:')
        print([x.FullName for x in loadedAssembly.GetTypes() if x.GetInterface("IExternalCommand") is not None])
        print('\n')
    except:
        pass
