' Imports System
' Imports System.IO

' Imports Autodesk.Revit.UI
' Imports Autodesk.Revit.UI.Events
' Imports Autodesk.Revit.DB

' Public Static Class MyEventMgr
'     Public Static Function MyEventMgr_UiApp_ViewActivated(sender As Object, e As ViewActivatedEventArgs)
'         File.AppendAllText(
'             Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Desktop), "hooks.log"),
'             String.Format("00000000000000000 [view-activated-vb] doc:""{0}"" active_view:""{1}"" prev_view:""{2}"" status:""{3}""\n",
'                           If(e.Document IsNot Nothing, e.Document.ToString(), ""),
'                           If(e.CurrentActiveView IsNot Nothing, e.CurrentActiveView.ToString(), ""),
'                           If(e.PreviousActiveView IsNot Nothing, e.PreviousActiveView.ToString(), ""),
'                           e.Status.ToString()))
'     End Function
' End Class