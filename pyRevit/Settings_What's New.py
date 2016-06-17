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

__doc__ = 'List the new tools added under each revision.'


import platform as pl

print('''
Version 2.40.44
-------------------------------------------------------------------------------
-	Settings > What's New
	Added a button to list all the tools added from now on.

-	Sheets > setCropRegionToSelectedShape
	Draw the desired crop boundary as a polygon on your sheet (using detail lines).
	Then select the bounday and the destination viewport and run the script.
	This script will apply the drafted boundary to the view of the selected viewport.

-	Minor cleanups
''')
