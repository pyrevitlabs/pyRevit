using System;
using System.Collections.Generic;
using System.IO;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.ApplicationServices;

namespace PyRevitLabs.PyRevit.Runtime {
    public enum InterfaceType {
        ExternalCommand,
        EventHandler,
    }

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

    public class ScriptData {
        public string ScriptPath;
        public string ConfigScriptPath;
        public string CommandUniqueId;
        public string CommandName;
        public string CommandBundle;
        public string CommandExtension;

        public string HelpSource;
    }


    public class ScriptRuntime : IDisposable {
        // app handles
        private UIApplication _uiApp = null;
        private Application _app = null;

        // for commands that are events
        private object _eventSender = null;

        // output window and stream
        private WeakReference<ScriptOutput> _scriptOutput = new WeakReference<ScriptOutput>(null);
        private WeakReference<ScriptOutputStream> _outputStream = new WeakReference<ScriptOutputStream>(null);

        // get the state of variables before command execution; the command could potentially change the values
        private EnvDictionary _envDict = new EnvDictionary();

        // dict for command result data
        private Dictionary<string, string> _resultsDict = null;

        // dict to store custom builtin variables
        // engine reads this and sets the vars in scope
        private IDictionary<string, object> _builtins = new Dictionary<string, object>();

        public ScriptRuntime(
                ExternalCommandData cmdData,
                ElementSet elements,
                ScriptData scriptData,
                string[] searchpaths,
                string[] arguments,
                bool needsCleanEngine,
                bool needsFullFrameEngine,
                bool needsPersistentEngine,
                bool refreshEngine,
                bool forcedDebugMode,
                bool configScriptMode,
                bool executedFromUI) {
            // set data
            ScriptData = scriptData;

            // set exec parameters
            NeedsRefreshedEngine = refreshEngine;
            DebugMode = forcedDebugMode;
            ConfigMode = configScriptMode;
            ExecutedFromUI = executedFromUI;

            // set IronPython engine configs
            NeedsCleanEngine = needsCleanEngine;
            NeedsFullFrameEngine = needsFullFrameEngine;
            NeedsPersistentEngine = needsPersistentEngine;

            // set execution hooks
            CommandData = cmdData;
            SelectedElements = elements;
            // event info
            EventSender = null;
            EventArgs = null;

            // set search paths
            ModuleSearchPaths = new List<string>();
            if (searchpaths != null)
                ModuleSearchPaths.AddRange(searchpaths);

            // set argument list
            var argv = new List<string>();
            // add script source as the first argument
            argv.Add(ScriptSourceFile);
            // if other arguments are available, add those as well
            if (arguments != null)
                argv.AddRange(arguments);
            Arguments = argv;

            ExecutionResult = ExecutionResultCodes.Succeeded;
            IronLanguageTraceBack = string.Empty;
            CLRTraceBack = string.Empty;
            CpythonTraceBack = string.Empty;
        }

        public ScriptData ScriptData { get; private set; }

        public ExternalCommandData CommandData { get; private set; }

        public ElementSet SelectedElements { get; private set; }

        public string ScriptSourceFile {
            get {
                if (ConfigMode && (ScriptData.ConfigScriptPath != null || ScriptData.ConfigScriptPath != string.Empty))
                    return ScriptData.ConfigScriptPath;
                else
                    return ScriptData.ScriptPath;
            }
        }

        public InterfaceType InterfaceType {
            get {
                if (EventSender != null || EventArgs != null)
                    return InterfaceType.EventHandler;

                return InterfaceType.ExternalCommand;
            }
        }

