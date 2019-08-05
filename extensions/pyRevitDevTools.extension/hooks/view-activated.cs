// executor needs to find the correct function signature and executes that
using System;
using System.IO;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;


namespace MyEvents {
    public static class MyEventMgr {
        public static void MyEventMgr_UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
            File.AppendAllText(
                Path.Combine(desktopPath, "hooks.log"),
                string.Format("[view-activate-csharp] doc:\"{0}\" active_view:\"{1}\" prev_view:\"{2}\" status:\"{3}\"",
                    e.Document.ToString(),
                    e.CurrentActiveView.ToString(),
                    e.PreviousActiveView.ToString(),
                    e.Status.ToString()
                )
            );
        }
    }
}