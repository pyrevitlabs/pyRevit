using System;
using System.Reflection;
using System.Linq;
using System.Net;
using System.IO;
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

        public string MakeFileLogEntry()
        {
            return String.Format("{0}, {1}, {2}:{3}, {4}, {5}, {6}, {7}, {8}, {9}",
                   DateTime.Now.ToString("yyyy/MM/dd@HH:mm:ss:ffff"),
                   _username, _revitVerNum, _revitBuild, _pyRevitVersion,
                   _forcedDebugMode, _altScriptMode, _cmdName, _execResult, _scriptSource);
        }

        public string MakeJSONLogEntry()
        {
            return '{' +
                   String.Format("\"date\":\"{0}\"", DateTime.Now.ToString("yyyy/MM/dd")) +
                   String.Format(", \"time\":\"{0}\"", DateTime.Now.ToString("HH:mm:ss:ffff")) +
                   String.Format(", \"username\":\"{0}\"", _username) +
                   String.Format(", \"revit\":\"{0}\"", _revitVerNum) +
                   String.Format(", \"revitbuild\":\"{0}\"", _revitBuild) +
                   String.Format(", \"pyrevit\":\"{0}\"", _pyRevitVersion) +
                   String.Format(", \"debug\":\"{0}\"", _forcedDebugMode) +
                   String.Format(", \"alternate\":\"{0}\"", _altScriptMode) +
                   String.Format(", \"commandname\":\"{0}\"", _cmdName) +
                   String.Format(", \"result\":\"{0}\"", _execResult) +
                   String.Format(", \"source\":\"{0}\"", _scriptSource.Replace("\\", "\\\\")) +
                   '}';
        }

        public void PostUsageLogToServer(string serverUrl)
        {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(serverUrl);
            httpWebRequest.ContentType = "application/json";
            httpWebRequest.Method = "POST";

            using (var streamWriter = new StreamWriter(httpWebRequest.GetRequestStream()))
            {
                string json = MakeJSONLogEntry();

                streamWriter.Write(json);
                streamWriter.Flush();
                streamWriter.Close();
            }

            var httpResponse = (HttpWebResponse)httpWebRequest.GetResponse();
            using (var streamReader = new StreamReader(httpResponse.GetResponseStream()))
            {
                var result = streamReader.ReadToEnd();
            }
        }

        public void WriteUsageLogToFile(string logFilePath)
        {
        }

        public void LogUsage()
        {
            // PostUsageLogToServer(" ");
        }
    }
}
