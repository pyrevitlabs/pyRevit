using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.Remoting;
using System.Reflection;
using System.Web.Script.Serialization;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class DynamoBIMEngineConfigs : ScriptEngineConfigs {
        public bool clean;
    }

    public class DynamoBIMEngine : ScriptEngine {
        public DynamoBIMEngineConfigs ExecEngineConfigs = new DynamoBIMEngineConfigs();

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);
            // this is not a cachable engine; always use new engines
            UseNewEngine = true;

            // extract engine configuration from runtime data
            try {
                ExecEngineConfigs = new JavaScriptSerializer().Deserialize<DynamoBIMEngineConfigs>(runtime.ScriptRuntimeConfigs.EngineConfigs);
            }
            catch {
                // if any errors switch to defaults
                ExecEngineConfigs.clean = false;
            }
        }

        public override int Execute(ref ScriptRuntime runtime) {
            var journalData = new Dictionary<string, string>() {
                // Specifies the path to the Dynamo workspace to execute.
                { "dynPath", runtime.ScriptSourceFile },

                // Specifies whether the Dynamo UI should be visible (set to false - Dynamo will run headless).
                { "dynShowUI", runtime.ScriptRuntimeConfigs.DebugMode.ToString() },

                // If the journal file specifies automation mode
                // Dynamo will run on the main thread without the idle loop.
                { "dynAutomation",  "True" },

                // The journal file can specify if the Dynamo workspace opened
                { "dynForceManualRun",  "False" },

                // The journal file can specify if the Dynamo workspace opened from DynPathKey will be executed or not. 
                // If we are in automation mode the workspace will be executed regardless of this key.
                { "dynPathExecute",  "True" },

                // The journal file can specify if the existing UIless RevitDynamoModel
                // needs to be shutdown before performing any action.
                // per comments on https://github.com/eirannejad/pyRevit/issues/570
                // Setting this to True slows down Dynamo by a factor of 3
                { "dynModelShutDown",  ExecEngineConfigs.clean ? "True" : "False" },

                // The journal file can specify the values of Dynamo nodes.
                //{ "dynModelNodesInfo",  "" }
                };

            //return new DynamoRevit().ExecuteCommand(new DynamoRevitCommandData() {
            //    JournalData = journalData,
            //    Application = commandData.Application
            //});

            try {
                // find the DynamoRevitApp from DynamoRevitDS.dll
                // this should be already loaded since Dynamo loads before pyRevit
                ObjectHandle dynRevitAppObjHandle =
                    Activator.CreateInstance("DynamoRevitDS", "Dynamo.Applications.DynamoRevitApp");
                object dynRevitApp = dynRevitAppObjHandle.Unwrap();
                MethodInfo execDynamo = dynRevitApp.GetType().GetMethod("ExecuteDynamoCommand");

                // run the script
                execDynamo.Invoke(dynRevitApp, new object[] { journalData, runtime.UIApp });
                return ScriptExecutorResultCodes.Succeeded;
            }
            catch (FileNotFoundException) {
                // if failed in finding DynamoRevitDS.dll, assume no dynamo
                TaskDialog.Show(PyRevitLabsConsts.ProductName,
                    "Can not find Dynamo installation or determine which Dynamo version to Run.\n\n" +
                    "Run Dynamo once to select the active version.");
                return ScriptExecutorResultCodes.ExecutionException;
            }
            catch (Exception dynEx) {
                // on any other errors
                var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                dialog.MainInstruction = "Error executing Dynamo script.";
                dialog.ExpandedContent = string.Format("{0}\n{1}", dynEx.Message, dynEx.StackTrace);
                dialog.Show();
                return ScriptExecutorResultCodes.ExecutionException;
            }
        }
    }
}
