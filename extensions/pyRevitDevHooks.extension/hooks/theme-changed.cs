// executor needs to find the correct function signature and executes that
using System;
using System.IO;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;


namespace MyEvents {
    public class MyEventMgr {

        public void MyEventMgr_UiApp_ThemeChanged(object sender, Autodesk.Revit.UI.Events.ThemeChangedEventArgs e) {
            string desktopPath = Environment.GetFolderPath(Environment.SpecialFolder.Desktop);
            File.AppendAllText(
                Path.Combine(desktopPath, "hooks.log"),
                string.Format("00000000000000000 [theme-changed-csharp] doc:\"{0}\" theme changed \n",
                    e.Document != null ? e.Document.ToString() : ""
                )
            );
        }
    }
}