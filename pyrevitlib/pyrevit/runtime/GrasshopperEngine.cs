using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.Remoting;
using System.Reflection;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class GrasshoppertEngine : ScriptEngine {
        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);
            // this is not a cachable engine; always use new engines
            UseNewEngine = true;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            try {
                // find RhinoInside.Revit.dll
                ObjectHandle ghObjHandle =
                    Activator.CreateInstance("RhinoInside.Revit", "RhinoInside.Revit.UI.CommandGrasshopperPlayer");
                object ghPlayer = ghObjHandle.Unwrap();
                foreach (MethodInfo methodInfo in ghPlayer.GetType().GetMethods()) {
                    var methodParams = methodInfo.GetParameters();
                    if (methodInfo.Name == "Execute" && methodParams.Count() == 5) {

                        View activeView = null;
#if !(REVIT2013 || REVIT2014)
                        if (runtime.UIApp != null && runtime.UIApp.ActiveUIDocument != null)
                            activeView = runtime.UIApp.ActiveUIDocument.ActiveGraphicalView;
#else
                        if (runtime.UIApp != null && runtime.UIApp.ActiveUIDocument != null)
                            activeView = runtime.UIApp.ActiveUIDocument.ActiveView;
#endif

                        // run the script
                        if (runtime.UIApp != null) {
                            string message = string.Empty;

                            methodInfo.Invoke(
                                ghPlayer,
                                new object[] {
                                    runtime.UIApp,
                                    activeView,
                                    new Dictionary<string,string>(),
                                    runtime.ScriptSourceFile,
                                    message
                            });

                            return ScriptExecutorResultCodes.Succeeded;
                        }
                        else {
                            TaskDialog.Show(PyRevitLabsConsts.ProductName, "Can not access the UIApplication instance");
                            return ScriptExecutorResultCodes.ExecutionException;
                        }
                    }
                }

                TaskDialog.Show(PyRevitLabsConsts.ProductName, "Can not find appropriate Grasshopper Execute method");
                return ScriptExecutorResultCodes.ExecutionException;

            }
            catch (FileNotFoundException) {
                // if failed in finding DynamoRevitDS.dll, assume no dynamo
                TaskDialog.Show(PyRevitLabsConsts.ProductName,
                    "Can not find Rhino.Inside installation or it is not loaded yet.\n\n" +
                    "Install/Load Rhino.Inside first.");
                return ScriptExecutorResultCodes.ExecutionException;
            }
            catch (Exception ghEx) {
                // if failed in finding RhinoInside.Revit.dll, assume no rhino
                var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                dialog.MainInstruction = "Error executing Grasshopper script.";
                dialog.ExpandedContent = string.Format("{0}\n{1}", ghEx.Message, ghEx.StackTrace);
                dialog.Show();
                return ScriptExecutorResultCodes.ExecutionException;
            }
        }
    }
}
