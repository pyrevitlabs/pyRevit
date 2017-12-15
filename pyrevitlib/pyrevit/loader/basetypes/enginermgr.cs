using System;
using System.IO;
using Microsoft.Scripting.Hosting;
using System.Collections.Generic;


namespace PyRevitBaseClasses
{
    public class EngineManager
    {
        public EngineManager() {}

        public ScriptEngine GetEngine(ref PyRevitCommandRuntime pyrvtCmd)
        {
            ScriptEngine engine;
            bool cachedEngine = false;

            // If the command required a fullframe engine
            if (pyrvtCmd.NeedsFullFrameEngine)
                engine = CreateNewEngine(ref pyrvtCmd, fullframe: true);

            // If the command required a clean engine
            else if (pyrvtCmd.NeedsCleanEngine)
                engine = CreateNewEngine(ref pyrvtCmd);

            // if the user is asking to refresh the cached engine for the command,
            // then update the engine and save in cache
            else if (pyrvtCmd.NeedsRefreshedEngine)
                engine = RefreshCachedEngine(ref pyrvtCmd);

            // if not above, get/create cached engine
            else {
                engine = GetCachedEngine(ref pyrvtCmd);
                cachedEngine = true;
            }

            // now that the engine is ready, setup the builtins and io streams
            SetupStreams(engine, pyrvtCmd.OutputStream);
            SetupBuiltins(engine, ref pyrvtCmd, cachedEngine);
            SetupSearchPaths(engine, pyrvtCmd.ModuleSearchPaths);

            return engine;
        }

        public Dictionary<string, ScriptEngine> EngineDict
        {
            get
            {
                var engineDict = (Dictionary<string, ScriptEngine>) AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitIpyEnginesDictKey);

                if (engineDict == null)
                    engineDict = ClearEngines();

                return engineDict;
            }
        }

        public Tuple<Stream, System.Text.Encoding> DefaultOutputStreamConfig
        {
            get
            {
                return (Tuple<Stream, System.Text.Encoding>)AppDomain.CurrentDomain.GetData(DomainStorageKeys.pyRevitIpyEngineDefaultStreamCfgKey);
            }

            set
            {
                AppDomain.CurrentDomain.SetData(DomainStorageKeys.pyRevitIpyEngineDefaultStreamCfgKey, value);
            }
        }

        public Dictionary<string, ScriptEngine> ClearEngines()
        {
            var newEngineDict = new Dictionary<string, ScriptEngine>();
            AppDomain.CurrentDomain.SetData(DomainStorageKeys.pyRevitIpyEnginesDictKey, newEngineDict);

            return newEngineDict;
        }

        public void CleanupEngine(ScriptEngine engine)
        {
            CleanupEngineBuiltins(engine);
            CleanupStreams(engine);
        }

        private ScriptEngine CreateNewEngine(ref PyRevitCommandRuntime pyrvtCmd, bool fullframe=false)
        {
            var flags = new Dictionary<string, object>();

            // default flags
            flags["LightweightScopes"] = true;

            if (fullframe)
            {
                flags["Frames"] = true;
                flags["FullFrames"] = true;
            }
                
            var engine = IronPython.Hosting.Python.CreateEngine(flags);

            // also, allow access to the PyRevitLoader internals
            engine.Runtime.LoadAssembly(typeof(PyRevitLoader.ScriptExecutor).Assembly);

            // also, allow access to the PyRevitBaseClasses internals
            engine.Runtime.LoadAssembly(typeof(PyRevitBaseClasses.ScriptExecutor).Assembly);

            // reference RevitAPI and RevitAPIUI
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // save the default stream for later resetting the streams
            DefaultOutputStreamConfig = new Tuple<Stream, System.Text.Encoding>(engine.Runtime.IO.OutputStream, engine.Runtime.IO.OutputEncoding);

            // setup stdlib
            SetupStdlib(engine);

            return engine;
        }

        private ScriptEngine CreateNewCachedEngine(ref PyRevitCommandRuntime pyrvtCmd)
        {
            var newEngine = CreateNewEngine(ref pyrvtCmd);
            this.EngineDict[pyrvtCmd.CommandExtension] = newEngine;
            return newEngine;
        }

        private ScriptEngine GetCachedEngine(ref PyRevitCommandRuntime pyrvtCmd)
        {
            if (this.EngineDict.ContainsKey(pyrvtCmd.CommandExtension))
            {
                var existingEngine = this.EngineDict[pyrvtCmd.CommandExtension];
                return existingEngine;
            }
            else
            {
                return CreateNewCachedEngine(ref pyrvtCmd);
            }
        }

