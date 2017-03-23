using System;
using System.IO;
using Autodesk.Revit;
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
        public string _scriptSource = "";
        public string _alternateScriptSource = "";
        public string _syspaths = "";
        public string _cmdName = "";
        public bool _forcedDebugMode = false;
        public bool _altScriptMode = false;

        public PyRevitCommand(string scriptSource,
                              string alternateScriptSource,
                              string syspaths,
                              string cmdName)
        {
            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
            _syspaths = syspaths;
            _cmdName = cmdName;
        }

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            // Default script is the main script unless it is changed by modifier buttons
            var _script = _scriptSource;

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

            // If Alt clicking on button, open the script in explorer and return.
            if (Keyboard.IsKeyDown(Key.LeftAlt) || Keyboard.IsKeyDown(Key.RightAlt))
            {
               // combine the arguments together
               // it doesn't matter if there is a space after ','
               string argument = "/select, \"" + _script +"\"";

               System.Diagnostics.Process.Start("explorer.exe", argument);
               return Result.Succeeded;
            }

            // Get script executor
            var executor = new ScriptExecutor(this, commandData, message, elements);

            // create result Dictionary
            var resultDict = new Dictionary<String, String>();
            // Execute script
            var resultCode = executor.ExecuteScript(_script, _syspaths, _cmdName,
                                                _forcedDebugMode, _altScriptMode,
                                                ref resultDict);

            // log usage if usage logging in enabled
            // get usage log state data from python dictionary saved in appdomain
            var envdict = new EnvDictionary();
            if(envdict.GetUsageLogState()) {
                var logger = new ScriptUsageLogger(commandData, _cmdName, _script,
                                                   _forcedDebugMode, _altScriptMode, resultCode,
                                                   ref resultDict);
                new Task(logger.LogUsage).Start();
            }

            // Return results
            if (resultCode == 0)
                return Result.Succeeded;
            else
                return Result.Cancelled;
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
