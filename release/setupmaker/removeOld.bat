cd %AppData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do del "%CD%\%%i\*pythonloader*.addin"

REG delete HKCU\Environment /F /V pyrevit 2>nul