        public EngineType EngineType {
            get {
                // determine engine necessary to run this script
                var scriptFile = ScriptSourceFile.ToLower();
                if (scriptFile.EndsWith(".py")) {
                    string firstLine = "";
                    using (StreamReader reader = new StreamReader(scriptFile)) {
                        firstLine = reader.ReadLine();

                        if (firstLine != null && (firstLine.Contains("python3") || firstLine.Contains("cpython")))
                            return EngineType.CPython;
                        else
                            return EngineType.IronPython;
                    }
                }
                else if (scriptFile.EndsWith(".cs")) {
                    return EngineType.CSharp;
                }
                else if (scriptFile.EndsWith(".vb")) {
                    return EngineType.VisualBasic;
                }
                else if (scriptFile.EndsWith(".rb")) {
                    return EngineType.IronRuby;
                }
                else if (scriptFile.EndsWith(".dyn")) {
                    return EngineType.Dynamo;
                }
                else if (scriptFile.EndsWith(".gh")) {
                    return EngineType.Grasshopper;
                }
                else if (scriptFile.EndsWith(".rfa")) {
                    return EngineType.Content;
                }

                if (ScriptData.CommandBundle != null) {
                    var bundleName = ScriptData.CommandBundle.ToLower();
                    if (bundleName.EndsWith(".invokebutton")) {
                        return EngineType.Invoke;
                    }
                }

                // should not get here
                throw new Exception("Unknown script type.");
            }
        }

        public List<string> ModuleSearchPaths { get; private set; }

        public List<string> Arguments { get; private set; }

        public object EventSender {
            get {
                return _eventSender;
            }

            set {
                _eventSender = value;
                if (_eventSender != null) {
                    // detemine sender type
                    if (_eventSender.GetType() == typeof(UIControlledApplication))
                        UIControlledApp = (UIControlledApplication)_eventSender;
                    else if (_eventSender.GetType() == typeof(UIApplication))
                        UIApp = (UIApplication)_eventSender;
                    else if (_eventSender.GetType() == typeof(ControlledApplication))
                        ControlledApp = (ControlledApplication)_eventSender;
                    else if (_eventSender.GetType() == typeof(Application))
                        App = (Application)_eventSender;
                }
            }
        }

        public object EventArgs { get; set; }

        public bool NeedsCleanEngine { get; private set; }

        public bool NeedsFullFrameEngine { get; private set; }

        public bool NeedsPersistentEngine { get; private set; }

        public bool NeedsRefreshedEngine { get; private set; }

        public bool DebugMode { get; private set; }

        public bool ConfigMode { get; private set; }

        public bool ExecutedFromUI { get; private set; }

        public string DocumentName {
            get {
                if (UIApp != null && UIApp.ActiveUIDocument != null)
                    return UIApp.ActiveUIDocument.Document.Title;
                else
                    return string.Empty;
            }
        }

        public string DocumentPath {
            get {
                if (UIApp != null && UIApp.ActiveUIDocument != null)
                    return UIApp.ActiveUIDocument.Document.PathName;
                else
                    return string.Empty;
            }
        }

        public ScriptOutput OutputWindow {
            get {
                // get ScriptOutput from the weak reference
                ScriptOutput output;
                var re = _scriptOutput.TryGetTarget(out output);
                if (re && output != null)
                    return output;
                else {
                    // Stating a new output window
                    var newOutput = new ScriptOutput(DebugMode, UIApp);

                    // Set output window title to command name
                    newOutput.OutputTitle = ScriptData.CommandName;

                    // Set window identity to the command unique identifier
                    newOutput.OutputId = ScriptData.CommandUniqueId;

                    // set window app version header
                    newOutput.AppVersion = string.Format(
                        "{0}:{1}:{2}",
                        _envDict.PyRevitVersion,
                        EngineType == EngineType.CPython ? _envDict.PyRevitCPYVersion : _envDict.PyRevitIPYVersion,
                        _envDict.RevitVersion
                        );

                    _scriptOutput = new WeakReference<ScriptOutput>(newOutput);
                    return newOutput;
                }
            }
        }

