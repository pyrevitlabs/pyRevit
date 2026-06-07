using System.Collections.Generic;

using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Thin entry used by the interactive shell to configure its IronPython engine exactly like a
    /// pyRevit script run: full builtins (incl. <c>__scriptruntime__</c>, so
    /// <c>from pyrevit import ...</c> works), RevitAPI loaded, the active fork's bundled stdlib, and
    /// the caller's sys.path. Built into the per-fork runtime, so it operates on the same DLR
    /// identity as the engine pyRevit is configured to use. The shell's console owns stdin/stdout,
    /// so engine streams are intentionally left untouched here.
    /// </summary>
    public static class InteractiveEngine {
        /// <summary>
        /// Apply the standard pyRevit environment to an interactive shell's IronPython engine
        /// (the one its DLR console already created for the active fork).
        /// </summary>
        public static void ConfigureIronPythonEngine(Microsoft.Scripting.Hosting.ScriptEngine engine, UIApplication uiapp, IList<string> searchPaths) {
            var scriptData = new ScriptData {
                ScriptPath = "interactive_shell.py",
                ConfigScriptPath = "interactive_shell.py",
                CommandName = "Interactive Shell",
                CommandBundle = "pyRevit Shell",
                CommandExtension = "pyRevitCore",
                CommandUniqueId = "pyrevit-interactive-shell",
                CommandControlId = "pyrevit-interactive-shell",
            };

            var configs = new ScriptRuntimeConfigs {
                UIApp = uiapp,
                SearchPaths = searchPaths != null ? new List<string>(searchPaths) : new List<string>(),
                Arguments = new List<string>(),
                Variables = new Dictionary<string, object>(),
                EngineConfigs = "{\"clean\":false,\"full_frame\":false,\"persistent\":true}",
            };

            var runtime = new ScriptRuntime(scriptData, configs);

            // mirror IronPythonEngine.Start's assembly access
            engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);
            engine.Runtime.LoadAssembly(typeof(ScriptExecutor).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // pyRevit's bundled standard library for the active fork
            new PyRevitLoader.ScriptExecutor().AddEmbeddedLib(engine);

            // sys.path captured from the launching pyRevit engine (pyrevitlib, site-packages, ...)
            engine.SetSearchPaths(configs.SearchPaths);

            // full pyRevit builtins so the REPL matches a normal script's environment
            IronPythonEngine.InjectBuiltins(engine, runtime, recoveredFromCache: false, typeId: "pyrevit-interactive-shell");
        }
    }
}
