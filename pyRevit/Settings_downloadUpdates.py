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

import os.path as op
import subprocess as sp

def getParentDirectory( path ):
	return op.split( op.dirname( path ))[0]

cloneDir = getParentDirectory( __file__ )
gitDir = op.dirname( cloneDir )

print('Parent directory is: {0}'.format( cloneDir ))
print('git package is located at: {0}'.format( gitDir ))
print('\nUpdating pyRevit from github repository...')
if op.exists( '{0}\git\cmd\git.exe'.format( gitDir ) ):
	output = sp.check_output(r'{0}\git\cmd\git.exe pull'.format( gitDir ), cwd = cloneDir, shell=True )
	print( output )
else:
	print('Can not find portable git package.')