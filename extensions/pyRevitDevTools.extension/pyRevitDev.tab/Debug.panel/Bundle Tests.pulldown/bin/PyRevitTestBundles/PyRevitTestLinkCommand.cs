using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace PyRevitTestBundles
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public class PyRevitTestLinkCommand : IExternalCommand
    {
        public PyRevitTestLinkCommand() { }

        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
        {
            TaskDialog.Show("Revit", "Hello World from Link Button!!!");
            return Result.Succeeded;
        }
    }

    public class PyRevitTestLinkCommandAvail : IExternalCommandAvailability
    {
        public PyRevitTestLinkCommandAvail() { }
        
        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories) => true;
    }
}
