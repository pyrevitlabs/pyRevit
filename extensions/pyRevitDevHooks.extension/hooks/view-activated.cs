// executor needs to find the correct function signature and executes that
using System;
using System.IO;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;


namespace MyEvents {
    public class MyEventMgr {
        public void TestArgsType(object sender, Autodesk.Revit.UI.Events.ViewActivatingEventArgs e) {
            TaskDialog.Show("Hooks", "Selected incorrect method");
        }

        public void MyEventMgr_UiApp_ViewActivated(object sender, Autodesk.Revit.UI.Events.ViewActivatedEventArgs e) {
            string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
            File.AppendAllText(
                Path.Combine(desktopPath, "hooks.log"),
                string.Format("00000000000000000 [view-activated-csharp] doc:\"{0}\" active_view:\"{1}\" prev_view:\"{2}\" status:\"{3}\"\n",
                    e.Document != null ? e.Document.ToString() : "",
                    e.CurrentActiveView != null ? e.CurrentActiveView.ToString() : "",
                    e.PreviousActiveView != null ? e.PreviousActiveView.ToString() : "",
                    e.Status.ToString()
                )
            );
        }
    }
}