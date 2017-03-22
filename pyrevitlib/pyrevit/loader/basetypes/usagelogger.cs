using System;
using System.Collections.Generic;
using System.Reflection;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.IO;
using System.Windows.Forms;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using IronPython.Runtime;


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
        public string _usageLogFilePath = "";
        public string _serverUrl = "";
        public bool _altScriptMode = false;
        public bool _forcedDebugMode = false;
        public int _execResult = 0;
        public int _processid = 0;
        public Dictionary<String, String> _resultDict;

        public ScriptUsageLogger(ExternalCommandData commandData,
                                 string cmdName, string scriptSource,
                                 bool forcedDebugMode, bool altScriptMode, int execResult,
                                 ref Dictionary<String, String> resultDict)
        {
            _cmdName = cmdName;
            _scriptSource = scriptSource;
            _revit = commandData.Application;
            _revitVerNum = _revit.Application.VersionNumber;
            _revitBuild = _revit.Application.VersionBuild;
            _processid = Process.GetCurrentProcess().Id;
            _username = _revit.Application.Username;
            _forcedDebugMode = forcedDebugMode;
            _altScriptMode = altScriptMode;
            _execResult = execResult;
            _resultDict = resultDict;

            // get live data from python dictionary saved in appdomain
            var envdict = new EnvDictionary();
            _pyRevitVersion = envdict.GetPyRevitVersion();
            _usageLogFilePath = envdict.GetUsageLogFilePath();
            _serverUrl = envdict.GetUsageLogFilePath();
        }

        public string MakeJSONLogEntry()
        {
            // Create json package and add the standard log data
            var json_log_pkg =  '{' +
                   String.Format("\"date\":\"{0}\"", DateTime.Now.ToString("yyyy/MM/dd")) +
                   String.Format(", \"time\":\"{0}\"", DateTime.Now.ToString("HH:mm:ss:ffff")) +
                   String.Format(", \"username\":\"{0}\"", _username) +
                   String.Format(", \"revit\":\"{0}\"", _revitVerNum) +
                   String.Format(", \"revitbuild\":\"{0}\"", _revitBuild) +
                   String.Format(", \"sessionid\":\"{0}\"", _processid) +
                   String.Format(", \"pyrevit\":\"{0}\"", _pyRevitVersion) +
                   String.Format(", \"debug\":\"{0}\"", _forcedDebugMode) +
                   String.Format(", \"alternate\":\"{0}\"", _altScriptMode) +
                   String.Format(", \"commandname\":\"{0}\"", _cmdName) +
                   String.Format(", \"result\":\"{0}\"", _execResult) +
                   String.Format(", \"source\":\"{0}\"", _scriptSource.Replace("\\", "\\\\"));

           foreach(KeyValuePair<string, string> entry in _resultDict)
           {
               // Add custom script data to log package
               json_log_pkg += String.Format(", \"{0}\":\"{1}\"", entry.Key, entry.Value);
           }

           // Close the json package
           json_log_pkg += '}';

           return json_log_pkg;
        }

        public void PostUsageLogToServer()
        {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(_serverUrl);
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

        public void WriteUsageLogToFile()
        {
        }

        public void LogUsage()
        {

        }
    }
}
