cd /D %AppData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do del "%CD%\%%i\pyRevit.addin"
for /D %%i in (*.*) do del "%CD%\%%i\*pythonloader*.addin"

REG delete HKCU\Environment /F /V pyrevit 2>nul

cd /D %AppData%\pyRevit
del *.dll
del *.pickle
del *.json
del *.log