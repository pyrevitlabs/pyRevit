using System;
using System.Collections.Generic;
using System.Web.Script.Serialization;
using System.Threading.Tasks;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public class ScriptTelemetryRecordEngineInfo {
        public string type { get; set; }
        public string version { get; set; }
        public List<string> syspath { get; set; }
        public Dictionary<string, string> configs { get; set; }
    }

    public class ScriptTelemetryRecordTraceInfo {
        public ScriptTelemetryRecordEngineInfo engine { get; set; }
        public string message { get; set; }
    }

    public class ScriptTelemetryRecord {
        // schema
        public Dictionary<string, string> meta { get; private set; }

        // when?
        public string timestamp { get; private set; }
        // by who?
        public string host_user { get; set; }
        public string username { get; set; }
        // on what?
        public string revit { get; set; }
        public string revitbuild { get; set; }
        public string sessionid { get; set; }
        public string pyrevit { get; set; }
        public string clone { get; set; }
        // on which document
        public string docname { get; set; }
        public string docpath { get; set; }
        // which mode?
        public bool debug { get; set; }
        public bool config { get; set; }
        public bool from_gui { get; set; }
        public string exec_id { get; set; }
        public string exec_timestamp { get; set; }
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
        public ScriptTelemetryRecordTraceInfo trace { get; set; }

        public ScriptTelemetryRecord() {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            var env = new EnvDictionary();
            if (env.TelemetryUTCTimeStamps)
                timestamp = CommonUtils.GetISOTimeStampNow();
            else
                timestamp = CommonUtils.GetISOTimeStampLocalNow();
        }
    }

    public static class ScriptTelemetry {
        private static ScriptTelemetryRecord MakeTelemetryRecord(ref ScriptRuntime runtime) {
            // setup a new telemetry record
            return new ScriptTelemetryRecord {
                host_user = UserEnv.GetLoggedInUserName(),
                username = runtime.App.Username,
                revit = runtime.App.VersionNumber,
                revitbuild = runtime.App.VersionBuild,
                sessionid = runtime.SessionUUID,
                pyrevit = runtime.PyRevitVersion,
                clone = runtime.CloneName,
                debug = runtime.ScriptRuntimeConfigs.DebugMode,
                config = runtime.ScriptRuntimeConfigs.ConfigMode,
                from_gui = runtime.ScriptRuntimeConfigs.ExecutedFromUI,
                exec_id = runtime.ExecId,
                exec_timestamp = runtime.ExecTimestamp,
                commandname = runtime.ScriptData.CommandName,
                commandbundle = runtime.ScriptData.CommandBundle,
                commandextension = runtime.ScriptData.CommandExtension,
                commanduniquename = runtime.ScriptData.CommandUniqueId,
                scriptpath = runtime.ScriptSourceFile,
                docname = runtime.DocumentName,
                docpath = runtime.DocumentPath,
                resultcode = runtime.ExecutionResult,
                commandresults = runtime.GetResultsDictionary(),
                trace = new ScriptTelemetryRecordTraceInfo {
                    engine = new ScriptTelemetryRecordEngineInfo {
                        type = runtime.EngineType.ToString().ToLower(),
                        version = runtime.EngineVersion,
                        syspath = runtime.ScriptRuntimeConfigs.SearchPaths,
                        configs = new JavaScriptSerializer().Deserialize<Dictionary<string, string>>(runtime.ScriptRuntimeConfigs.EngineConfigs),
                    },
                    message = runtime.TraceMessage
                }
            };
        }

        public static void LogScriptTelemetryRecord(ref ScriptRuntime runtime) {
            var envDict = new EnvDictionary();

            var record = MakeTelemetryRecord(ref runtime);

            if (envDict.TelemetryState) {
                if (envDict.TelemetryState
                        && envDict.TelemetryServerUrl != null
                        && !string.IsNullOrEmpty(envDict.TelemetryServerUrl))
                    new Task(() =>
                        Telemetry.PostTelemetryRecord(envDict.TelemetryServerUrl, record)).Start();

                if (envDict.TelemetryState
                        && envDict.TelemetryFilePath != null
                        && !string.IsNullOrEmpty(envDict.TelemetryFilePath))
                    new Task(() =>
                        Telemetry.WriteTelemetryRecord(envDict.TelemetryFilePath, record)).Start();
            }
        }
    }
}
