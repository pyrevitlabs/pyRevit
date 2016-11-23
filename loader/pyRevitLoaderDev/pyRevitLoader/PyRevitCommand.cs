using System;
using System.IO;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using Autodesk.Revit.Attributes;
using System.Collections.Generic;
using System.Windows.Input;

namespace PyRevitLoader
{
    /// <summary>
    /// Starts up a ScriptOutput window for a given canned command.
    /// This class version will log the liked _scriptSource execution in a log file in user temp drive. 
    /// 
    /// It is expected that this will be inherited by dynamic types that have the field
    /// _scriptSource set to point to a python file that will be executed in the constructor.
    /// </summary>
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

        /// <summary>
        /// Overload this method to implement an external command within Revit.
        /// </summary>
        /// <returns>
        /// The result indicates if the execution fails, succeeds, or was canceled by user. If it does not
        /// succeed, Revit will undo any changes made by the external command. 
        /// </returns>
        /// <param name="commandData">An ExternalCommandData object which contains reference to Application and View
        /// needed by external command.</param><param name="message">Error message can be returned by external command. This will be displayed only if the command status
        /// was "Failed".  There is a limit of 1023 characters for this message; strings longer than this will be truncated.</param><param name="elements">Element set indicating problem elements to display in the failure dialog.  This will be used
        /// only if the command status was "Failed".</param>
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
}
