REM When Revit is loaded, pyRevitLoader.dll is open by Revit instance and
REM git can not overwrite this core dll to the newest version.
REM This script will update pyRevit core to the newest version when
REM Revit is closed and all dlls are free.

REM Go back up one to repository root
cd ..
REM Save repo root
set current=%CD%
REM Pull (fetch and merge) the remote head
cd %current%\release\pyRevitCoreUpdater\pyRevitCoreUpdater\bin\Release\pyRevitCoreUpdater.exe %current%
REM cd back to script folder
cd %current%\release
