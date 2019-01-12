using System;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.UI;

namespace PyRevitRunner {
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    class PyRevitRunnerApplication : IExternalApplication {
        // Hook into Revit to allow starting a command.
        Result IExternalApplication.OnStartup(UIControlledApplication application) {
            try {
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
