using System;
using System.IO;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;
using System.Collections.Generic;
using System.Windows.Input;

namespace PyRevitBaseClasses
{
    [Regeneration(RegenerationOption.Manual)]
    [Transaction(TransactionMode.Manual)]
    public abstract class PyRevitCommand : IExternalCommand
    {
        public string _scriptSource = "";
        public string _alternateScriptSource = "";
        public string _logfilename = "";
        public string _syspaths;
        public string _cmdName;
        public string _cmdOptions;
        public bool _forcedDebugMode = false;
        public bool _altScriptMode = false;

        public PyRevitCommand(string scriptSource, string alternateScriptSource, string logfilename, string syspaths, string cmdName, string cmdOptions)
        {
            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
            _logfilename = logfilename;
            _syspaths = syspaths;
            _cmdName = cmdName;
            _cmdOptions = cmdOptions;
        }

        public Result Execute(ExternalCommandData commandData, ref string message, ElementSet elements)
        {
            // FIXME: somehow fetch back message after script execution...
            var executor = new ScriptExecutor( commandData, message, elements);

            // If Ctrl clicking on button, set forced debug mode
            if (Keyboard.IsKeyDown(Key.LeftCtrl) || Keyboard.IsKeyDown(Key.RightCtrl))
            {
                _forcedDebugMode = true;
            }

            // If Shift clicking on button, run config script instead
            if (Keyboard.IsKeyDown(Key.LeftShift) || Keyboard.IsKeyDown(Key.RightShift))
            {
                _scriptSource = _alternateScriptSource;
                _altScriptMode = true;
            }

            // Execute script
            var result = executor.ExecuteScript(_scriptSource, _syspaths, _cmdName, _cmdOptions, _forcedDebugMode, _altScriptMode);
            message = executor.Message;

            // Log successful script usage
            if (result == (int)Result.Succeeded && _logfilename.Length > 0)
            {
                //Logger: Log filename will be set by the loader when creating classes for each script. That's the _logfilename.
                //This step will record a log entry for each script execution.
                string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");        //log time stamp
                string username = commandData.Application.Application.Username;         //log username
                string rvtversion = commandData.Application.Application.VersionNumber;  //log Revit version
                string temppath = Path.Combine(Path.GetTempPath(), _logfilename);
                using (var logger = File.AppendText(temppath))
                {
                    //This is the log entry in CSV format: {timestamp}, {username}, {revit version}, {full script address}
                    logger.WriteLine(String.Format("{0}, {1}, {2}, {3}", timestamp, username, rvtversion, _scriptSource));
                }
            }

            switch (result)
            {
                case (int)Result.Succeeded:
                    return Result.Succeeded;
                case (int)Result.Cancelled:
                    return Result.Cancelled;
                case (int)Result.Failed:
                    return Result.Failed;
                default:
                    return Result.Succeeded;
            }
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
