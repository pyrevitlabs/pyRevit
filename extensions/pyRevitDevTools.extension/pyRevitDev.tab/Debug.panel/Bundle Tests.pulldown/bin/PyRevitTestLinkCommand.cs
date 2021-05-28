using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace PyRevitTestLinkCommand {
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public class PyRevitTestLinkExternalCommand : IExternalCommand {
        public PyRevitTestLinkExternalCommand() { }
        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements) {
            TaskDialog.Show("Revit", "Hello World from Link Button!!!");
            return Result.Succeeded;
        }
    }

    public class PyRevitTestLinkExternalCommandAvail : IExternalCommandAvailability {
        public PyRevitTestLinkExternalCommandAvail() { }
        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) => true;
    }
}
