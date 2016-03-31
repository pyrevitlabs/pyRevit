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

'''	Rename Revit output PDFs on user desktop to remove the project name from file name.'''

__doc__ = 'Renames PDF sheets printed from Revit and removed the Central model name from the PDF names. The PDF files must be on desktop.'

import os, sys
import os.path as op
from Autodesk.Revit.UI import TaskDialog

__window__.Close()

basefolder = op.expandvars('%userprofile%\\desktop')
sheetcount = 0

def alert(msg):
	TaskDialog.Show('pyRevit', msg)

def renamePDF( file ):
	import re
	r = re.compile('(?<=Sheet - )(.+)')
	fname = r.findall(file)[0]
	r = re.compile('(.+)\s-\s(.+)')
	fnameList= r.findall(fname)
	return fnameList[0][0] + ' - ' + fnameList[0][1].upper()

# for dirname, dirnames, filenames in os.walk( basefolder ):
filenames = os.listdir( basefolder )
for file in filenames:
	ext = op.splitext(file)[1].upper()
	if ext == '.PDF' and ('Sheet' in file):
		newfile = renamePDF(file)
		try:
			os.rename( op.join( basefolder, file ), op.join( basefolder, newfile ))
			sheetcount+=1
		except:
			print("Unexpected error:", sys.exc_info()[0])

alert('{0} FILES RENAMED.'.format(sheetcount))