using Autodesk.Revit.Attributes;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.PyRevit.Runtime.Shared;

namespace PyRevitTestBundles
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public class PyRevitTestInvokeCommandWithExecParams : IExternalCommand
    {
        public ExecParams execParams;

        public PyRevitTestInvokeCommandWithExecParams() { }

        public Result Execute(ExternalCommandData revit, ref string message, ElementSet elements)
        {
            TaskDialog.Show("Revit", $"Hello World from Invoke Button!!!\nName:\n\"{execParams.CommandName}\"");
            return Result.Succeeded;
        }
    }
}
