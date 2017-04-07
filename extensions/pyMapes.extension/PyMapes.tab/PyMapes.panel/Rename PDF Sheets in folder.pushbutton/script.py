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

__doc__ = 'Renames PDF sheets printed from Revit and removes the Central model name from the PDF names. The PDF files must be on desktop.'

import os, sys
import os.path as op
from Autodesk.Revit.UI import TaskDialog

__window__.Close()

basefolder = op.expandvars('%userprofile%\Desktop\Bluebeam Plots')
sheetcount = 0


def alert(msg):
    TaskDialog.Show('pyMapes', msg)


def renamePDF(pdffile):
    import re
    r = re.compile('(?<=Sheet - )(.+)')
    fname = r.findall(pdffile)[0]
    r = re.compile('(.+)\s-\s(.+)')
    fnameList = r.findall(fname)
    return fnameList[0][0] + ' - ' + fnameList[0][1].upper()


# for dirname, dirnames, filenames in os.walk( basefolder ):
filenames = os.listdir(basefolder)
for pdffile in filenames:
    ext = op.splitext(pdffile)[1].upper()
    if ext == '.PDF' and ('Sheet' in pdffile):
        newfile = renamePDF(pdffile)
        try:
            os.rename(op.join(basefolder, pdffile), op.join(basefolder, newfile))
            sheetcount += 1
        except Exception as e:
            print("Unexpected error:", sys.exc_info()[0])

alert('{0} FILES RENAMED. Your Bluebeam Plots folder will now open. Have a Great Day!'.format(sheetcount))

import os
os.system('explorer "%userprofile%\Desktop\Bluebeam Plots"')

