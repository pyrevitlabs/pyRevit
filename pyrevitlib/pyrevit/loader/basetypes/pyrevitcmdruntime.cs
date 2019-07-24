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
        Dynamo,
        Grasshopper
    }

    public class PyRevitCommandRuntime : IDisposable {
        private ExternalCommandData _commandData = null;
        private ElementSet _elements = null;

        private string _scriptSource = null;
        private string _alternateScriptSource = null;
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
        private bool _altScriptMode = false;
        private bool _execFromUI = false;

        private WeakReference<ScriptOutput> _scriptOutput = new WeakReference<ScriptOutput>(null);
        private WeakReference<ScriptOutputStream> _outputStream = new WeakReference<ScriptOutputStream>(null);

        // get the state of variables before command execution; the command could potentially change the values
        private EnvDictionary _envDict = new EnvDictionary();

        private int _execResults = 0;
        private string _ipyTrace = "";
        private string _clrTrace = "";
        private string _cpyTrace = "";
        private Dictionary<string, string> _resultsDict = null;


        public PyRevitCommandRuntime(ExternalCommandData cmdData,
                                     ElementSet elements,
                                     string scriptSource,
                                     string alternateScriptSource,
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
                                     bool altScriptMode,
                                     bool executedFromUI) {
            _commandData = cmdData;
            _elements = elements;

            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
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
            _altScriptMode = altScriptMode;
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
                if (_altScriptMode)
                    return _alternateScriptSource;
                else
                    return _scriptSource;
            }
        }

        public string OriginalScriptSourceFile {
            get {
                return _scriptSource;
            }
        }

        public string AlternateScriptSourceFile {
            get {
                return _alternateScriptSource;
            }
        }

        public EngineType EngineType {
            get {
                string firstLine = "";
                using (StreamReader reader = new StreamReader(ScriptSourceFile)) {
                    firstLine = reader.ReadLine();
                }

                if (firstLine.Contains("python3") || firstLine.Contains("cpython"))
                    return EngineType.CPython;
                else
                    return EngineType.IronPython;
            }
        }

        public List<string> ModuleSearchPaths {
            get {
                return new List<string>(_syspaths.Split(';'));
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

        public bool AlternateMode {
            get {
                return _altScriptMode;
            }
        }

        public bool ExecutedFromUI {
            get {
                return _execFromUI;
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
                        _envDict.pyRevitVersion,
                        EngineType == EngineType.CPython ? _envDict.pyRevitCpyVersion : _envDict.pyRevitIpyVersion,
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

        public string IronPythonTraceBack {
            get {
                return _ipyTrace;
            }
            set {
                _ipyTrace = value;
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
                else if (IronPythonTraceBack != string.Empty && ClrTraceBack != string.Empty) {
                    return string.Format("{0}\n\n{1}", IronPythonTraceBack, ClrTraceBack);
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
                return _commandData.Application;
            }
        }

        public Application App {
            get {
                return _commandData.Application.Application;
            }
        }

        public string PyRevitVersion {
            get {
                return _envDict.pyRevitVersion;
            }
        }

        public string SessionUUID {
            get {
                return _envDict.sessionUUID;
            }
        }

        public LogEntry MakeLogEntry() {
            // setup a new log entry
            return new LogEntry(App.Username,
                                App.VersionNumber,
                                App.VersionBuild,
                                SessionUUID,
                                PyRevitVersion,
                                DebugMode,
                                AlternateMode,
                                CommandName,
                                CommandBundle,
                                CommandExtension,
                                CommandUniqueId,
                                ScriptSourceFile,
                                ExecutionResult,
                                GetResultsDictionary(),
                                new TraceInfo {
                                    engine = new EngineInfo {
                                        type = EngineType == EngineType.CPython ? "cpython" : "ironpython",
                                        version = Convert.ToString(
                                            EngineType == EngineType.CPython ?
                                                  _envDict.pyRevitCpyVersion : _envDict.pyRevitIpyVersion
                                                  ),
                                        syspath = ModuleSearchPaths
                                    },
                                    message = TraceMessage
                                });
        }

        public void Dispose() {
            _scriptOutput = null;
            _outputStream = null;
            _resultsDict = null;
        }
    }
}
