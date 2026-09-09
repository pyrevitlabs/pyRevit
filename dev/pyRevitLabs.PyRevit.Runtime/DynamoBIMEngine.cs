using System;
using System.Linq;
using System.Collections.Generic;
using System.Reflection;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;
using pyRevitLabs.Json;

namespace PyRevitLabs.PyRevit.Runtime {
    public class DynamoBIMEngineConfigs : ScriptEngineConfigs {
        public bool clean = false;
        public bool automate = true;
        public string dynamo_path = string.Empty;
        public bool dynamo_path_exec = true;
        public bool dynamo_path_check_existing = false;
        public bool dynamo_force_manual_run = false;
        public string dynamo_model_nodes_info = string.Empty;
    }

    public class DynamoBIMEngine : ScriptEngine {
        public DynamoBIMEngineConfigs ExecEngineConfigs = new DynamoBIMEngineConfigs();

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);
            // this is not a cachable engine; always use new engines
            UseNewEngine = true;

            // extract engine configuration from runtime data
            try {
                ExecEngineConfigs = JsonConvert.DeserializeObject<DynamoBIMEngineConfigs>(runtime.ScriptRuntimeConfigs.EngineConfigs);
            } catch {}
        }

        public override int Execute(ref ScriptRuntime runtime) {
            var journalData = new Dictionary<string, string>() {
                // Specifies the path to the Dynamo workspace to execute.
                { "dynPath", runtime.ScriptSourceFile },

                // Specifies whether the Dynamo UI should be visible (set to false - Dynamo will run headless).
                { "dynShowUI", runtime.ScriptRuntimeConfigs.DebugMode.ToString() },

                // If the journal file specifies automation mode
                // Dynamo will run on the main thread without the idle loop.
                { "dynAutomation",  ExecEngineConfigs.automate ? "True" : "False" },

                 // The journal file can specify if the Dynamo workspace opened 
                // from DynPathKey will be executed or not. 
                // If we are in automation mode the workspace will be executed regardless of this key.
                { "dynPathExecute",  ExecEngineConfigs.dynamo_path_exec ? "True" : "False" },

                // The journal file can specify if the existing UIless RevitDynamoModel
                // needs to be shutdown before performing any action.
                // per comments on https://github.com/eirannejad/pyRevit/issues/570
                // Setting this to True slows down Dynamo by a factor of 3
                { "dynModelShutDown",  ExecEngineConfigs.clean ? "True" : "False" },
            };

            if (ExecEngineConfigs.dynamo_path != null && ExecEngineConfigs.dynamo_path != string.Empty) {
                // The journal file can specify a Dynamo workspace to be opened 
                // (and executed if we are in automation mode) at run time.
                journalData["dynPath"] = ExecEngineConfigs.dynamo_path;
                // The journal file can specify if a check should be performed to see if the
                // current workspaceModel already points to the Dynamo file we want to 
                // run (or perform other tasks). If that's the case, we want to use the
                // current workspaceModel.
                journalData["dynPathCheckExisting"] = ExecEngineConfigs.dynamo_path_check_existing ? "True" : "False";
                // The journal file can specify if the Dynamo workspace opened
                // from DynPathKey will be forced in manual mode.
                journalData["dynForceManualRun"] = ExecEngineConfigs.dynamo_force_manual_run ? "True" : "False";
            }

            if (ExecEngineConfigs.dynamo_model_nodes_info != null && ExecEngineConfigs.dynamo_model_nodes_info != string.Empty) {
                // The journal file can specify the values of Dynamo nodes.
                journalData["dynModelNodesInfo"] = ExecEngineConfigs.dynamo_model_nodes_info;
            }

            //return new DynamoRevit().ExecuteCommand(new DynamoRevitCommandData() {
            //    JournalData = journalData,
            //    Application = commandData.Application
            //});

            try {
                Assembly dynamoAssembly = AppDomain.CurrentDomain.GetAssemblies()
                    .FirstOrDefault(a => a.GetName().Name == "DynamoRevitDS");

                if (dynamoAssembly == null) {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName,
                        "Can not find Dynamo installation or determine which Dynamo version to Run.\n\n" +
                        "Run Dynamo once to select the active version.");
                    return ScriptExecutorResultCodes.ExecutionException;
                }

                Type dynRevitAppType = dynamoAssembly.GetType("Dynamo.Applications.DynamoRevitApp");
                if (dynRevitAppType == null) {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName,
                        "Could not locate DynamoRevitApp in the loaded Dynamo assembly.\n\n" +
                        "The installed Dynamo version may not be compatible.");
                    return ScriptExecutorResultCodes.ExecutionException;
                }

                object dynRevitApp = Activator.CreateInstance(dynRevitAppType);
                MethodInfo execDynamo = dynRevitAppType.GetMethod("ExecuteDynamoCommand");

                if (execDynamo == null) {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName,
                        "Could not locate ExecuteDynamoCommand in DynamoRevitApp.\n\n" +
                        "The installed Dynamo version may not be compatible.");
                    return ScriptExecutorResultCodes.ExecutionException;
                }

                // run the script
                execDynamo.Invoke(dynRevitApp, new object[] { journalData, runtime.UIApp });
                return ScriptExecutorResultCodes.Succeeded;
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
