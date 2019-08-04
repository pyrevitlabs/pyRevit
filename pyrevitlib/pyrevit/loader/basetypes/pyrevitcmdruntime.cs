using System;
using System.Collections.Generic;
using System.IO;

using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.ApplicationServices;

namespace PyRevitBaseClasses {
    public enum EngineType {
        IronPython,
        CPython,
        CSharp,
        Invoke,
        VisualBasic,
        IronRuby,
        Dynamo,
        Grasshopper
    }

    public class PyRevitCommandRuntime : IDisposable {
        private ExternalCommandData _commandData = null;
        private UIApplication _uiApp = null;
        private Application _app = null;
        private ElementSet _elements = null;

        private string _scriptSource = null;
        private string _configScriptSource = null;
        private string _syspaths = null;
        private string[] _arguments = null;
        private string _helpSource = null;
        private string _cmdName = null;
        private string _cmdBundle = null;
        private string _cmdExtension = null;
        private string _cmdUniqueName = null;
        private bool _needsCleanEngine = false;
        private bool _needsFullFrameEngine = false;

        private bool _refreshEngine = false;
        private bool _forcedDebugMode = false;
        private bool _configScriptMode = false;
        private bool _execFromUI = false;

        private WeakReference<ScriptOutput> _scriptOutput = new WeakReference<ScriptOutput>(null);
        private WeakReference<ScriptOutputStream> _outputStream = new WeakReference<ScriptOutputStream>(null);

        // get the state of variables before command execution; the command could potentially change the values
        private EnvDictionary _envDict = new EnvDictionary();

        private int _execResults = 0;
        private string _ironLangTrace = "";
        private string _clrTrace = "";
        private string _cpyTrace = "";
        private Dictionary<string, string> _resultsDict = null;

        private IDictionary<string, object> _builtins = new Dictionary<string, object>();

        public PyRevitCommandRuntime(ExternalCommandData cmdData,
                                     ElementSet elements,
                                     string scriptSource,
                                     string configScriptSource,
                                     string syspaths,
                                     string[] arguments,
                                     string helpSource,
                                     string cmdName,
                                     string cmdBundle,
                                     string cmdExtension,
                                     string cmdUniqueName,
                                     bool needsCleanEngine,
                                     bool needsFullFrameEngine,
                                     bool refreshEngine,
                                     bool forcedDebugMode,
                                     bool configScriptMode,
                                     bool executedFromUI) {
            _commandData = cmdData;
            _elements = elements;

            _scriptSource = scriptSource;
            _configScriptSource = configScriptSource;
            _syspaths = syspaths;
            _arguments = arguments;

            _helpSource = helpSource;
            _cmdName = cmdName;
            _cmdBundle = cmdBundle;
            _cmdExtension = cmdExtension;
            _cmdUniqueName = cmdUniqueName;
            _needsCleanEngine = Convert.ToBoolean(needsCleanEngine);
            _needsFullFrameEngine = Convert.ToBoolean(needsFullFrameEngine);

            _refreshEngine = refreshEngine;
            _forcedDebugMode = forcedDebugMode;
            _configScriptMode = configScriptMode;
            _execFromUI = executedFromUI;
        }

        public ExternalCommandData CommandData {
            get {
                return _commandData;
            }
        }

        public ElementSet SelectedElements {
            get {
                return _elements;
            }
        }

        public string ScriptSourceFile {
            get {
                if (_configScriptMode && (_configScriptSource != null || _configScriptSource != string.Empty))
                    return _configScriptSource;
                else
                    return _scriptSource;
            }
        }

        public string OriginalScriptSourceFile {
            get {
                return _scriptSource;
            }
        }

        public string ConfigScriptSourceFile {
            get {
                return _configScriptSource;
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
                    }

                    if (firstLine.Contains("python3") || firstLine.Contains("cpython"))
                        return EngineType.CPython;
                    else
                        return EngineType.IronPython;
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

                if (CommandBundle != null) {
                    var bundleName = CommandBundle.ToLower();
                    if (bundleName.EndsWith(".invokebutton")) {
                        return EngineType.Invoke;
                    }
                }

                // should not get here
                throw new Exception("Unknown script type.");
            }
        }

