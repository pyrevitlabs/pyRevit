using System;
using System.IO;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.Attributes;

namespace PyRevitLoader
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    class PyRevitLoaderApplication : IExternalApplication
    {
        private static string versionNumber;

        // Hook into Revit to allow starting a command.
        Result IExternalApplication.OnStartup(UIControlledApplication application)
        {

            try
            {
                versionNumber = application.ControlledApplication.VersionNumber;
                if (application.ControlledApplication.VersionName.ToLower().Contains("vasari"))
                {
                    versionNumber = "_Vasari";
                }

                ExecuteStartupScript(application);

                return Result.Succeeded;
            }
            catch (Exception ex)
            {
                TaskDialog.Show("Error setting up PyRevitLoader", ex.ToString());
                return Result.Failed;
            }
        }

        private static void ExecuteStartupScript(UIControlledApplication uiControlledApplication)
        {
            // we need a UIApplication object to assign as `__revit__` in python...
            var versionNumber = uiControlledApplication.ControlledApplication.VersionNumber;
            var fieldName = int.Parse(versionNumber) >= 2017 ? "m_uiapplication": "m_application";
            var fi = uiControlledApplication.GetType().GetField(fieldName, BindingFlags.NonPublic | BindingFlags.Instance);

            var uiApplication = (UIApplication)fi.GetValue(uiControlledApplication);
            // execute StartupScript
            var startupScript = GetStartupScriptPath();
            if (startupScript != null)
            {
                var executor = new ScriptExecutor(uiApplication); // uiControlledApplication);
                var result = executor.ExecuteScript(startupScript);
                if (result == (int)Result.Failed)
                {
                    TaskDialog.Show("PyRevitLoader", executor.Message);
                }
            }
        }

        private static string GetStartupScriptPath()
        {
            var loaderDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            var dllDir = Path.GetDirectoryName(loaderDir);
            return Path.Combine(dllDir, String.Format("{0}.py", Assembly.GetExecutingAssembly().GetName().Name));
        }

        Result IExternalApplication.OnShutdown(UIControlledApplication application)
        {
            // FIXME: deallocate the python shell...
            return Result.Succeeded;
        }
    }
}
