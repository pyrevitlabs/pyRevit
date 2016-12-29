cd %AppData%\Autodesk\Revit\Addins
for /D %%i in (*.*) do del "%CD%\%%i\pyRevit.addin"

test