        public ScriptOutputStream OutputStream {
            get {
                // get ScriptOutputStream from the weak reference
                ScriptOutputStream outputStream;
                var re = _outputStream.TryGetTarget(out outputStream);
                if (re && outputStream != null)
                    return outputStream;
                else {
                    // Setup the output stream
                    ScriptOutputStream newStream = new ScriptOutputStream(this);
                    _outputStream = new WeakReference<ScriptOutputStream>(newStream);
                    return newStream;
                }
            }
        }

        public int ExecutionResult { get; set; }

        public string IronLanguageTraceBack { get; set; }

        public string CLRTraceBack { get; set; }

        public string CpythonTraceBack { get; set; }

        public string TraceMessage {
            get {
                // return the trace message based on the engine type
                if (EngineType == EngineType.CPython) {
                    return CpythonTraceBack;
                }
                else if (IronLanguageTraceBack != string.Empty && CLRTraceBack != string.Empty) {
                    return string.Format("{0}\n\n{1}", IronLanguageTraceBack, CLRTraceBack);
                }
                // or return empty if none
                return string.Empty;
            }
        }

        public Dictionary<string, string> GetResultsDictionary() {
            if (_resultsDict == null)
                _resultsDict = new Dictionary<string, string>();

            return _resultsDict;
        }

        public ControlledApplication ControlledApp { get; set; }

        public Application App {
            get {
                if (CommandData != null)
                    return CommandData.Application.Application;
                else if (UIApp != null)
                    return UIApp.Application;
                else if (_app != null)
                    return _app;
                return null;
            }

            set {
                _app = value;
            }
        }

        public UIControlledApplication UIControlledApp { get; set; }

        public UIApplication UIApp {
            get {
                if (CommandData != null)
                    return CommandData.Application;
                else if (_uiApp != null)
                    return _uiApp;
                return null;
            }

            set {
                _uiApp = value;
            }
        }

        public string PyRevitVersion {
            get {
                return _envDict.PyRevitVersion;
            }
        }

        public string CloneName {
            get {
                return _envDict.PyRevitClone;
            }
        }

        public string SessionUUID {
            get {
                return _envDict.SessionUUID;
            }
        }

        public ScriptTelemetryRecord MakeTelemetryRecord() {
            // setup a new telemetry record
            return new ScriptTelemetryRecord {
                username = App.Username,
                revit = App.VersionNumber,
                revitbuild = App.VersionBuild,
                sessionid = SessionUUID,
                pyrevit = PyRevitVersion,
                clone = CloneName,
                debug = DebugMode,
                config = ConfigMode,
                from_gui = ExecutedFromUI,
                clean_engine = NeedsCleanEngine,
                fullframe_engine = NeedsFullFrameEngine,
                commandname = ScriptData.CommandName,
                commandbundle = ScriptData.CommandBundle,
                commandextension = ScriptData.CommandExtension,
                commanduniquename = ScriptData.CommandUniqueId,
                scriptpath = ScriptSourceFile,
                docname = DocumentName,
                docpath = DocumentPath,
                resultcode = ExecutionResult,
                commandresults = GetResultsDictionary(),
                trace = new TraceInfo {
                    engine = new EngineInfo {
                        type = EngineType.ToString().ToLower(),
                        version = Convert.ToString(
                            EngineType == EngineType.CPython ?
                                    _envDict.PyRevitCPYVersion : _envDict.PyRevitIPYVersion
                                    ),
                        syspath = ModuleSearchPaths
                    },
                    message = TraceMessage
                }
            };
        }

        public IDictionary<string, object> GetBuiltInVariables() {
            return _builtins;
        }

        public void SetBuiltInVariables(IDictionary<string, object> builtins) {
            _builtins = builtins;
        }

        public void Dispose() {
            UIControlledApp = null;
            _uiApp = null;
            _app = null;
            _eventSender = null;
            EventArgs = null;
            _scriptOutput = null;
            _outputStream = null;
            _resultsDict = null;
            _builtins = null;
        }
    }
}
