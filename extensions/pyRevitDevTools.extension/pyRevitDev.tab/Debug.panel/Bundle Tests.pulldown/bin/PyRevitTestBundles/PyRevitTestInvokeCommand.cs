using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace PyRevitTestBundles
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public class PyRevitTestInvokeCommand : IExternalCommand
    {
        public PyRevitTestInvokeCommand() { }

        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
        {
            TaskDialog.Show("Revit", "Hello World from Invoke Button!!!");
            return Result.Succeeded;
        }
    }
}
