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


    public class ScriptUsageLogger
    {
        private string _usageLogFilePath;
        private string _usageLogServerUrl;
        public LogEntry logEntry;

        public ScriptUsageLogger() {}

        public string MakeJSONLogEntry()
        {
            logEntry.TimeStamp();
            return new JavaScriptSerializer().Serialize(logEntry);
        }

        public void PostUsageLogToServer()
        {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(_usageLogServerUrl);
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

        public void LogUsage(ref PyRevitCommandRuntime pyrvtCmd)
        {
            // get usage log state data from python dictionary saved in appdomain
            // this needs to happen before command exection to get the values before the command changes them
            var envdict = new EnvDictionary();

            // get live data from python dictionary saved in appdomain
            _usageLogFilePath = envdict.usageLogFilePath;
            _usageLogServerUrl = envdict.usageLogServerUrl;

            logEntry = new LogEntry(pyrvtCmd.App.Username,
                                    pyrvtCmd.App.VersionNumber, pyrvtCmd.App.VersionBuild,
                                    envdict.sessionUUID, envdict.addonVersion,
                                    pyrvtCmd.DebugMode,
                                    pyrvtCmd.AlternateMode,
                                    pyrvtCmd.CommandName,
                                    pyrvtCmd.CommandBundle,
                                    pyrvtCmd.CommandExtension,
                                    pyrvtCmd.CommandUniqueId,
                                    pyrvtCmd.ScriptSourceFile,
                                    pyrvtCmd.ExecutionResult,
                                    pyrvtCmd.GetResultsDictionary());

            // log usage if usage logging in enabled
            if (envdict.usageLogState && !String.IsNullOrEmpty(_usageLogServerUrl))
                new Task(PostUsageLogToServer).Start();

            if (envdict.usageLogState && !String.IsNullOrEmpty(_usageLogFilePath))
                new Task(WriteUsageLogToFile).Start();
        }
    }
}
