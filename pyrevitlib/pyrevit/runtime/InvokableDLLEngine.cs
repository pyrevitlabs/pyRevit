using System;
using System.IO;
using System.Linq;
using System.Reflection;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class InvokableDLLEngine : ScriptEngine {
        private string scriptSig = string.Empty;
        private Assembly scriptAssm = null;

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);

            // If the user is asking to refresh the cached engine for the command,
            UseNewEngine = runtime.ScriptRuntimeConfigs.RefreshEngine;
        }

        public override int Execute(ref ScriptRuntime runtime) {
            try {
                // first argument is expected to be assmFile:className
                if (runtime.ScriptRuntimeConfigs.Arguments.Count == 1) {
                    // load the binary data from the DLL
                    // Direct invoke commands use the config script source file to point
                    // to the target dll assembly location
                    string argumentString = runtime.ScriptRuntimeConfigs.Arguments.First();
                    string assmFile = argumentString;
                    string className = null;
                    if (argumentString.Contains("::")) {
                        var parts = argumentString.Split(
                            new string[] { "::" },
                            StringSplitOptions.RemoveEmptyEntries
                            );

                        assmFile = parts[0];
                        className = parts[1];
                    }

                    if (scriptSig == null || CommonUtils.GetFileSignature(assmFile) != scriptSig) {
                        scriptAssm = Assembly.Load(File.ReadAllBytes(assmFile));
                    }

                    var resultCode = CLREngine.ExecuteExternalCommand(scriptAssm, className, ref runtime);
                    if (resultCode == ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException)
                        TaskDialog.Show(PyRevitLabsConsts.ProductName,
                            string.Format(
                                "Can not find type \"{0}\" in assembly \"{1}\"",
                                className,
                                scriptAssm.Location
                                ));
                    return resultCode;
                }
                else {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName, "Target assembly is not set correctly and can not be loaded.");
                    return ScriptExecutorResultCodes.ExternalInterfaceNotImplementedException;
                }
            }
            catch (Exception invokeEx) {
                var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                dialog.MainInstruction = "Error invoking .NET external command.";
                dialog.ExpandedContent = string.Format("{0}\n{1}", invokeEx.Message, invokeEx.StackTrace);
                dialog.Show();
                return ScriptExecutorResultCodes.ExecutionException;
            }
            finally {
                // whatever
            }
        }
    }
}
