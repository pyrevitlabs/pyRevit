REM Remove all manifest files
cd /D %ProgramData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do del "%CD%\%%i\pyRevit.addin"
cd /D %AppData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do del "%CD%\%%i\pyRevit.addin"
for /D %%i in (*.*) do del "%CD%\%%i\*pythonloader*.addin"

REM Remove the legacy registery entry
REG delete HKCU\Environment /F /V pyrevit 2>nul

REM Clear all cache files
cd /D %AppData%\pyRevit
del *.dll
del *.pickle
del *.json
del *.log
