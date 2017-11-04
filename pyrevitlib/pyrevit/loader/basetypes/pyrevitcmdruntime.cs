using System;
using System.Collections.Generic;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.ApplicationServices;


namespace PyRevitBaseClasses
{
	public class PyRevitCommandRuntime: IDisposable
	{
        private ExternalCommandData _commandData = null;
        private ElementSet _elements = null;

        private string _scriptSource = null;
        private string _alternateScriptSource = null;
        private string _syspaths = null;
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

        private WeakReference<ScriptOutput> _scriptOutput = new WeakReference<ScriptOutput>(null);
        private WeakReference<ScriptOutputStream> _outputStream = new WeakReference<ScriptOutputStream>(null);

        private int _execResults = 0;
        private Dictionary<String, String> _resultsDict = null;

        public PyRevitCommandRuntime(ExternalCommandData cmdData,
                                     ElementSet elements,
                                     string scriptSource,
                                     string alternateScriptSource,
                                     string syspaths,
                                     string helpSource,
                                     string cmdName,
                                     string cmdBundle,
                                     string cmdExtension,
                                     string cmdUniqueName,
                                     bool needsCleanEngine,
                                     bool needsFullFrameEngine,
                                     bool refreshEngine,
                                     bool forcedDebugMode,
                                     bool altScriptMode)
        {
            _commandData = cmdData;
            _elements = elements;

            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
            _syspaths = syspaths;
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
        }

        public ExternalCommandData CommandData
        {
            get
            {
                return _commandData;
            }
        }

        public ElementSet SelectedElements
        {
            get
            {
                return _elements;
            }
        }


        public string ScriptSourceFile
        {
            get
            {
                if (_altScriptMode)
                    return _alternateScriptSource;
                else
                    return _scriptSource;
            }
        }

        public string OriginalScriptSourceFile
        {
            get
            {
                return _scriptSource;
            }
        }

        public string AlternateScriptSourceFile
        {
            get
            {
                return _alternateScriptSource;
            }
        }

        public string[] ModuleSearchPaths
        {
            get
            {
                return _syspaths.Split(';');
            }
        }

        public string HelpSource
        {
            get
            {
                return _helpSource;
            }
        }

        public string CommandName
        {
            get
            {
                return _cmdName;
            }
        }

        public string CommandUniqueId
        {
            get
            {
                return _cmdUniqueName;
            }
        }

        public string CommandBundle
        {
            get
            {
                return _cmdBundle;
            }
        }

        public string CommandExtension
        {
            get
            {
                return _cmdExtension;
            }
        }

        public bool NeedsCleanEngine
        {
            get
            {
                return _needsCleanEngine;
            }
        }

        public bool NeedsFullFrameEngine
        {
            get
            {
                return _needsFullFrameEngine;
            }
        }

        public bool NeedsRefreshedEngine
        {
            get
            {
                return _refreshEngine;
            }
        }

        public bool DebugMode
        {
            get
            {
                return _forcedDebugMode;
            }
        }

        public bool AlternateMode
        {
            get
            {
                return _altScriptMode;
            }
        }

        public ScriptOutput OutputWindow
        {
            get
            {
                // get ScriptOutput from the weak reference
                ScriptOutput output;
                var re = _scriptOutput.TryGetTarget(out output);
                if (re && output != null)
                    return output;
                else
                {
                    // Stating a new output window
                    var newOutput = new ScriptOutput(DebugMode);
                    newOutput.Title = _cmdName;              // Set output window title to command name
                    newOutput.OutputId = _cmdUniqueName;     // Set window identity to the command unique identifier
                    _scriptOutput = new WeakReference<ScriptOutput>(newOutput);
                    return newOutput;
                }
            }
        }

        public ScriptOutputStream OutputStream
        {
            get
            {
                // get ScriptOutputStream from the weak reference
                ScriptOutputStream outputStream;
                var re = _outputStream.TryGetTarget(out outputStream);
                if (re && outputStream != null)
                    return outputStream;
                else
                {
                    // Setup the output stream
                    ScriptOutputStream newStream = new ScriptOutputStream(this);
                    _outputStream = new WeakReference<ScriptOutputStream>(newStream);
                    return newStream;
                }
            }
        }

        public int ExecutionResult
        {
            get
            {
                return _execResults;
            }
            set
            {
                _execResults = value;
            }
        }

        public Dictionary<String, String> GetResultsDictionary()
        {
            if(_resultsDict == null)
                _resultsDict = new Dictionary<String, String>();

            return _resultsDict;
        }

        public UIApplication UIApp
        {
            get
            {
                return _commandData.Application;
            }
        }

        public Application App
        {
            get
            {
                return _commandData.Application.Application;
            }
        }

        public void Dispose()
        {
            _scriptOutput = null;
            _outputStream = null;
            _resultsDict = null;
        }
    }
}
