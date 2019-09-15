using System.IO;

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
    }

    /// Executes a script
    public class ScriptExecutor {
        /// Run the script and print the output to a new output window.
        public static int ExecuteScript(ref ScriptRuntime runtime) {
            if (EnsureTargetScript(ref runtime)) {
                switch (runtime.EngineType) {
                    case ScriptEngineType.IronPython:
                        return ExecuteManagedScript<IronPythonEngine>(ref runtime);

                    case ScriptEngineType.CPython:
                        return ExecuteManagedScript<CPythonEngine>(ref runtime);

                    case ScriptEngineType.CSharp:
                        return ExecuteManagedScript<CLREngine>(ref runtime);

                    case ScriptEngineType.Invoke:
                        return ExecuteManagedScript<InvokableDLLEngine>(ref runtime);

                    case ScriptEngineType.VisualBasic:
                        return ExecuteManagedScript<CLREngine>(ref runtime);

                    case ScriptEngineType.IronRuby:
                        return ExecuteManagedScript<IronRubyEngine>(ref runtime);

                    case ScriptEngineType.DynamoBIM:
                        return ExecuteManagedScript<DynmoBIMEngine>(ref runtime);

                    case ScriptEngineType.Grasshopper:
                        return ExecuteManagedScript<GrasshoppertEngine>(ref runtime);

                    case ScriptEngineType.Content:
                        return ExecuteManagedScript<ContentEngine>(ref runtime);

                    case ScriptEngineType.HyperLink:
                        return ExecuteManagedScript<HyperlinkEngine>(ref runtime);

                    default:
                        // should not get here
                        throw new PyRevitException("Unknown engine type.");
                }
            } else
                return ScriptExecutorResultCodes.MissingTargetScript;
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

        private static int ExecuteManagedScript<T>(ref ScriptRuntime runtime) where T : ScriptEngine, new() {
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

            return result;
        }
    }
}
