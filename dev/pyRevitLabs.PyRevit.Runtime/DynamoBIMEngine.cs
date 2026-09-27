using System;
using System.Collections.Generic;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit.Runtime.Shared;
using pyRevitLabs.TargetApps.Revit;

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
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public DynamoBIMEngineConfigs ExecEngineConfigs = new DynamoBIMEngineConfigs();

        public override void Init(ref ScriptRuntime runtime) {
            base.Init(ref runtime);
            // this is not a cachable engine; always use new engines
            UseNewEngine = true;

            // extract engine configuration from runtime data
            try {
                ExecEngineConfigs = JsonConvert.DeserializeObject<DynamoBIMEngineConfigs>(runtime.ScriptRuntimeConfigs.EngineConfigs);
            }
            catch { }
        }

        public override int Execute(ref ScriptRuntime runtime) {
            try {
                if (runtime.UIApp == null) {
                    TaskDialog.Show(PyRevitLabsConsts.ProductName, "Can not access the UIApplication instance");
                    return ScriptExecutorResultCodes.ExecutionException;
                }

                var execResult = DynamoRevitInterop.Run(
                    BuildExecutionOptions(ref runtime),
                    runtime.UIApp,
                    GetRevitAddinsFolders(ref runtime)
                    );

                logger.Debug("Dynamo script run: {0}\n{1}", execResult.Status, execResult.Details);

                if (execResult.Succeeded) {
                    if (!string.IsNullOrEmpty(execResult.Message))
                        logger.Info(execResult.Message);
                    return ScriptExecutorResultCodes.Succeeded;
                }

                var dialog = new TaskDialog(PyRevitLabsConsts.ProductName);
                dialog.MainInstruction = execResult.Message;
                if (!string.IsNullOrEmpty(execResult.Details))
                    dialog.ExpandedContent = execResult.Details;
                dialog.Show();
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

        private DynamoExecutionOptions BuildExecutionOptions(ref ScriptRuntime runtime) {
            return new DynamoExecutionOptions {
                GraphPath = !string.IsNullOrEmpty(ExecEngineConfigs.dynamo_path)
                    ? ExecEngineConfigs.dynamo_path
                    : runtime.ScriptSourceFile,
                NodesInfo = ExecEngineConfigs.dynamo_model_nodes_info,
                ShowUI = runtime.ScriptRuntimeConfigs.DebugMode,
                Automate = ExecEngineConfigs.automate,
                ExecuteGraph = ExecEngineConfigs.dynamo_path_exec,
                ShutdownModel = ExecEngineConfigs.clean,
                ReuseOpenGraph = ExecEngineConfigs.dynamo_path_check_existing,
                ForceManualRun = ExecEngineConfigs.dynamo_force_manual_run
            };
        }

        private IEnumerable<string> GetRevitAddinsFolders(ref ScriptRuntime runtime) {
            int revitYear;
            if (runtime.App == null || !int.TryParse(runtime.App.VersionNumber, out revitYear))
                return new string[0];

            return new[] {
                RevitAddons.GetRevitAddonsFolder(revitYear, allUsers: false),
                RevitAddons.GetRevitAddonsFolder(revitYear, allUsers: true)
            };
        }
    }
}
