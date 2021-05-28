using System;
using System.IO;
using System.Reflection;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.UI;

/* Note:
 * It is necessary that this code object do not have any references to IronPython.
 * To ensure the correct version of IronPython dlls are loaded, the OnStartup()
 * methods manually loads the IronPython assemblies before calling into the 
 * ScriptExecutor that has IronPython references
 */
namespace PyRevitRunner {
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    class PyRevitRunnerApplication : IExternalApplication {
        public static string LoaderPath => Path.GetDirectoryName(typeof(PyRevitRunnerApplication).Assembly.Location);

        // Hook into Revit to allow starting a command.
        Result IExternalApplication.OnStartup(UIControlledApplication application) {
            try {
                // load all engine assemblies
                // this is to ensure pyRevit is loaded on its own assemblies
                foreach (var engineDll in Directory.GetFiles(LoaderPath, "*.dll"))
                    Assembly.LoadFrom(engineDll);

                return RegisterExternalCommand(application);
            }
            catch (Exception ex) {
                TaskDialog.Show("Error Loading Script Runner Application", ex.ToString());
                return Result.Failed;
            }
        }

        private static Result RegisterExternalCommand(UIControlledApplication application) {
            var assembly = typeof(PyRevitRunnerApplication).Assembly;

            RibbonPanel ribbonPanel = application.CreateRibbonPanel("pyRevitRunner");

            // Run service button
            var pbData = new PushButtonData(
                "PyRevitRunnerCommand",
                "PyRevitRunnerCommand",
                assembly.Location,
                "PyRevitRunner.PyRevitRunnerCommand");
            pbData.AvailabilityClassName = "PyRevitRunner.PyRevitRunnerCommandAvail";

            ribbonPanel.AddItem(pbData);

            return Result.Succeeded;
        }

        Result IExternalApplication.OnShutdown(UIControlledApplication application) {
            // FIXME: deallocate the python shell...
            return Result.Succeeded;
        }
    }
}
