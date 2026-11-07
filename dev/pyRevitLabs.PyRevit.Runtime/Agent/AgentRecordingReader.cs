using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Revit-free reader of recordings written by <see cref="AgentRecordingStore"/>, shared by
    /// the in-Revit host and the <c>pyrevit mcp</c> server so <c>get_recording</c> works without Revit.
    /// </summary>
    internal static class AgentRecordingReader {
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

        public static string FindDirectory(string root, string id) {
            if (string.IsNullOrWhiteSpace(id) || !id.Trim().All(char.IsLetterOrDigit) || !Directory.Exists(root))
                return null;
            return Directory.GetDirectories(root, "*-" + id.Trim()).FirstOrDefault();
        }

        public static List<JObject> List(string root, int limit) {
            if (!Directory.Exists(root))
                return new List<JObject>();
            return Directory.GetDirectories(root)
                .OrderByDescending(Path.GetFileName, StringComparer.Ordinal)
                .Take(limit)
                .Select(directory => ReadSummary(directory))
                .ToList();
        }

        /// <summary>
        /// Reads a recording's summary and timeline. A recording without <c>recording.json</c>
        /// (still running, or interrupted by a crash) reports status <c>incomplete</c>.
        /// </summary>
        public static JObject ReadRecording(string directory, int offset, int limit) {
            var recording = ReadSummary(directory);
            var eventsPath = Path.Combine(directory, "events.jsonl");
            var events = new JArray();
            var total = 0;
            foreach (var entry in ReadEvents(eventsPath)) {
                if (total >= offset && events.Count < limit)
                    events.Add(entry);
                total++;
            }
            recording["events"] = events;
            recording["offset"] = offset;
            recording["total_events"] = total;
            recording["truncated"] = offset + events.Count < total;
            return recording;
        }

        private static IEnumerable<JObject> ReadEvents(string eventsPath) {
            if (!File.Exists(eventsPath))
                yield break;
            using (var stream = new FileStream(eventsPath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
            using (var reader = new StreamReader(stream, Utf8)) {
                string line;
                while ((line = reader.ReadLine()) != null) {
                    var entry = TryParse(line);
                    if (entry != null)
                        yield return entry;
                }
            }
        }

        private static JObject TryParse(string json) {
            if (string.IsNullOrWhiteSpace(json))
                return null;
            try {
                return JObject.Parse(json);
            }
            catch (Exception) {
                return null;
            }
        }

        private static JObject ReadSummary(string directory) {
            var path = Path.Combine(directory, "recording.json");
            JObject summary = null;
            if (File.Exists(path))
                summary = TryParse(File.ReadAllText(path, Utf8));
            if (summary == null)
                summary = new JObject {
                    ["id"] = Path.GetFileName(directory).Split('-').Last(),
                    ["status"] = "incomplete",
                };
            summary["directory"] = directory;
            return summary;
        }

    }
}
