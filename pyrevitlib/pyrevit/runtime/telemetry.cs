using System;
using System.Collections.Generic;
using System.Net;
using System.IO;
using System.Diagnostics;

using Autodesk.Revit.UI;
using Autodesk.Revit.ApplicationServices;

using pyRevitLabs.Json;
using pyRevitLabs.Common;
using pyRevitLabs.TargetApps.Revit;

namespace PyRevitLabs.PyRevit.Runtime {
    public class TelemetryRecord {
        // schema
        public Dictionary<string, string> meta { get; private set; }

        // when?
        public string timestamp { get; private set; }
        // by who?
        public string host_user { get; private set; }


        public TelemetryRecord() {
            meta = new Dictionary<string, string> {
                { "schema", "2.0"},
            };

            timestamp = Telemetry.GetTelemetryTimeStamp();
            host_user = UserEnv.GetLoggedInUserName() ?? UserEnv.GetExecutingUserName();
        }
    }

    public static class Telemetry {
        private static string _exeBuild = null;
        
        public static string SerializeTelemetryRecord(object telemetryRecord) {
            return JsonConvert.SerializeObject(telemetryRecord);
        }

        public static string PostTelemetryRecord(string telemetryServerUrl, object telemetryRecord) {
            var httpWebRequest = (HttpWebRequest)WebRequest.Create(telemetryServerUrl);
            httpWebRequest.ContentType = "application/json";
            httpWebRequest.Method = "POST";
            httpWebRequest.UserAgent = PyRevitLabsConsts.ProductName;

            using (var streamWriter = new StreamWriter(httpWebRequest.GetRequestStream())) {
                // serialize and write
                string json = SerializeTelemetryRecord(telemetryRecord);
                streamWriter.Write(json);
                streamWriter.Flush();
                streamWriter.Close();
            }

            var httpResponse = (HttpWebResponse)httpWebRequest.GetResponse();
            using (var streamReader = new StreamReader(httpResponse.GetResponseStream())) {
                return streamReader.ReadToEnd();
            }
        }

        public static void WriteTelemetryRecord<T>(string telemetryFilePath, T telemetryRecord) {
            string existingTelemetryData = "[]";
            if (File.Exists(telemetryFilePath)) {
                existingTelemetryData = File.ReadAllText(telemetryFilePath);
            }
            else {
                File.WriteAllText(telemetryFilePath, existingTelemetryData);
            }

            var telemetryData = JsonConvert.DeserializeObject<List<T>>(existingTelemetryData);

            telemetryData.Add(telemetryRecord);

            existingTelemetryData = JsonConvert.SerializeObject(telemetryData);
            File.WriteAllText(telemetryFilePath, existingTelemetryData);
        }

        public static string GetTelemetryTimeStamp() {
            var env = new EnvDictionary();
            if (env.TelemetryUTCTimeStamps)
                return GetISOTimeStamp(DateTime.Now.ToUniversalTime()); // 2019-09-27T23:22:41.1355Z
            else
                return GetISOTimeStamp(DateTime.Now);                   // 2019-09-27T16:15:56.9528-07:00
        }

        private static string GetISOTimeStamp(DateTime dtimeValue) {
            // higher resolution timestamp for telemetry

            return dtimeValue.ToString("yyyy-MM-ddTHH:mm:ss.ffffK");
        }

        public static string GetRevitUser(object source) {
            string username = string.Empty;
            
            switch (source) {
                case UIApplication uiapp:
                    username = uiapp.Application.Username;
                    break;

                case Application app:
                    username = app.Username;
                    break;
            }

            return username;
        }

        public static string GetRevitVersion(object source) {
            string revit = string.Empty;
            
            switch (source) {
                case UIControlledApplication uictrlapp:
                    revit = uictrlapp.ControlledApplication.VersionNumber;
                    break;
                case UIApplication uiapp:
                    revit = uiapp.Application.VersionNumber;
                    break;

                case ControlledApplication ctrlapp:
                    revit = ctrlapp.VersionNumber;
                    break;

                case Application app:
                    revit = app.VersionNumber;
                    break;
            }
            
            return revit;
        }

        public static string GetRevitBuild(object source) {
            // determine build number
            string revitbuild = string.Empty;

#if (REVIT2013 || REVIT2014 || REVIT2015 || REVIT2016 || REVIT2017 || REVIT2018 || REVIT2019 || REVIT2020)
            switch (source) {
                case UIControlledApplication uictrlapp:
                    revitbuild = uictrlapp.ControlledApplication.VersionBuild;
                    break;
                case UIApplication uiapp:
                    revitbuild = uiapp.Application.VersionBuild;
                    break;
                case ControlledApplication ctrlapp:
                    revitbuild = ctrlapp.VersionBuild;
                    break;
                case Application app:
                    revitbuild = app.VersionBuild;
                    break;
            }
#else
            // Revit 2021 has a bug on .VersionBuild
            // it reports identical value as .VersionNumber
            // let's give a invalid, but correctly formatted value to the telemetry server
            if (_exeBuild is null) {
                string revitExePath = Process.GetCurrentProcess().MainModule.FileName;
                if (revitExePath != null && revitExePath != string.Empty) {
                    HostProductInfo pinfo = RevitProductData.GetBinaryProductInfo(revitExePath);
                    if (pinfo.build != null && pinfo.build != string.Empty) {
                        revitbuild = string.Format("{0}({1})", pinfo.build, pinfo.target);
                        _exeBuild = revitbuild;
                    }
                }
            }
            else
                revitbuild = _exeBuild;
#endif
            return revitbuild;
        }
    }
}
