using System;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;
using System.Windows.Input;


namespace PyRevitBaseClasses
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public abstract class PyRevitCommand : IExternalCommand
    {
        private string _scriptSource = null;
        private string _alternateScriptSource = null;
        private string _syspaths = null;
        private string _cmdName = null;
        private string _cmdBundle = null;
        private string _cmdExtension = null;
        private string _cmdUniqueName = null;
        private bool _needsCleanEngine = false;
        private bool _needsFullFrameEngine = false;


        public PyRevitCommand(string scriptSource,
                              string alternateScriptSource,
                              string syspaths,
                              string cmdName,
                              string cmdBundle,
                              string cmdExtension,
                              string cmdUniqueName,
                              int needsCleanEngine,
                              int needsFullFrameEngine)
        {
            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
            _syspaths = syspaths;
            _cmdName = cmdName;
            _cmdBundle = cmdBundle;
            _cmdExtension = cmdExtension;
            _cmdUniqueName = cmdUniqueName;
            _needsCleanEngine = Convert.ToBoolean(needsCleanEngine);
            _needsFullFrameEngine = Convert.ToBoolean(needsFullFrameEngine);
        }


        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            // 1: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Processing modifier keys
            // Processing modifier keys
            // Default script is the main script unless it is changed by modifier buttons
            var _script = _scriptSource;

            bool _refreshEngine = false;
            bool _altScriptMode = false;
            bool _forcedDebugMode = false;

            // If Ctrl-Alt-Shift clicking on the tool run in clean engine
            if ((Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt)) &&
                (Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl)) &&
                (Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift)))
            {
                _refreshEngine = true;
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
            #endregion

            // 2: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Setup pyRevit Command Runtime
            var pyrvtCmdRuntime = new PyRevitCommandRuntime(commandData, elements,
                                                            _scriptSource,
                                                            _alternateScriptSource,
                                                            _syspaths,
                                                            _cmdName,
                                                            _cmdBundle,
                                                            _cmdExtension,
                                                            _cmdUniqueName,
                                                            _needsCleanEngine,
                                                            _needsFullFrameEngine,
                                                            _refreshEngine,
                                                            _forcedDebugMode,
                                                            _altScriptMode);
            #endregion

            // 3: ---------------------------------------------------------------------------------------------------------------------------------------------
            #region Execute and log results
            // Executing the script and logging the results

            // Get script executor and Execute the script
            var executor = new ScriptExecutor();
            pyrvtCmdRuntime.ExecutionResult = executor.ExecuteScript(ref pyrvtCmdRuntime);

            // Log results
            ScriptUsageLogger.LogUsage(pyrvtCmdRuntime.MakeLogEntry());

            // GC cleanups
            var re = pyrvtCmdRuntime.ExecutionResult;
            pyrvtCmdRuntime.Dispose();
            pyrvtCmdRuntime = null;

            // Return results to Revit. Don't report errors since we don't want Revit popup with error results
            if ( re == 0)
                return Result.Succeeded;
            else
                return Result.Cancelled;
            #endregion
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
