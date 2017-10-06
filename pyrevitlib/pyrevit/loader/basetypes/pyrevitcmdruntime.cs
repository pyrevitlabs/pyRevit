using System;
using System.Collections.Generic;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.ApplicationServices;


namespace PyRevitBaseClasses
{
	public class PyRevitCommandRuntime
	{
        private ExternalCommandData _commandData = null;
        private ElementSet _elements = null;

        private string _scriptSource = null;
        private string _alternateScriptSource = null;
        private string _syspaths = null;
        private string _cmdName = null;
        private string _cmdBundle = null;
        private string _cmdExtension = null;
        private string _cmdUniqueName = null;
        private bool _needsCleanEngine = false;
        private bool _needsFullFrameEngine = false;

        private bool _refreshEngine = false;
        private bool _forcedDebugMode = false;
        private bool _altScriptMode = false;

        private WeakReference<ScriptOutput> _scriptOutput;
        private WeakReference<ScriptOutputStream> _outputStream;

        private int _execResults = 0;
        private Dictionary<String, String> _resultsDict = null;

        public PyRevitCommandRuntime(ExternalCommandData cmdData,
                                     ElementSet elements,
                                     string scriptSource,
                                     string alternateScriptSource,
                                     string syspaths,
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
            _cmdName = cmdName;
            _cmdBundle = cmdBundle;
            _cmdExtension = cmdExtension;
            _cmdUniqueName = cmdUniqueName;
            _needsCleanEngine = Convert.ToBoolean(needsCleanEngine);
            _needsFullFrameEngine = Convert.ToBoolean(needsFullFrameEngine);

            _refreshEngine = refreshEngine;
            _forcedDebugMode = forcedDebugMode;
            _altScriptMode = altScriptMode;

            // Stating a new output window
            var output = new ScriptOutput();
            output.Text = _cmdName;                  // Set output window title to command name
            output.OutputId = _cmdUniqueName;        // Set window identity to the command unique identifier
            _scriptOutput = new WeakReference<ScriptOutput>(output);

            // Setup the output stream
            _outputStream = new WeakReference<ScriptOutputStream>(new ScriptOutputStream(output));

            // create result Dictionary 
            _resultsDict = new Dictionary<String, String>();

        }

        public Application RevitApp
        {
            get
            {
                return _commandData.Application.Application;
            }
        }

        public UIApplication RevitUIApp
        {
            get
            {
                return _commandData.Application;
            }
        }
        public UIDocument RevitUIDoc
        {
            get
            {
                return _commandData.Application.ActiveUIDocument;
            }
        }
        public Document RevitDoc
        {
            get
            {
                if (_commandData.Application.ActiveUIDocument != null)
                    return _commandData.Application.ActiveUIDocument.Document;
                else
                    return null;
            }
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
                if (re)
                    return output;

                return null;
            }
        }

        public ScriptOutputStream OutputStream
        {
            get
            {
                // get ScriptOutputStream from the weak reference
                ScriptOutputStream outputStream;
                var re = _outputStream.TryGetTarget(out outputStream);
                if (re)
                    return outputStream;

                return null;
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
            return _resultsDict;
        }
    }
}
