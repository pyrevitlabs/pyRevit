using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Revit-free reader of recordings written by <see cref="AgentRecordingStore"/>, shared by
    /// the in-Revit host and the <c>pyrevit mcp</c> server so <c>get_recording</c> works without Revit.
    /// </summary>
    internal static class AgentRecordingReader {
        public const string LockFileName = ".active";
        public const int MaxPageChars = 200 * 1024;
        private const int SharingViolation = 32;
        private const int LockViolation = 33;
        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);

        /// <summary>
        /// True while some process still holds the recording's lock file, that is while it is being written.
        /// </summary>
        public static bool IsLive(string directory) {
            var lockPath = Path.Combine(directory, LockFileName);
            if (!File.Exists(lockPath))
                return false;
            try {
                using (new FileStream(lockPath, FileMode.Open, FileAccess.Write, FileShare.None)) {
                }
                return false;
            }
            catch (IOException ex) when ((ex.HResult & 0xFFFF) == SharingViolation || (ex.HResult & 0xFFFF) == LockViolation) {
                return true;
            }
            catch (IOException) {
                return false;
            }
        }

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
        /// reports status <c>recording</c> while another process holds its lock, otherwise <c>incomplete</c> (interrupted by a crash).
        /// </summary>
        public static JObject ReadRecording(string directory, int offset, int limit, int maxChars = MaxPageChars) {
            var recording = ReadSummary(directory);
            var eventsPath = Path.Combine(directory, "events.jsonl");
            var events = new JArray();
            var total = 0;
            var chars = 0;
            var full = false;
            foreach (var entry in ReadEvents(eventsPath)) {
                if (total >= offset && !full) {
                    var length = entry.ToString(Formatting.None).Length;
                    if (events.Count >= limit || (events.Count > 0 && chars + length > maxChars))
                        full = true;
                    else {
                        events.Add(entry);
                        chars += length;
                    }
                }
                total++;
            }
            recording["events"] = events;
            recording["offset"] = offset;
            recording["next_offset"] = offset + events.Count;
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

        private static JObject DescribeUnfinished(string directory) {
            var count = 0;
            JToken started = null;
            foreach (var entry in ReadEvents(Path.Combine(directory, "events.jsonl"))) {
                started = started ?? entry["time"];
                count++;
            }
            return new JObject {
                ["id"] = Path.GetFileName(directory).Split('-').Last(),
                ["status"] = IsLive(directory) ? "recording" : "incomplete",
                ["started"] = started,
                ["event_count"] = count,
            };
        }

        private static JObject ReadSummary(string directory) {
            var path = Path.Combine(directory, "recording.json");
            JObject summary = null;
            if (File.Exists(path))
                summary = TryParse(File.ReadAllText(path, Utf8));
            if (summary == null)
                summary = DescribeUnfinished(directory);
            summary["directory"] = directory;
            return summary;
        }

    }
}
