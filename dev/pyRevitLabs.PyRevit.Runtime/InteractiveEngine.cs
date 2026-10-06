using System.Collections.Generic;

using Autodesk.Revit.UI;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Configures an interactive engine with the pyRevit command environment without replacing
    /// console-owned streams.
    /// </summary>
    public static class InteractiveEngine {
        /// <summary>
        /// Applies the standard pyRevit environment to an interactive engine.
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

            engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);
            engine.Runtime.LoadAssembly(typeof(ScriptExecutor).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            new PyRevitLoader.ScriptExecutor().AddEmbeddedLib(engine);

            engine.SetSearchPaths(configs.SearchPaths);

            IronPythonEngine.InjectBuiltins(engine, runtime, recoveredFromCache: false, typeId: "pyrevit-interactive-shell");
        }
    }
}
