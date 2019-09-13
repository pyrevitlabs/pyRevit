using System.Collections.Generic;
using System.Net;
using System.Web.Script.Serialization;
using System.IO;

using pyRevitLabs.Common;

namespace PyRevitLabs.PyRevit.Runtime {
    public static class Telemetry {
        public static string SerializeTelemetryRecord(object telemetryRecord) {
            return new JavaScriptSerializer().Serialize(telemetryRecord);
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

            var telemetryData = new JavaScriptSerializer().Deserialize<List<T>>(existingTelemetryData);

            telemetryData.Add(telemetryRecord);

            existingTelemetryData = new JavaScriptSerializer().Serialize(telemetryData);
            File.WriteAllText(telemetryFilePath, existingTelemetryData);
        }
    }
}
