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
xcopy /Y/S "%current%\release\pyrevitgitservices\pyrevitgitservices\bin\Release" "%temp%\pyrevitgitservices\" >NUL
"%temp%\pyrevitgitservices\pyrevitgitservices.exe" update "%current%"
REM cd back to script folder
cd /D %current%\release

REM Run the addin fixers
cmd /c uninstall_addin.bat
cmd /c install_addin.bat

echo You can close this window now.
pause
exit
