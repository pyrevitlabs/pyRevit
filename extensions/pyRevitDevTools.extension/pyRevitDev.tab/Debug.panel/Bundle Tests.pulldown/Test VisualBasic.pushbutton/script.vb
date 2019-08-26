Imports System
Imports Microsoft.VisualBasic

Imports Autodesk.Revit.UI
Imports Autodesk.Revit.DB

Imports PyRevitLabs.PyRevit.Runtime

Public Class HelloWorld
    Implements IExternalCommand

    Public execParams As ExecParams

    Public Function Execute(ByVal revit As ExternalCommandData, _
                            ByRef message As String, _
                            ByVal elements As ElementSet) As Autodesk.Revit.UI.Result _
                                Implements IExternalCommand.Execute
            Console.WriteLine(execParams.ScriptPath)

            MsgBox("Hello World from Visual Basic!!")
            TaskDialog.Show(execParams.CommandName, "Hello World from Visual Basic!!")
            TaskDialog.Show(execParams.CommandName, execParams.ScriptPath)

            If execParams.ConfigMode Then
                TaskDialog.Show(execParams.CommandName, "Command is in Config Mode!")
            End If

            If execParams.DebugMode Then
                TaskDialog.Show(execParams.CommandName, "Command is in Debug Mode!")
            End If

            Console.WriteLine(":thumbs_up:")

            Return Autodesk.Revit.UI.Result.Succeeded
    End Function
End Class
