using System;
using System.Collections.Generic;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using Autodesk.Revit.UI;


namespace PyRevitBaseClasses
{
    public class LogEntry
    {
        public string date { get; set; }
        public string time { get; set; }
        public string username { get; set; }
        public string revit { get; set; }
        public string revitbuild { get; set; }
        public string sessionid { get; set; }
        public string pyrevit { get; set; }
        public bool debug { get; set; }
        public bool alternate { get; set; }
        public string commandname { get; set; }
        public string commandbundle { get; set; }
        public string commandextension { get; set; }
        public string commanduniquename { get; set; }
        public int resultcode { get; set; }
        public Dictionary<String, String> commandresults { get; set; }
        public string scriptpath { get; set; }

        public LogEntry() {

        }

        public LogEntry(string revitUsername, string revitVersion, string revitBuild, string revitProcessId,
                        string pyRevitVersion, bool debugModeEnabled, bool alternateModeEnabled,
                        string pyRevitCommandName, string pyRevitCommandBundle, string pyRevitCommandExtension, string pyRevitCommandUniqueName,
                        int executorResultCode, ref Dictionary<String, String> resultDict,
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
            commandbundle = pyRevitCommandBundle;
            commandextension = pyRevitCommandExtension;
            commanduniquename = pyRevitCommandUniqueName;
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
        private string _usageLogFilePath;
        private string _usageLogServerUrl;
        public LogEntry logEntry;

        public ScriptUsageLogger(ref EnvDictionary envdict, ExternalCommandData commandData,
                                 string cmdName, string cmdBundle, string cmdExtension, string cmdUniqueName,
                                 string scriptSource,
                                 bool forcedDebugMode, bool altScriptMode,
                                 int execResult, ref Dictionary<String, String> resultDict)
        {
            // get host
            var revit = commandData.Application;
            
            // get live data from python dictionary saved in appdomain
            _usageLogFilePath = envdict.usageLogFilePath;
            _usageLogServerUrl = envdict.usageLogServerUrl;

            logEntry = new LogEntry(revit.Application.Username,
                                    revit.Application.VersionNumber, revit.Application.VersionBuild,
                                    envdict.sessionUUID, envdict.addonVersion,
                                    forcedDebugMode, altScriptMode,
                                    cmdName, cmdBundle, cmdExtension, cmdUniqueName,
                                    execResult, ref resultDict,
                                    scriptSource);
        }

        public string MakeJSONLogEntry()
        {
            logEntry.TimeStamp();
            return new JavaScriptSerializer().Serialize(logEntry);
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
            logEntry.TimeStamp();
            logData.Add(logEntry);

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
