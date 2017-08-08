@echo off
REM When Revit is loaded, pyRevitLoader.dll is open by Revit instance and
REM git can not overwrite this core dll to the newest version.
REM This script will update pyRevit core to the newest version when
REM Revit is closed and all dlls are free.

REM Go back up one to repository root
cd ..
REM Save repo root
set current=%CD%
REM Pull (fetch and merge) the remote head
"%current%\release\pyrevitgitservices\pyrevitgitservices\bin\Release\pyrevitgitservices.exe" update "%current%"
REM cd back to script folder
cd /D %current%\release
echo Successfully updated pyRevit core. You can close this window now.
pause
exit
