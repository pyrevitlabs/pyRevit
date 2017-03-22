using System;
using System.Collections.Generic;
using System.Reflection;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using System.Windows.Forms;
using Autodesk.Revit;
using Autodesk.Revit.UI;
using Autodesk.Revit.DB;
using IronPython.Runtime;


namespace PyRevitBaseClasses
{
    public class LogEntry
    {
        public string date;
        public string time;
        public string username;
        public string revit;
        public string revitbuild;
        public int sessionid;
        public string pyrevit;
        public bool debug;
        public bool alternate;
        public string commandname;
        public int resultcode;
        public Dictionary<String, String> commandresults;
        public string scriptpath;

        public LogEntry(string revitUsername, string revitVersion, string revitBuild, int revitProcessId,
                        string pyRevitVersion, bool debugModeEnabled, bool alternateModeEnabled,
                        string pyRevitCommandName, int executorResultCode, ref Dictionary<String, String> resultDict,
                        string pyRevitCommandPath)
        {
            // date = logDate;
            // time = logTime;
            username = revitUsername;
            revit = revitVersion;
            revitbuild = revitBuild;
            sessionid = revitProcessId;
            pyrevit = pyRevitVersion;
            debug = debugModeEnabled;
            alternate = alternateModeEnabled;
            commandname = pyRevitCommandName;
            resultcode = executorResultCode;
            commandresults = resultDict;
            scriptpath = pyRevitCommandPath;
        }
    }

    public class ScriptUsageLogger
    {
        private readonly UIApplication _revit;
        public LogEntry _entry;
        public string _usageLogFilePath;
        public string _usageLogServerUrl;

        public ScriptUsageLogger(ExternalCommandData commandData,
                                 string cmdName, string scriptSource,
                                 bool forcedDebugMode, bool altScriptMode, int execResult,
                                 ref Dictionary<String, String> resultDict)
        {
            _revit = commandData.Application;

            // get live data from python dictionary saved in appdomain
            var envdict = new EnvDictionary();
            _usageLogFilePath = envdict.GetUsageLogFilePath();
            _usageLogServerUrl = envdict.GetUsageLogServerUrl();

            _entry = new LogEntry(_revit.Application.Username,
                                  _revit.Application.VersionNumber, _revit.Application.VersionBuild,
                                  Process.GetCurrentProcess().Id, envdict.GetPyRevitVersion(),
                                  forcedDebugMode, altScriptMode, cmdName, execResult, ref resultDict,
                                  scriptSource.Replace("\\", "\\\\"));
        }

        public string MakeJSONLogEntry()
        {
            _entry.date = DateTime.Now.ToString("yyyy/MM/dd");
            _entry.time = DateTime.Now.ToString("HH:mm:ss:ffff");

             return new JavaScriptSerializer().Serialize(_entry);
        }

        public void PostUsageLogToServer(string usageLogServerUrl)
        {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(usageLogServerUrl);
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

        public void WriteUsageLogToFile(string usageLogFilePath)
        {
            string json = MakeJSONLogEntry();
        }

        public void LogUsage()
        {
            if(!String.IsNullOrEmpty(_usageLogServerUrl))
                PostUsageLogToServer(_usageLogServerUrl);
            if(!String.IsNullOrEmpty(_usageLogServerUrl))
                WriteUsageLogToFile(_usageLogFilePath);
        }
    }
}
