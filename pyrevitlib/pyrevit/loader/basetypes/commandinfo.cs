using System;
using Microsoft.Scripting.Hosting;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using System.Collections.Generic;


namespace PyRevitBaseClasses
{
    public class PyRevitCommandInfo
    {
        private string _scriptSource;
        private string _alternateScriptSource;
        private string _syspaths;
        private string _cmdName;
        private string _cmdBundle;
        private string _cmdExtension;
        private string _cmdUniqueName;
        private bool _forcedDebugMode = false;
        private bool _altScriptMode = false;

        public PyRevitCommandInfo(string scriptSource,
                                  string alternateScriptSource,
                                  string syspaths,
                                  string cmdName,
                                  string cmdBundle,
                                  string cmdExtension,
                                  string cmdUniqueName,
                                  bool forcedDebugMode, bool altScriptMode)
        {
            _scriptSource = scriptSource;
            _alternateScriptSource = alternateScriptSource;
            _syspaths = syspaths;
            _cmdName = cmdName;
            _cmdBundle = cmdBundle;
            _cmdExtension = cmdExtension;
            _cmdUniqueName = cmdUniqueName;
            _forcedDebugMode = forcedDebugMode;
            _altScriptMode = altScriptMode;

            // create result Dictionary
            var resultDict = new Dictionary<String, String>();

        }
    }

}