        public List<string> ModuleSearchPaths {
            get {
                return new List<string>(_syspaths.Split(ExternalConfig.defaultsep));
            }
        }

        public List<string> Arguments {
            get {
                var argv = new List<string>();

                // add script source as the first argument
                argv.Add(ScriptSourceFile);

                // if other arguments are available, add those as well
                if (_arguments != null)
                    argv.AddRange(_arguments);

                return argv;
            }
        }

        public string HelpSource {
            get {
                return _helpSource;
            }
        }

        public string CommandName {
            get {
                return _cmdName;
            }
        }

        public string CommandUniqueId {
            get {
                return _cmdUniqueName;
            }
        }

        public string CommandBundle {
            get {
                return _cmdBundle;
            }
        }

        public string CommandExtension {
            get {
                return _cmdExtension;
            }
        }

        public bool NeedsCleanEngine {
            get {
                return _needsCleanEngine;
            }
        }

        public bool NeedsFullFrameEngine {
            get {
                return _needsFullFrameEngine;
            }
        }

        public bool NeedsRefreshedEngine {
            get {
                return _refreshEngine;
            }
        }

        public bool DebugMode {
            get {
                return _forcedDebugMode;
            }
        }

        public bool ConfigMode {
            get {
                return _configScriptMode;
            }
        }

        public bool ExecutedFromUI {
            get {
                return _execFromUI;
            }
        }

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
                    newOutput.OutputTitle = _cmdName;

                    // Set window identity to the command unique identifier
                    newOutput.OutputId = _cmdUniqueName;

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

        public int ExecutionResult {
            get {
                return _execResults;
            }
            set {
                _execResults = value;
            }
        }

        public string IronLanguageTraceBack {
            get {
                return _ironLangTrace;
            }
            set {
                _ironLangTrace = value;
            }
        }

        public string ClrTraceBack {
            get {
                return _clrTrace;
            }
            set {
                _clrTrace = value;
            }
        }

        public string CpythonTraceBack {
            get {
                return _cpyTrace;
            }
            set {
                _cpyTrace = value;
            }
        }

        public string TraceMessage {
            get {
                // return the trace message based on the engine type
                if (EngineType == EngineType.CPython) {
                    return CpythonTraceBack;
                }
                else if (IronLanguageTraceBack != string.Empty && ClrTraceBack != string.Empty) {
                    return string.Format("{0}\n\n{1}", IronLanguageTraceBack, ClrTraceBack);
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

        public UIApplication UIApp {
            get {
                if (_commandData != null)
                    return _commandData.Application;
                else if (_uiApp != null)
                    return _uiApp;
                return null;
            }

            set {
                _uiApp = value;
            }
        }

        public Application App {
            get {
                if (_commandData != null)
                    return _commandData.Application.Application;
                else if (_uiApp != null)
                    return _uiApp.Application;
                else if (_app != null)
                    return _app;
                return null;
            }

            set {
                _app = value;
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

        public TelemetryRecord MakeTelemetryRecord() {
            // setup a new telemetry record
            return new TelemetryRecord(
                App.Username,
                App.VersionNumber,
                App.VersionBuild,
                SessionUUID,
                PyRevitVersion,
                CloneName,
                DebugMode,
                ConfigMode,
                ExecutedFromUI,
                NeedsCleanEngine,
                NeedsFullFrameEngine,
                CommandName,
                CommandBundle,
                CommandExtension,
                CommandUniqueId,
                ScriptSourceFile,
                DocumentName,
                DocumentPath,
                ExecutionResult,
                GetResultsDictionary(),
                new TraceInfo {
                    engine = new EngineInfo {
                        type = EngineType.ToString().ToLower(),
                        version = Convert.ToString(
                            EngineType == EngineType.CPython ?
                                    _envDict.PyRevitCPYVersion : _envDict.PyRevitIPYVersion
                                    ),
                        syspath = ModuleSearchPaths
                    },
                    message = TraceMessage
                });
        }

        public IDictionary<string, object> GetBuiltInVariables() {
            return _builtins;
        }

        public void SetBuiltInVariables(IDictionary<string, object> builtins) {
            _builtins = builtins;
        }

        public void Dispose() {
            _uiApp = null;
            _scriptOutput = null;
            _outputStream = null;
            _resultsDict = null;
            _builtins = null;
        }
    }
}
