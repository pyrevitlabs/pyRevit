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

__doc__ = 'Clear memory and Append current selection. Works like the M+ button in a calculator. ' \
          'This is a project-dependent (Revit *.rvt) memory. Every project has its own memory saved in ' \
          'user temp folder as *.pym files.'

# from Autodesk.Revit.DB import ElementId
import os
import os.path as op
import pickle as pl

from scriptutils import this_script
from revitutils import uidoc

__context__ = 'Selection'

datafile = this_script.get_document_data_file(0, "pym", command_name="SelList")

selection = {elId.ToString() for elId in uidoc.Selection.GetElementIds()}

f = open(datafile, 'w')
pl.dump(selection, f)
f.close()
