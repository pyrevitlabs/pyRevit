'''
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
'''

__doc__ = 'Site Designer has a bug that duplicates its standard line styles. This script will disable the Add-in.'

import os
import os.path as op
from System import AppDomain

assmName = 'SiteDesigner'

def findAssembly( assemblyName ):
		alist = []
		for loadedAssembly in AppDomain.CurrentDomain.GetAssemblies():
			if assemblyName in loadedAssembly.FullName:
				alist.append( loadedAssembly )
		return alist

def disableAddin( assm ):
	assmLoc = op.dirname( assm.Location )
	files = os.listdir( assmLoc )
	atLeastOneDisabled = False
	for f in files:
		if f.endswith( '.addin' ):
			fname = op.join( assmLoc, f )
			newfname = op.join( assmLoc, f.replace( '.addin', '.addin.bak' ))
			os.rename( fname, newfname )
			print('Addin description file renamed:\n{0}'.format( newfname ))
			atLeastOneDisabled = True
	if atLeastOneDisabled:
		print('ADDIN SUCCESSFULLY DISABLED.')
	else:
		print('--- Disabling unsuccessful for:\n{0}'.format( op.join( assmLoc, f )))


assmList = findAssembly( assmName )

if len(assmList) > 1:
	print('Multiple assemblies found:\n{0}\n\nAttemping disabling all...'.format( assmList ))
	for i, a in enumerate( assmList ):
		print('\n\n{0}: {1}'.format( i, a.GetName().Name ))
		if not a.IsDynamic:
			disableAddin( a )
		else:
			print('Can not disable dynamic assembly...')

elif len(assmList) == 1:
	assm = assmList[0]
	if not assm.IsDynamic:
		print('Assembly found:\n{0}\nAttemping disabling...'.format( assm.GetName().Name ))
		disableAddin( assm )
	else:
		print('Can not disable dynamic assembly...')
else:
	print('Can not find addin: {0}'.format( assmName ))



