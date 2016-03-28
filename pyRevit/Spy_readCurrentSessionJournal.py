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

# __window__.Close()
import os, subprocess
import os.path as op
appdataFolder = os.getenv('localappdata')
journalsFolder = op.join( appdataFolder, 'Autodesk\\Revit\\Autodesk Revit {0}\\Journals'.format( __revit__.Application.VersionNumber ))
os.chdir(journalsFolder)
journalFiles = [x for x in os.listdir( journalsFolder ) if op.splitext(x)[1].lower() == '.txt']
newest = max( journalFiles, key=op.getctime )
with open( newest, 'r') as f:
	print f.read()