        private ScriptEngine RefreshCachedEngine(ref PyRevitCommandRuntime pyrvtCmd)
        {
            return CreateNewCachedEngine(ref pyrvtCmd);
        }

        private void SetupStdlib(ScriptEngine engine)
        {
            // ask PyRevitLoader to add it's resource ZIP file that contains the IronPython
            // standard library to this engine
            var tempExec = new PyRevitLoader.ScriptExecutor();
            tempExec.AddEmbeddedLib(engine);
        }

        private void SetupSearchPaths(ScriptEngine engine, string[] searchPaths)
        {
            // Process search paths provided to executor
            // syspaths variable is a string of paths separated by ';'. Split syspath and update the search paths
            engine.SetSearchPaths(searchPaths);
        }

        private void SetupBuiltins(ScriptEngine engine, ref PyRevitCommandRuntime pyrvtCmd, bool cachedEngine)
        {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);

            // Let commands know if they're being run in a cached engine
            builtin.SetVariable("__cachedengine__", cachedEngine);

            // Add current engine manager to builtins
            builtin.SetVariable("__ipyenginemanager__", this);

            // Add this script executor to the the builtin to be globally visible everywhere
            // This support pyrevit functionality to ask information about the current executing command
            builtin.SetVariable("__externalcommand__", pyrvtCmd);

            // Add host application handle to the builtin to be globally visible everywhere
            builtin.SetVariable("__revit__", pyrvtCmd.UIApp);

            // Adding data provided by IExternalCommand.Execute
            builtin.SetVariable("__commanddata__",          pyrvtCmd.CommandData);
            builtin.SetVariable("__elements__",             pyrvtCmd.SelectedElements);

            // Adding information on the command being executed
            builtin.SetVariable("__commandpath__",          Path.GetDirectoryName(pyrvtCmd.OriginalScriptSourceFile));
            builtin.SetVariable("__alternatecommandpath__", Path.GetDirectoryName(pyrvtCmd.AlternateScriptSourceFile));
            builtin.SetVariable("__commandname__",          pyrvtCmd.CommandName);
            builtin.SetVariable("__commandbundle__",        pyrvtCmd.CommandBundle);
            builtin.SetVariable("__commandextension__",     pyrvtCmd.CommandExtension);
            builtin.SetVariable("__commanduniqueid__",      pyrvtCmd.CommandUniqueId);
            builtin.SetVariable("__forceddebugmode__",      pyrvtCmd.DebugMode);
            builtin.SetVariable("__shiftclick__",           pyrvtCmd.AlternateMode);

            // Add reference to the results dictionary
            // so the command can add custom values for logging
            builtin.SetVariable("__result__",               pyrvtCmd.GetResultsDictionary());
        }

        private void SetupStreams(ScriptEngine engine, ScriptOutputStream outStream)
        {
            engine.Runtime.IO.SetOutput(outStream, System.Text.Encoding.UTF8);
        }

        private void CleanupEngineBuiltins(ScriptEngine engine)
        {
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);

            builtin.SetVariable("__cachedengine__",         (Object)null);
            builtin.SetVariable("__ipyenginemanager__",     (Object)null);
            builtin.SetVariable("__externalcommand__",      (Object)null);
            builtin.SetVariable("__commanddata__",          (Object)null);
            builtin.SetVariable("__elements__",             (Object)null);
            builtin.SetVariable("__commandpath__",          (Object)null);
            builtin.SetVariable("__alternatecommandpath__", (Object)null);
            builtin.SetVariable("__commandname__",          (Object)null);
            builtin.SetVariable("__commandbundle__",        (Object)null);
            builtin.SetVariable("__commandextension__",     (Object)null);
            builtin.SetVariable("__commanduniqueid__",      (Object)null);
            builtin.SetVariable("__forceddebugmode__",      (Object)null);
            builtin.SetVariable("__shiftclick__",           (Object)null);
            builtin.SetVariable("__result__",               (Object)null);
        }

        private void CleanupStreams(ScriptEngine engine)
        {
            // Remove IO streams references so GC can collect
            Tuple<Stream, System.Text.Encoding> outStream = this.DefaultOutputStreamConfig;
            if (outStream != null)
            {
                engine.Runtime.IO.SetOutput(outStream.Item1, outStream.Item2);
                outStream.Item1.Dispose();
            }
        }
    }
}
