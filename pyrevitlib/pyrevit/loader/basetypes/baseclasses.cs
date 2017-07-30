using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;
using System.Collections.Generic;
using System.Windows.Input;
using System.Threading.Tasks;


namespace PyRevitBaseClasses
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public abstract class PyRevitCommand : IExternalCommand
    {
        private string _scriptSource;
        private string _alternateScriptSource;
        private string _syspaths;
        private string _cmdName;
        private string _cmdBundle;
        private string _cmdExtension;
        private string _cmdUniqueName;
        private bool _needsCleanEngine = false;
        private bool _forcedDebugMode = false;
        private bool _altScriptMode = false;

        private ScriptOutput _scriptOutput;
        private ScriptOutputStream _outputStream;

        private ExternalCommandData _commandData;
        private ElementSet _elements;
        private Dictionary<String, String> _resultsDict;

        public PyRevitCommand(string scriptSource,
                              string alternateScriptSource,
                              string syspaths,
                              string cmdName,
                              string cmdBundle,
                              string cmdExtension,
                              string cmdUniqueName,
                              int needsCleanEngine)
        {
            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
            _syspaths = syspaths;
            _cmdName = cmdName;
            _cmdBundle = cmdBundle;
            _cmdExtension = cmdExtension;
            _cmdUniqueName = cmdUniqueName;
            _needsCleanEngine = Convert.ToBoolean(needsCleanEngine);
        }

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            // 1: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Processing modifier keys
            // Default script is the main script unless it is changed by modifier buttons
            var _script = _scriptSource;

            // If Ctrl-Alt-Shift clicking on the tool run in clean engine
            if (Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt) &&
                Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl) &&
                Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift))
            {
                _needsCleanEngine = true;
            }
            else
            {
                // If Alt clicking on button, open the script in explorer and return.
                if (Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt))
                {
                    // combine the arguments together
                    // it doesn't matter if there is a space after ','
                    string argument = "/select, \"" + _script + "\"";

                    System.Diagnostics.Process.Start("explorer.exe", argument);
                    return Result.Succeeded;
                }
                else
                {
                    // If Shift clicking on button, run config script instead
                    if (Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift))
                    {
                        _script = _alternateScriptSource;
                        _altScriptMode = true;
                    }

                    // If Ctrl clicking on button, set forced debug mode.
                    if (Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl))
                    {
                        _forcedDebugMode = true;
                    }
                }
            }

            // 2: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Stating a new output window
            _scriptOutput = new ScriptOutput();
            _outputStream = new ScriptOutputStream(_scriptOutput);
            var hndl = _scriptOutput.Handle;                // Forces creation of handle before showing the window
            _scriptOutput.Text = _cmdName;                  // Set output window title to command name
            _scriptOutput.OutputId = _cmdUniqueName;        // Set window identity to the command unique identifier

            // 3: ---------------------------------------------------------------------------------------------------------------------------------------------
            // Executing the script and logging the results
            // get usage log state data from python dictionary saved in appdomain
            // this needs to happen before command exection to get the values before the command changes them
            var envdict = new EnvDictionary();

            // create result Dictionary 
            _resultsDict = new Dictionary<String, String>();

            // Get script executor
            var executor = new ScriptExecutor(commandData);
            // Execute script
            var resultCode = executor.ExecuteScript(this);

            // log usage if usage logging in enabled
            if(envdict.usageLogState) {
                var logger = new ScriptUsageLogger(ref envdict, commandData, this, resultCode);
                new Task(logger.LogUsage).Start();
            }

            // Return results
            if (resultCode == 0)
                return Result.Succeeded;
            else
                return Result.Cancelled;
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
                return _scriptOutput;
            }
        }

        public ScriptOutputStream OutputStream
        {
            get
            {
                return _outputStream;
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

        public Dictionary<String, String> GetResultsDictionary()
        {
            return _resultsDict;
        }

    }


    public abstract class PyRevitCommandCategoryAvail : IExternalCommandAvailability
    {
        public string _categoryName = "";

        public PyRevitCommandCategoryAvail(string contextString)
        {
            _categoryName = contextString;
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories)
        {
            // Categories allCats = uiApp.ActiveUIDocument.Document.Settings.Categories;
            if (selectedCategories.IsEmpty) return false;
            foreach(Category rvt_cat in selectedCategories){
                if (rvt_cat.Name != this._categoryName) return false;
            }
            return true;
        }
    }


    public abstract class PyRevitCommandSelectionAvail : IExternalCommandAvailability
    {
        public string _categoryName = "";

        public PyRevitCommandSelectionAvail(string contextString)
        {
            _categoryName = contextString;
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories)
        {
            if (selectedCategories.IsEmpty) return false;
            return true;
        }
    }


    public abstract class PyRevitCommandDefaultAvail : IExternalCommandAvailability
    {
        public PyRevitCommandDefaultAvail()
        {
        }

        public bool IsCommandAvailable(UIApplication uiApp, CategorySet selectedCategories)
        {
            return true;
        }
    }

}
