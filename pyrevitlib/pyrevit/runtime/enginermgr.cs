using System;
using System.IO;
using System.Collections.Generic;

using Microsoft.Scripting.Hosting;
using IronPython.Hosting;


namespace PyRevitLabs.PyRevit.Runtime {
    public enum EngineType {
        IronPython,
        CPython,
        CSharp,
        Invoke,
        VisualBasic,
        IronRuby,
        Dynamo,
        Grasshopper,
        Content,
    }

    public abstract class ExecutionEngine {
        public abstract string Id { get; set; }
        public abstract bool NeedsNew { get; set; }
        public abstract EngineType EngineType { get; }
        public abstract bool Cached { get; set; }

        public abstract void Init(ref ScriptRuntime runtime);
        public abstract void Setup(ref ScriptRuntime runtime);
        public abstract void Shutdown();
    }

    public static class EngineManager {
        public static T GetEngine<T>(ref ScriptRuntime runtime) where T : ExecutionEngine, new() {
            T engine = new T();
            engine.Init(ref runtime);

            if (engine.NeedsNew) {
                SetCachedEngine<T>(engine.Id, engine);
            }
            else {
                var cachedEngine = GetCachedEngine<T>(engine.Id);
                if (cachedEngine != null) {
                    engine = cachedEngine;
                    engine.Cached = true;
                }
                else
                    SetCachedEngine<T>(engine.Id, engine);
            }

            engine.Setup(ref runtime);
            return engine;
        }

        public static Dictionary<string, ExecutionEngine> EngineDict {
            get {
                var engineDict = (Dictionary<string, ExecutionEngine>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.EnginesDictKey);

                if (engineDict == null)
                    engineDict = ClearEngines();

                return engineDict;
            }
        }

        public static Dictionary<string, ExecutionEngine> ClearEngines() {
            // shutdown all existing engines
            foreach (KeyValuePair<string, ExecutionEngine> kv in EngineDict)
                kv.Value.Shutdown();
            
            // create a new list
            var newEngineDict = new Dictionary<string, ExecutionEngine>();
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.EnginesDictKey, newEngineDict);
            return newEngineDict;
        }

        private static T GetCachedEngine<T>(string engineId) where T : ExecutionEngine, new() {
            if (EngineDict.ContainsKey(engineId))
                return (T)EngineDict[engineId];
            return null;
        }

