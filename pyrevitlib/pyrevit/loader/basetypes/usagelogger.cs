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
        public string date { get; set; }
        public string time { get; set; }
        public string username { get; set; }
        public string revit { get; set; }
        public string revitbuild { get; set; }
        public int sessionid { get; set; }
        public string pyrevit { get; set; }
        public bool debug { get; set; }
        public bool alternate { get; set; }
        public string commandname { get; set; }
        public int resultcode { get; set; }
        public Dictionary<String, String> commandresults { get; set; }
        public string scriptpath { get; set; }

        public LogEntry() {

        }

        public LogEntry(string revitUsername, string revitVersion, string revitBuild, int revitProcessId,
                        string pyRevitVersion, bool debugModeEnabled, bool alternateModeEnabled,
                        string pyRevitCommandName, int executorResultCode, ref Dictionary<String, String> resultDict,
                        string pyRevitCommandPath)
        {
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

        public void TimeStamp()
        {
            date = DateTime.Now.ToString("yyyy/MM/dd");
            time = DateTime.Now.ToString("HH:mm:ss:ffff");
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
                                  scriptSource);
        }

        public string MakeJSONLogEntry()
        {
            _entry.TimeStamp();
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
            // Read existing json data
            string jsonData = "[]";
            if(File.Exists(usageLogFilePath)) {
                jsonData = System.IO.File.ReadAllText(usageLogFilePath);
            }
            else {
                System.IO.File.WriteAllText(usageLogFilePath, jsonData);
            }

            // De-serialize to object or create new list
            var logData = new JavaScriptSerializer().Deserialize<List<LogEntry>>(jsonData);

            // Add any new employees
            _entry.TimeStamp();
            logData.Add(_entry);

            // Update json data string
            jsonData = new JavaScriptSerializer().Serialize(logData);
            System.IO.File.WriteAllText(usageLogFilePath, jsonData);
        }

        public void LogUsage()
        {
            if(!String.IsNullOrEmpty(_usageLogServerUrl))
                PostUsageLogToServer(_usageLogServerUrl);
            if(!String.IsNullOrEmpty(_usageLogFilePath))
                WriteUsageLogToFile(_usageLogFilePath);
        }
    }
}
