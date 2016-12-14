cd %AppData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do (
echo Adding addin description file to Revit %%i...
(
echo ^<?xml version="1.0" encoding="utf-8" standalone="no"?^>
echo ^<RevitAddIns^>
echo   ^<AddIn Type="Application"^>
echo     ^<Name^>RevitPythonLoader^</Name^>
echo     ^<Assembly^>%1^</Assembly^>
echo     ^<AddInId^>B39107C3-A1D7-47F4-A5A1-532DDF6EDB5D^</AddInId^>
echo     ^<FullClassName^>RevitPythonLoader.RevitPythonLoaderApplication^</FullClassName^>
echo   ^<VendorId^>eirannejad^</VendorId^>
echo   ^</AddIn^>
echo ^</RevitAddIns^>
) > "%CD%\%%i\pyRevit.addin"
)