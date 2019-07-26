using System;
using System.Collections.Generic;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using System.Threading.Tasks;

using pyRevitLabs.Common;

namespace PyRevitBaseClasses
{
    public class EngineInfo {
        public string type { get; set; }
        public string version { get; set; }
        public List<string> syspath { get; set; }
    }

    public class TraceInfo {
        public EngineInfo engine { get; set; }
        public string message { get; set; }
    }

    public class LogEntry {
        // schema
        public Dictionary<string, string> meta { get; private set; }

            // when?
        public string timestamp { get; set; }
        // by who?
        public string username { get; set; }
        // on what?
        public string revit { get; set; }
        public string revitbuild { get; set; }
        public string sessionid { get; set; }
        public string pyrevit { get; set; }
        public string clone { get; set; }
        // which mode?
        public bool debug { get; set; }
        public bool config { get; set; }
        public bool from_gui { get; set; }
        public bool clean_engine { get; set; }
        public bool fullframe_engine { get; set; }
        // which script?
        public string commandname { get; set; }
        public string commandbundle { get; set; }
        public string commandextension { get; set; }
        public string commanduniquename { get; set; }
        public string scriptpath { get; set; }
        public string arguments { get; set; }
        // returned what?
        public int resultcode { get; set; }
        public Dictionary<string, string> commandresults { get; set; }
        // any errors?
        public TraceInfo trace { get; set; }

        public LogEntry(string revitUsername,
                        string revitVersion,
                        string revitBuild,
                        string revitProcessId,
                        string pyRevitVersion,
                        string cloneName,
                        bool debugModeEnabled,
                        bool configModeEnabled,
                        bool execFromGUI,
                        bool cleanEngine,
                        bool fullframeEngine,
                        string pyRevitCommandName,
                        string pyRevitCommandBundle,
                        string pyRevitCommandExtension,
                        string pyRevitCommandUniqueName,
                        string pyRevitCommandPath,
                        int executorResultCode,
                        Dictionary<string, string> resultDict,
                        TraceInfo traceInfo)
        {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            timestamp = CommonUtils.GetISOTimeStampNow();

            username = revitUsername;
            revit = revitVersion;
            revitbuild = revitBuild;
            sessionid = revitProcessId;
            pyrevit = pyRevitVersion;
            clone = cloneName;
            debug = debugModeEnabled;
            config = configModeEnabled;
            from_gui = execFromGUI;
            clean_engine = cleanEngine;
            fullframe_engine = fullframeEngine;
            commandname = pyRevitCommandName;
            commandbundle = pyRevitCommandBundle;
            commandextension = pyRevitCommandExtension;
            commanduniquename = pyRevitCommandUniqueName;
            scriptpath = pyRevitCommandPath;
            resultcode = executorResultCode;
            commandresults = resultDict;
            trace = traceInfo;
        }
    }


    public static class ScriptUsageLogger
    {
        public static string MakeJSONLogEntry(LogEntry logEntry)
        {
            return new JavaScriptSerializer().Serialize(logEntry);
        }

        public static void PostUsageLogToServer(string _usageLogServerUrl, LogEntry logEntry)
        {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(_usageLogServerUrl);
            httpWebRequest.ContentType = "application/json";
            httpWebRequest.Method = "POST";
            httpWebRequest.UserAgent = "pyrevit";

            using (var streamWriter = new StreamWriter(httpWebRequest.GetRequestStream())) {
                string json = MakeJSONLogEntry(logEntry);

                streamWriter.Write(json);
                streamWriter.Flush();
                streamWriter.Close();
            }

            var httpResponse = (HttpWebResponse)httpWebRequest.GetResponse();
            using (var streamReader = new StreamReader(httpResponse.GetResponseStream())) {
                var result = streamReader.ReadToEnd();
            }
        }

        public static void WriteUsageLogToFile(string _usageLogFilePath, LogEntry logEntry)
        {
            // Read existing json data
            string jsonData = "[]";
            if (File.Exists(_usageLogFilePath))
            {
                jsonData = File.ReadAllText(_usageLogFilePath);
            }
            else
            {
                File.WriteAllText(_usageLogFilePath, jsonData);
            }

            // De-serialize to object or create new list
            var logData = new JavaScriptSerializer().Deserialize<List<LogEntry>>(jsonData);

            // Add any new employees
            logData.Add(logEntry);

            // Update json data string
            jsonData = new JavaScriptSerializer().Serialize(logData);
            File.WriteAllText(_usageLogFilePath, jsonData);
        }

        public static void LogUsage(LogEntry logEntry)
        {
            var envDict = new EnvDictionary();

            if (envDict.usageLogState)
            {
                if (envDict.usageLogState && envDict.usageLogServerUrl != null && !string.IsNullOrEmpty(envDict.usageLogServerUrl))
                    new Task(() => PostUsageLogToServer(envDict.usageLogServerUrl, logEntry)).Start();

                if (envDict.usageLogState && envDict.usageLogFilePath != null && !string.IsNullOrEmpty(envDict.usageLogFilePath))
                    new Task(() => WriteUsageLogToFile(envDict.usageLogFilePath, logEntry)).Start();
            }
        }
    }
}
