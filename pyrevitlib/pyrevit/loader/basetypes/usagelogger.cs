using System;
using System.Collections.Generic;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;
using System.Threading.Tasks;


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
                        string pyRevitVersion,
                        bool debugModeEnabled, bool alternateModeEnabled,
                        string pyRevitCommandName, string pyRevitCommandBundle, string pyRevitCommandExtension, string pyRevitCommandUniqueName, string pyRevitCommandPath,
                        int executorResultCode, Dictionary<String, String> resultDict)
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
            scriptpath = pyRevitCommandPath;
            resultcode = executorResultCode;
            commandresults = resultDict;
        }

        public void TimeStamp()
        {
            date = DateTime.Now.ToString("yyyy/MM/dd");
            time = DateTime.Now.ToString("HH:mm:ss:ffff");
        }
    }


    public static class ScriptUsageLogger
    {
        public static string MakeJSONLogEntry(LogEntry logEntry)
        {
            logEntry.TimeStamp();
            return new JavaScriptSerializer().Serialize(logEntry);
        }

        public static void PostUsageLogToServer(string _usageLogServerUrl, LogEntry logEntry)
        {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(_usageLogServerUrl);
            httpWebRequest.ContentType = "application/json";
            httpWebRequest.Method = "POST";

            using (var streamWriter = new StreamWriter(httpWebRequest.GetRequestStream()))
            {
                string json = MakeJSONLogEntry(logEntry);

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

        public static void WriteUsageLogToFile(string _usageLogFilePath, LogEntry logEntry)
        {
            // Read existing json data
            string jsonData = "[]";
            if(File.Exists(_usageLogFilePath)) {
                jsonData = System.IO.File.ReadAllText(_usageLogFilePath);
            }
            else {
                System.IO.File.WriteAllText(_usageLogFilePath, jsonData);
            }

            // De-serialize to object or create new list
            var logData = new JavaScriptSerializer().Deserialize<List<LogEntry>>(jsonData);

            // Add any new employees
            logEntry.TimeStamp();
            logData.Add(logEntry);

            // Update json data string
            jsonData = new JavaScriptSerializer().Serialize(logData);
            System.IO.File.WriteAllText(_usageLogFilePath, jsonData);
        }

        public static void LogUsage(LogEntry logEntry)
        {
            var envDict = new EnvDictionary();

            if (envDict.usageLogState && envDict.usageLogServerUrl != null && !String.IsNullOrEmpty(envDict.usageLogServerUrl))
                new Task(() => PostUsageLogToServer(envDict.usageLogServerUrl, logEntry)).Start();

            if (envDict.usageLogState && envDict.usageLogFilePath != null && !String.IsNullOrEmpty(envDict.usageLogFilePath))
                new Task(() => WriteUsageLogToFile(envDict.usageLogFilePath, logEntry)).Start();
        }
    }
}
