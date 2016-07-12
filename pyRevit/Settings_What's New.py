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

__doc__ = 'List the new tools added under each revision. This is the official revision history for pyRevit.'

__window__.Width = 900

import platform as pl

print('''
Version 2.40.4
-------------------------------------------------------------------------------
-   Settings > What's New
        Added a button to list all the tools added from now on.

-   Sheets > setCropRegionToSelectedShape
        Draw the desired crop boundary as a polygon on your sheet (using detail lines).
        Then select the bounday and the destination viewport and run the script.
        This script will apply the drafted boundary to the view of the selected viewport.

-   Minor cleanups

Version 2.43.46
-------------------------------------------------------------------------------
-   WorkSharing > listSheetsWithElementsOwnedByMe
        Lists all sheets containing elements currently "owned" by the user.
        "Owned" elements are the elements by the user since the last synchronize and release.

-   WorkSharing > selectLastEditedByMeInCurrentView
        Uses the Worksharing tooltip to find out the element "last edited" by the user in the current view.
        If current view is a sheet, the tools searches all the views placed on this sheet as well.
        "Last Edited" elements are elements last edited by the user, and are different from borrowed elements.

-   WorkSharing > selectOwnedByMeInCurrentView
        Uses the Worksharing tooltip to find out the element "owned" by the user in the current view.
        If current view is a sheet, the tools searches all the views placed on this sheet as well.
        "Owned" elements are the elements edited by the user since the last synchronize and release.

-   Added extended tooltip notes to buttons listing class and assembly name.
-   Minor cleanups

Version 2.45.51
-------------------------------------------------------------------------------
-   Revised findReferencingSheets to find referencing sheets for schedules as well.

-   Select > selectAllMirroredDoors
        Selects all mirrored doors in the model.

-   Views > removeUnderlayFromSelectedViews
        Removes Underlay from selected views.

-   Misc changes

Version 2.46.51 (current)
-------------------------------------------------------------------------------
-   Analyse > Analyse_calculateAverageArea.py
        Find all Rooms//Areas//Spaces with identical names and calcualts the average area of that space type.

-   Misc changes

''')
