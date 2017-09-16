using System;
using System.IO;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Collections.Generic;
using System.Windows.Forms;


namespace PyRevitBaseClasses
{
    public class EngineManager
    {
        private readonly UIApplication _revit;

        public EngineManager(UIApplication revit)
        {
            _revit = revit;
        }

        public ScriptEngine GetEngine(ref PyRevitCommand pyrvtCmd)
        {
            // If the command required a clean engine, make a clean one
            if (pyrvtCmd.NeedsCleanEngine)
                return CreateNewEngine(ref pyrvtCmd);

            // If the command required a clean engine, make a clean one
            if (pyrvtCmd.NeedsFullFrameEngine)
                return CreateNewEngine(ref pyrvtCmd, fullframe:true);

            // if the user is asking to refresh the cached engine for the command,
            // then update the engine and save in cache
            if (pyrvtCmd.NeedsRefreshedEngine)
                return GetCachedEngine(ref pyrvtCmd, true);
            else
                // if not above, get/create cached engine
                return GetCachedEngine(ref pyrvtCmd);

        }

        public Dictionary<string, ScriptEngine> EngineDict
        {
            get
            {
                var engineDict = (Dictionary<string, ScriptEngine>) AppDomain.CurrentDomain.GetData(EnvDictionaryKeys.docEngineDict);

                if (engineDict == null)
                    engineDict = ClearEngines();

                return engineDict;
            }
        }

        public Dictionary<string, ScriptEngine> ClearEngines()
        {
            var engineDict = new Dictionary<string, ScriptEngine>();
            AppDomain.CurrentDomain.SetData(EnvDictionaryKeys.docEngineDict, engineDict);

            return engineDict;
        }

        private ScriptEngine CreateNewEngine(ref PyRevitCommand pyrvtCmd, bool fullframe=false)
        {
            var flags = new Dictionary<string, object>(){{ "LightweightScopes", true }};

            if (fullframe)
            {
                // Disabling all frames to avoid the memory leak issue
                // that would increase the % of time spent in GC dramatically
                // Tried these options together and made the runtime much slower
                //  { "GCStress", 0 },
                //  { "MaxRecursion", 0 },
                flags["Frames"] = true;
                flags["FullFrames"] = true;
            }
                
            var engine = IronPython.Hosting.Python.CreateEngine(flags);

            // reference RevitAPI and RevitAPIUI
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.DB.Document).Assembly);
            engine.Runtime.LoadAssembly(typeof(Autodesk.Revit.UI.TaskDialog).Assembly);

            // also, allow access to the RPL internals
            engine.Runtime.LoadAssembly(typeof(PyRevitBaseClasses.ScriptExecutor).Assembly);

            SetupBuiltins(engine, ref pyrvtCmd, false);

            return engine;
        }

        private ScriptEngine CreateNewCachedEngine(ref PyRevitCommand pyrvtCmd)
        {
            var newEngine = CreateNewEngine(ref pyrvtCmd);
            this.EngineDict[pyrvtCmd.CommandExtension] = newEngine;
            return newEngine;
        }

        private ScriptEngine GetCachedEngine(ref PyRevitCommand pyrvtCmd, bool refresh=false)
        {
            if (!refresh && this.EngineDict.ContainsKey(pyrvtCmd.CommandExtension))
            {
                var existingEngine = this.EngineDict[pyrvtCmd.CommandExtension];
                SetupBuiltins(existingEngine, ref pyrvtCmd, true);
                return existingEngine;
            }
            else
            {
                return CreateNewCachedEngine(ref pyrvtCmd);
            }
        }

        private void SetupBuiltins(ScriptEngine engine, ref PyRevitCommand pyrvtCmd, bool cachedEngine)
        {
            // BUILTINS -----------------------------------------------------------------------------------------------
            // Get builtin to add custom variables
            var builtin = IronPython.Hosting.Python.GetBuiltinModule(engine);

            // Add current IronPython engine to builtins
            builtin.SetVariable("__ipyengine__", engine);

            // Add current engine manager to builtins
            builtin.SetVariable("__ipyenginemanager__", this);

            // Let commands know if they're being run in a cached engine
            builtin.SetVariable("__cachedengine__", cachedEngine);

            // Adding output window handle (__window__ is for backwards compatibility)
            builtin.SetVariable("__window__", pyrvtCmd.OutputWindow);
            builtin.SetVariable("__output__", pyrvtCmd.OutputWindow);

            // Adding output window stream
            builtin.SetVariable("__outputstream__", pyrvtCmd.OutputStream);

            // Add host application handle to the builtin to be globally visible everywhere
            builtin.SetVariable("__revit__", _revit);

            // Add handles to current document and ui document
            if (_revit.ActiveUIDocument != null) {
                builtin.SetVariable("__activeuidoc__", _revit.ActiveUIDocument);
                builtin.SetVariable("__activedoc__", _revit.ActiveUIDocument.Document);
                builtin.SetVariable("__zerodoc__", false);
            }
            else {
                builtin.SetVariable("__activeuidoc__", (Object) null);
                builtin.SetVariable("__activedoc__", (Object) null);
                builtin.SetVariable("__zerodoc__", true);
            }

            // Add this script executor to the the builtin to be globally visible everywhere
            // This support pyrevit functionality to ask information about the current executing command
            builtin.SetVariable("__externalcommand__", pyrvtCmd);

            // Adding data provided by IExternalCommand.Execute
            builtin.SetVariable("__commanddata__", pyrvtCmd.CommandData);
            builtin.SetVariable("__elements__", pyrvtCmd.SelectedElements);

            builtin.SetVariable("__commandpath__", Path.GetDirectoryName(pyrvtCmd.OriginalScriptSourceFile));
            builtin.SetVariable("__alternatecommandpath__", Path.GetDirectoryName(pyrvtCmd.AlternateScriptSourceFile));
            builtin.SetVariable("__commandname__", pyrvtCmd.CommandName);
            builtin.SetVariable("__commandbundle__", pyrvtCmd.CommandBundle);
            builtin.SetVariable("__commandextension__", pyrvtCmd.CommandExtension);
            builtin.SetVariable("__commanduniqueid__", pyrvtCmd.CommandUniqueId);
            builtin.SetVariable("__forceddebugmode__", pyrvtCmd.DebugMode);
            builtin.SetVariable("__shiftclick__", pyrvtCmd.AlternateMode);
            builtin.SetVariable("__result__", pyrvtCmd.GetResultsDictionary());
        }

    }
}
