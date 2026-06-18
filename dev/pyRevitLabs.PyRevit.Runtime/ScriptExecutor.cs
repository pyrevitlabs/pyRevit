using System.IO;
using System.Threading;

using Autodesk.Revit.UI;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class ScriptExecutorResultCodes {
        public static int Succeeded = 0;
        public static int SysExited = 1;
        public static int ExecutionException = 2;
        public static int CompileException = 3;
        public static int EngineNotImplementedException = 4;
        public static int ExternalInterfaceNotImplementedException = 5;
        public static int FailedLoadingContent = 6;
        public static int BadCommandArguments = 7;
        public static int NotSupportedFeatureException = 8;
        public static int UnknownException = 9;
        public static int MissingTargetScript = 10;
        public static int DelayedExecutionRequested = 11;
        public static int FailedDelayedExecutionRequest = 12;
        public static int DelayedExecutionException = 13;
        public static int ExecutorNotInitialized = 14;
    }

    public class ScriptExecutorExternalEventHandler : IExternalEventHandler {
        public ScriptData ScriptData;
        public ScriptRuntimeConfigs ScriptRuntimeConfigs;
        public int Result = ScriptExecutorResultCodes.DelayedExecutionException;

        public void Execute(UIApplication uiApp) {
            if (ScriptData != null && ScriptRuntimeConfigs != null) {
                try {
                    // provide the given uiapp
                    ScriptRuntimeConfigs.UIApp = uiApp;

                    // request execution and set results
                    Result = ScriptExecutor.ExecuteScript(ScriptData, ScriptRuntimeConfigs);
                }
                finally {
                    // release the executed script's references; this handler lives
                    // for the whole process and would otherwise pin the previous
                    // session's runtime objects (UIApp, documents) across reloads.
                    // NOTE: these fields are a singleton and not thread-safe. A
                    // concurrent non-blocking RequestExecuteScript can overwrite a
                    // pending script before Execute() fires for it; this is a
                    // pre-existing limitation of the single-handler design.
                    ScriptData = null;
                    ScriptRuntimeConfigs = null;
                }
            }
        }

        public string GetName() {
            return "ScriptExecutorExternalEventHandler";
        }
    }

    public class ScriptExecutorConfigs {
        public bool WaitForResult = true;
        public bool SendTelemetry = false;
    }

    /// Executes a script
    public class ScriptExecutor {
        private static int mainThreadId;
        private static ScriptExecutorExternalEventHandler extExecEventHandler;
        private static ExternalEvent extExecEvent;

        public static void Initialize() {
            // Idempotent on purpose. The ExternalEvent is scoped to the add-in
            // lifetime (the loader stays registered for the whole Revit process),
            // not to a pyRevit session, so the same event remains valid across
            // reloads and is reused instead of recreated. Reusing it avoids
            // leaking an undisposed ExternalEvent + handler on every reload
            // (Revit holds a strong reference to the handler) and avoids breaking
            // an in-flight RequestExecuteScript. Both the python and c# session
            // managers call Initialize() during a single load, so the early
            // return also collapses that double call.
            // NOTE: assemblies load into the default (non-collectible)
            // AssemblyLoadContext, so there is no per-session context to pin or
            // unload here; revisit this if pyRevit ever adopts collectible load
            // contexts, where disposing the old event on reload would matter.
            // The check-then-create below is intentionally unlocked: both call
            // sites run on the Revit main thread during init, so there is no
            // concurrent entry to guard against.
            if (extExecEvent != null)
                return;

            mainThreadId = Thread.CurrentThread.ManagedThreadId;
            extExecEventHandler = new ScriptExecutorExternalEventHandler();
            extExecEvent = ExternalEvent.Create(extExecEventHandler);
        }

        /// Run the script and print the output to a new output window.
        public static int ExecuteScript(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs = null) {
            // make sure there is base configs
            scriptExecConfigs = scriptExecConfigs == null ? new ScriptExecutorConfigs() : scriptExecConfigs;

            if (mainThreadId != 0) {
                if (Thread.CurrentThread.ManagedThreadId == mainThreadId)
                    return ExecuteScriptNow(scriptData, scriptRuntimeCfg, scriptExecConfigs);
                else
                    return RequestExecuteScript(scriptData, scriptRuntimeCfg, scriptExecConfigs);
            }

            return ScriptExecutorResultCodes.ExecutorNotInitialized;
        }

        private static int ExecuteScriptNow(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs) {
            // create runtime
            var runtime = new ScriptRuntime(scriptData, scriptRuntimeCfg);

            // determine which engine to use, and execute
            if (EnsureTargetScript(ref runtime)) {
                switch (runtime.EngineType) {
                    case ScriptEngineType.IronPython:
                        ExecuteManagedScript<IronPythonEngine>(ref runtime);
                        break;

                    case ScriptEngineType.CPython:
                        ExecuteManagedScript<CPythonEngine>(ref runtime);
                        break;

                    case ScriptEngineType.CSharp:
                        ExecuteManagedScript<CLREngine>(ref runtime);
                        break;

                    case ScriptEngineType.Invoke:
                        ExecuteManagedScript<InvokableDLLEngine>(ref runtime);
                        break;

                    case ScriptEngineType.VisualBasic:
                        ExecuteManagedScript<CLREngine>(ref runtime);
                        break;

                    case ScriptEngineType.IronRuby:
                        ExecuteManagedScript<IronRubyEngine>(ref runtime);
                        break;

                    case ScriptEngineType.DynamoBIM:
                        ExecuteManagedScript<DynamoBIMEngine>(ref runtime);
                        break;

                    case ScriptEngineType.Grasshopper:
                        ExecuteManagedScript<GrasshoppertEngine>(ref runtime);
                        break;

                    case ScriptEngineType.Content:
                        ExecuteManagedScript<ContentEngine>(ref runtime);
                        break;

                    case ScriptEngineType.HyperLink:
                        ExecuteManagedScript<HyperlinkEngine>(ref runtime);
                        break;

                    default:
                        // should not get here
                        throw new PyRevitException("Unknown engine type.");
                }
            }
            else
                runtime.ExecutionResult = ScriptExecutorResultCodes.MissingTargetScript;

            // Log results
            int result = runtime.ExecutionResult;
            if (scriptExecConfigs.SendTelemetry)
                ScriptTelemetry.LogScriptTelemetryRecord(ref runtime);

            // GC cleanups
            var re = runtime.ExecutionResult;
            runtime.Dispose();
            runtime = null;

            // return the result
            return result;
        }

        private static int RequestExecuteScript(ScriptData scriptData, ScriptRuntimeConfigs scriptRuntimeCfg, ScriptExecutorConfigs scriptExecConfigs) {
            if (extExecEventHandler != null) {
                extExecEventHandler.ScriptData = scriptData;
                extExecEventHandler.ScriptRuntimeConfigs = scriptRuntimeCfg;

                // request command exec now
                extExecEvent.Raise();

                // wait until the script is executed
                if (scriptExecConfigs.WaitForResult) {
                    while (extExecEvent.IsPending) ;
                    return extExecEventHandler.Result;
                }
                // otherwise
                return ScriptExecutorResultCodes.DelayedExecutionRequested;
            }

            return ScriptExecutorResultCodes.FailedDelayedExecutionRequest;
        }

        public static bool EnsureTargetScript(ref ScriptRuntime runtime) {
            if (runtime.ScriptRuntimeConfigs.ConfigMode)
                return EnsureTargetScript(runtime.ScriptData.ConfigScriptPath);
            else
                return EnsureTargetScript(runtime.ScriptData.ScriptPath);
        }

        public static bool EnsureTargetScript(string scriptFile) {
            if (File.Exists(scriptFile))
                return true;
            TaskDialog.Show(PyRevitLabsConsts.ProductName, "Can not find target file. Maybe deleted?");
            return false;
        }

        private static void ExecuteManagedScript<T>(ref ScriptRuntime runtime) where T : ScriptEngine, new() {
            // 1: ----------------------------------------------------------------------------------------------------
            // get new engine manager (EngineManager manages document-specific engines)
            // and ask for an engine (EngineManager return either new engine or an already active one)
            T engine = ScriptEngineManager.GetEngine<T>(ref runtime);

            // init the engine
            engine.Start(ref runtime);
            // execute
            var result = engine.Execute(ref runtime);
            // stop and cleanup the engine
            engine.Stop(ref runtime);

            // set result
            runtime.ExecutionResult = result;
        }
    }
}