        private static void SetCachedEngine<T>(string engineId, T engine) where T : ExecutionEngine, new() {
            var cachedEngine = GetCachedEngine<T>(engine.Id);
            if (cachedEngine != null)
                cachedEngine.Shutdown();
            EngineDict[engineId] = engine;
        }
    }

    public class IronPythonEngine : ExecutionEngine {
        private List<string> _commandBuiltins = new List<string>();
        private List<ScriptScope> _scopes = new List<ScriptScope>();

        public override string Id { get; set; }
        public override bool NeedsNew { get; set; }
        public override bool Cached { get; set; }
        public override EngineType EngineType { get { return EngineType.IronPython; } }

        public ScriptEngine Engine { get; private set; }
        public static Tuple<Stream, System.Text.Encoding> DefaultOutputStreamConfig {
            get {
                return (Tuple<Stream, System.Text.Encoding>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.IronPythonEngineDefaultStreamCfgKey);
            }

            set {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.IronPythonEngineDefaultStreamCfgKey, value);
            }
        }

        public IronPythonEngine() : base() { }

        public override void Init(ref ScriptRuntime runtime) {
            Id = runtime.ScriptData.CommandExtension;

            // If the command required a fullframe engine
            // or if the command required a clean engine
            // of if the user is asking to refresh the cached engine for the command,
            NeedsNew = runtime.NeedsFullFrameEngine || runtime.NeedsCleanEngine || runtime.NeedsRefreshedEngine;

            Cached = false;
        }

        public override void Setup(ref ScriptRuntime runtime) {
            if (!Cached) {
                var flags = new Dictionary<string, object>();

                // default flags
                flags["LightweightScopes"] = true;

                if (runtime.NeedsFullFrameEngine) {
                    flags["Frames"] = true;
                    flags["FullFrames"] = true;
                }

                Engine = IronPython.Hosting.Python.CreateEngine(flags);

                // also, allow access to the PyRevitLoader internals
                Engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);

                // also, allow access to the PyRevitRuntime internals
                Engine.Runtime.LoadAssembly(typeof(ScriptExecutor).Assembly);

                // reference RevitAPI and RevitAPIUI
                Engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
                Engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

                // save the default stream for later resetting the streams
                DefaultOutputStreamConfig = new Tuple<Stream, System.Text.Encoding>(Engine.Runtime.IO.OutputStream, Engine.Runtime.IO.OutputEncoding);

                // setup stdlib
                SetupStdlib(Engine);
            }

            SetupStreams(ref runtime);
            SetupBuiltins(ref runtime);
            SetupSearchPaths(ref runtime);
            SetupArguments(ref runtime);
        }

        public override void Shutdown() {
            CleanScopes();
            CleanupEngineBuiltins();
            CleanupStreams();
            _commandBuiltins = null;
            _scopes = null;
        }

        public ScriptScope GetNewScope() {
            var scope = Engine.CreateScope();
            _scopes.Add(scope);
            return scope;
        }

        private void SetupStdlib(ScriptEngine engine) {
            // ask PyRevitLoader to add it's resource ZIP file that contains the IronPython
            // standard library to this engine
            var tempExec = new PyRevitLoader.ScriptExecutor();
            tempExec.AddEmbeddedLib(engine);
        }

        private void SetupStreams(ref ScriptRuntime runtime) {
            Engine.Runtime.IO.SetOutput(runtime.OutputStream, System.Text.Encoding.UTF8);
        }

        private void SetupBuiltins(ref ScriptRuntime runtime) {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(Engine);

            // Let commands know if they're being run in a cached engine
            builtin.SetVariable("__cachedengine__", Cached);

            // Add current engine manager to builtins
            builtin.SetVariable("__ipyenginemanager__", this);

            // Add this script executor to the the builtin to be globally visible everywhere
            // This support pyrevit functionality to ask information about the current executing command
            builtin.SetVariable("__externalcommand__", runtime);

            // Add host application handle to the builtin to be globally visible everywhere
            if (runtime.UIApp != null)
                builtin.SetVariable("__revit__", runtime.UIApp);
            else if (runtime.UIControlledApp != null)
                builtin.SetVariable("__revit__", runtime.UIControlledApp);
            else if (runtime.App != null)
                builtin.SetVariable("__revit__", runtime.App);
            else
                builtin.SetVariable("__revit__", null);

            // Adding data provided by IExternalCommand.Execute
            builtin.SetVariable("__commanddata__", runtime.CommandData);
            builtin.SetVariable("__elements__", runtime.SelectedElements);

            // Adding information on the command being executed
            builtin.SetVariable("__commandpath__", Path.GetDirectoryName(runtime.ScriptData.ScriptPath));
            builtin.SetVariable("__configcommandpath__", Path.GetDirectoryName(runtime.ScriptData.ConfigScriptPath));
            builtin.SetVariable("__commandname__", runtime.ScriptData.CommandName);
            builtin.SetVariable("__commandbundle__", runtime.ScriptData.CommandBundle);
            builtin.SetVariable("__commandextension__", runtime.ScriptData.CommandExtension);
            builtin.SetVariable("__commanduniqueid__", runtime.ScriptData.CommandUniqueId);
            builtin.SetVariable("__forceddebugmode__", runtime.DebugMode);
            builtin.SetVariable("__shiftclick__", runtime.ConfigMode);

            // Add reference to the results dictionary
            // so the command can add custom values for logging
            builtin.SetVariable("__result__", runtime.GetResultsDictionary());

            // EVENT HOOKS BUILTINS ----------------------------------------------------------------------------------
            // set event arguments for engine
            builtin.SetVariable("__eventsender__", runtime.EventSender);
            builtin.SetVariable("__eventargs__", runtime.EventArgs);


            // CUSTOM BUILTINS ---------------------------------------------------------------------------------------
            var commandBuiltins = runtime.GetBuiltInVariables();
            if (commandBuiltins != null)
                foreach (KeyValuePair<string, object> data in commandBuiltins) {
                    _commandBuiltins.Add(data.Key);
                    builtin.SetVariable(data.Key, (object)data.Value);
                }
        }

        private void SetupSearchPaths(ref ScriptRuntime runtime) {
            // process search paths provided to executor
            Engine.SetSearchPaths(runtime.ModuleSearchPaths);
        }

        private void SetupArguments(ref ScriptRuntime runtime) {
            // setup arguments (sets sys.argv)
            // engine.Setup.Options["Arguments"] = arguments;
            // engine.Runtime.Setup.HostArguments = new List<object>(arguments);
            var sysmodule = Engine.GetSysModule();
            var pythonArgv = new IronPython.Runtime.List();
            pythonArgv.extend(runtime.Arguments);
            sysmodule.SetVariable("argv", pythonArgv);
        }

        private void CleanScopes() {
            // cleaning removes all references to revit content that's been casualy stored in global-level
            // variables and prohibit the GC from cleaning them up and releasing memory
            var scopeCleaerScript = Engine.CreateScriptSourceFromString(
                "for __deref in dir():\n" +
                "    if not __deref.startswith('__'):\n" +
                "        del globals()[__deref]");
            scopeCleaerScript.Compile();

            foreach (ScriptScope scope in _scopes)
                scopeCleaerScript.Execute(scope);
        }

        private void CleanupEngineBuiltins() {
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(Engine);

            builtin.SetVariable("__cachedengine__", null);
            builtin.SetVariable("__ipyenginemanager__", null);
            builtin.SetVariable("__externalcommand__", null);
            builtin.SetVariable("__commanddata__", null);
            builtin.SetVariable("__elements__", null);
            builtin.SetVariable("__commandpath__", null);
            builtin.SetVariable("__configcommandpath__", null);
            builtin.SetVariable("__commandname__", null);
            builtin.SetVariable("__commandbundle__", null);
            builtin.SetVariable("__commandextension__", null);
            builtin.SetVariable("__commanduniqueid__", null);
            builtin.SetVariable("__forceddebugmode__", null);
            builtin.SetVariable("__shiftclick__", null);

            builtin.SetVariable("__result__", null);

            builtin.SetVariable("__eventsender__", null);
            builtin.SetVariable("__eventargs__", null);

            // cleanup all data set by command custom builtins
            if (_commandBuiltins.Count > 0)
                foreach (string builtinVarName in _commandBuiltins)
                    builtin.SetVariable(builtinVarName, null);
        }

        private void CleanupStreams() {
            // Remove IO streams references so GC can collect
            Tuple<Stream, System.Text.Encoding> outStream = DefaultOutputStreamConfig;
            if (outStream != null) {
                Engine.Runtime.IO.SetOutput(outStream.Item1, outStream.Item2);
                outStream.Item1.Dispose();
            }
        }
    }
}
