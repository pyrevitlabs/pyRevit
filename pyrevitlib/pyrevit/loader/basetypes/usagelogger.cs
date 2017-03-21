using System;
using System.Reflection;
using System.Linq;
using System.Windows.Forms;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;


namespace PyRevitBaseClasses
{
    public class ScriptUsageLogger
    {
        private readonly UIApplication _revit;
        public string _cmdName = "";
        public string _scriptSource = "";
        public string _revitVerNum = "";
        public string _revitBuild = "";
        public string _username = "";
        public string _pyRevitVersion = "";
        public bool _altScriptMode = false;
        public bool _forcedDebugMode = false;
        public int _execResult = 0;

        public ScriptUsageLogger(ExternalCommandData commandData,
                                 string cmdName, string scriptSource,
                                 bool forcedDebugMode, bool altScriptMode, int execResult, string pyRevitVersion)
        {
            _cmdName = cmdName;
            _scriptSource = scriptSource;
            _revit = commandData.Application;
            _revitVerNum = _revit.Application.VersionNumber;
            _revitBuild = _revit.Application.VersionBuild;
            _username = _revit.Application.Username;
            _forcedDebugMode = forcedDebugMode;
            _altScriptMode = altScriptMode;
            _execResult = execResult;
            _pyRevitVersion = pyRevitVersion;
        }

        public void LogUsage()
        {
            string timeStamp = DateTime.Now.ToString("yyyy/MM/dd@HH:mm:ss:ffff");
            string logEntry = String.Format("{0}, {1}, {2}:{3}, {4}, {5}, {6}, {7}, {8}, {9}",
                timeStamp, _username, _revitVerNum, _revitBuild, _pyRevitVersion,
                _forcedDebugMode, _altScriptMode, _cmdName, _execResult, _scriptSource);

            // MessageBox.Show(logEntry, "Log Entry");
        }
    }
}
