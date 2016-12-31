cd /D %~dp0
cd ..
set installpath=%CD%
cd /D %AppData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do (
echo Adding addin description file to Revit %%i...
(
echo ^<?xml version="1.0" encoding="utf-8" standalone="no"?^>
echo ^<RevitAddIns^>
echo   ^<AddIn Type="Application"^>
echo     ^<Name^>PyRevitLoader^</Name^>
echo     ^<Assembly^>%installpath%\pyrevitlib\pyrevit\loader\addin\PyRevitLoader.dll^</Assembly^>
echo     ^<AddInId^>B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D^</AddInId^>
echo     ^<FullClassName^>PyRevitLoader.PyRevitLoaderApplication^</FullClassName^>
echo   ^<VendorId^>eirannejad^</VendorId^>
echo   ^</AddIn^>
echo ^</RevitAddIns^>
) > "%CD%\%%i\pyRevit.addin"
)