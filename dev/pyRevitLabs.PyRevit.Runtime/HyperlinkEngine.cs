using System;
using System.Linq;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class HyperlinkEngine : ScriptEngine {
        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);
            // this is not a cachable engine; always use new engines
            UseNewEngine = true;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            try {
                // first argument is expected to be a hyperlink
                if (runtime.ScriptRuntimeConfigs.Arguments.Count == 1) {
                    string hyperLink = runtime.ScriptRuntimeConfigs.Arguments.First();
                    System.Diagnostics.Process.Start(hyperLink);
                    return ScriptExecutorResultCodes.Succeeded;
                }
                else {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName, "Target hyperlink is not set correctly and can not be loaded.");
                    return ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException;
                }
            }
            catch (Exception hyperlinkEx) {
                var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                dialog.MainInstruction = "Error opening link.";
                dialog.ExpandedContent = string.Format("{0}\n{1}", hyperlinkEx.Message, hyperlinkEx.StackTrace);
                dialog.Show();
                return ScriptExecutorResultCodes.ExecutionException;
            }
            finally {
                // whatever
            }
        }
    }
}