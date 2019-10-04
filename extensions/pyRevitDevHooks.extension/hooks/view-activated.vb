Imports System
Imports System.IO
Imports Microsoft.VisualBasic

Imports Autodesk.Revit.UI
Imports Autodesk.Revit.UI.Events
Imports Autodesk.Revit.DB

Public Class MyEventMgr
    Public Sub MyEventMgr_UiApp_ViewActivated(sender As Object, e As ViewActivatedEventArgs)
        File.AppendAllText(
             Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "hooks.log"),
                     String.Format("00000000000000000 [view-activated-vb] doc:""{0}"" active_view:""{1}"" prev_view:""{2}"" status:""{3}""" + Environment.NewLine,
                                   If(e.Document IsNot Nothing, e.Document.ToString(), ""),
                                   If(e.CurrentActiveView IsNot Nothing, e.CurrentActiveView.ToString(), ""),
                                   If(e.PreviousActiveView IsNot Nothing, e.PreviousActiveView.ToString(), ""),
                                   e.Status.ToString()))
    End Sub
End Class