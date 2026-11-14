using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Limits of one recording. Every limit bounds disk use and what an agent has to read.
    /// </summary>
    internal sealed class AgentRecordingOptions {
        public const int DefaultMaxEvents = 5000;
        public const int HardMaxEvents = 20000;
        public const int HardMaxScreenshots = 100;
        public const int HardMaxDurationSeconds = 4 * 60 * 60;

        public bool Screenshots { get; set; } = true;
        public double ScreenshotIntervalSeconds { get; set; } = 5;
        public int MaxScreenshots { get; set; } = 20;
        public int MaxEvents { get; set; } = DefaultMaxEvents;
        public int MaxDurationSeconds { get; set; } = 30 * 60;

        public static AgentRecordingOptions FromJson(JObject parameters) {
            var options = new AgentRecordingOptions();
            if (parameters == null)
                return options;
            options.Screenshots = parameters.Value<bool?>("screenshots") ?? options.Screenshots;
            options.ScreenshotIntervalSeconds = Bounded(parameters, "screenshot_interval_s", options.ScreenshotIntervalSeconds, 0, 3600);
            options.MaxScreenshots = (int)Bounded(parameters, "max_screenshots", options.MaxScreenshots, 0, HardMaxScreenshots, whole: true);
            options.MaxEvents = (int)Bounded(parameters, "max_events", options.MaxEvents, 1, HardMaxEvents, whole: true);
            options.MaxDurationSeconds = (int)Bounded(parameters, "max_duration_s", options.MaxDurationSeconds, 1, HardMaxDurationSeconds, whole: true);
            return options;
        }

        public JObject ToJson() {
            return new JObject {
                ["screenshots"] = Screenshots,
                ["screenshot_interval_s"] = ScreenshotIntervalSeconds,
                ["max_screenshots"] = MaxScreenshots,
                ["max_events"] = MaxEvents,
                ["max_duration_s"] = MaxDurationSeconds,
            };
        }

        private static double Bounded(JObject parameters, string name, double fallback, double min, double max, bool whole = false) {
            var token = parameters[name];
            if (token == null || token.Type == JTokenType.Null)
                return fallback;
            if (token.Type != JTokenType.Integer && token.Type != JTokenType.Float)
                throw new AgentException("invalid_params", $"'{name}' must be a number.");
            var value = token.Value<double>();
            if (double.IsNaN(value) || value < min || value > max)
                throw new AgentException("invalid_params", $"'{name}' must be between {min} and {max}.");
            if (whole && value != Math.Floor(value))
                throw new AgentException("invalid_params", $"'{name}' must be a whole number.");
            return value;
        }
    }

    /// <summary>
    /// Decides whether a screenshot may be taken now: a minimum interval since the last one and
    /// a maximum count.
    /// </summary>
    internal sealed class AgentScreenshotThrottle {
        private readonly TimeSpan interval;
        private readonly int maxCount;
        private TimeSpan? lastTaken;

        public AgentScreenshotThrottle(TimeSpan interval, int maxCount) {
            this.interval = interval;
            this.maxCount = maxCount;
        }

        public int Taken { get; private set; }

        public void Refund() {
            if (Taken > 0)
                Taken--;
        }

        public bool TryAcquire(TimeSpan now) {
            if (Taken >= maxCount)
                return false;
            if (lastTaken.HasValue && now - lastTaken.Value < interval)
                return false;
            lastTaken = now;
            Taken++;
            return true;
        }
    }

    /// <summary>
    /// Revit-free storage of one recording: an append-only <c>events.jsonl</c> timeline, a
    /// <c>screenshots</c> folder and a <c>recording.json</c> summary written on stop.
    /// </summary>
    /// <remarks>
    /// Invariant: events are appended as complete lines, so a recording interrupted by a Revit
    /// crash is still readable by <see cref="ReadRecording"/>. The event count is capped; once
    /// the cap is reached further events are counted in <c>dropped_events</c> and not stored.
    /// Recordings are local plaintext and may contain client data; nothing here sends them anywhere.
    /// </remarks>
    internal sealed class AgentRecordingStore {
        public const int MaxTextLength = 4000;
        public static readonly TimeSpan Retention = TimeSpan.FromDays(7);
        public const int MaxRecordings = 20;
        public const int MaxMarkLength = 16000;
        private const int SharingViolation = 32;
        private const int LockViolation = 33;

        private static readonly UTF8Encoding Utf8 = new UTF8Encoding(false);
        private readonly object sync = new object();
        private readonly System.Diagnostics.Stopwatch clock = System.Diagnostics.Stopwatch.StartNew();
        private readonly DateTime startedUtc = DateTime.UtcNow;
        private int sequence;
        private int dropped;
        private bool stopped;
        private FileStream activeLock;
        private FileStream events;
        private JObject stoppedSummary;

        private AgentRecordingStore(string id, string directory, AgentRecordingOptions options) {
            Id = id;
            Directory = directory;
            Options = options;
            activeLock = new FileStream(Path.Combine(directory, AgentRecordingReader.LockFileName), FileMode.Create, FileAccess.Write, FileShare.Read);
            events = new FileStream(Path.Combine(directory, "events.jsonl"), FileMode.Append, FileAccess.Write, FileShare.ReadWrite);
        }

        public string Id { get; }
        public string Directory { get; }
        public AgentRecordingOptions Options { get; }
        public TimeSpan Elapsed => clock.Elapsed;
        public string ScreenshotsDirectory => Path.Combine(Directory, "screenshots");

        public static AgentRecordingStore Create(string root, AgentRecordingOptions options) {
            var id = Guid.NewGuid().ToString("N").Substring(0, 8);
            var directory = Path.Combine(root, DateTime.Now.ToString("yyyyMMdd-HHmmss", CultureInfo.InvariantCulture) + "-" + id);
            System.IO.Directory.CreateDirectory(directory);
            try {
                return new AgentRecordingStore(id, directory, options);
            }
            catch (Exception) {
                System.IO.Directory.Delete(directory, recursive: true);
                throw;
            }
        }

        public static JToken BoundError(JToken error) {
            if (!(error is JObject fields))
                return error;
            var bounded = new JObject();
            foreach (var field in fields.Properties())
                bounded[field.Name] = field.Value.Type == JTokenType.String
                    ? Truncate(field.Value.Value<string>())
                    : field.Value;
            return bounded;
        }

        public static JToken ParseMarkData(string json) {
            if (string.IsNullOrEmpty(json))
                return JValue.CreateNull();
            if (json.Length > MaxMarkLength)
                return new JObject {
                    ["truncated"] = true,
                    ["original_length"] = json.Length,
                    ["preview"] = json.Substring(0, MaxTextLength),
                };
            try {
                return JToken.Parse(json);
            }
            catch (JsonException) {
                return new JValue(json);
            }
        }

        public static string Truncate(string text) {
            if (text == null || text.Length <= MaxTextLength)
                return text;
            return text.Substring(0, MaxTextLength) + "... [" + (text.Length - MaxTextLength) + " more characters]";
        }

        public bool Append(string kind, JObject data) {
            lock (sync) {
                if (stopped)
                    return false;
                if (clock.Elapsed.TotalSeconds >= Options.MaxDurationSeconds) {
                    dropped++;
                    return false;
                }
                if (sequence >= Options.MaxEvents) {
                    dropped++;
                    return false;
                }
                sequence++;
                var entry = new JObject {
                    ["seq"] = sequence,
                    ["t_ms"] = (long)clock.ElapsedMilliseconds,
                    ["time"] = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture),
                    ["kind"] = kind,
                };
                if (data != null)
                    foreach (var property in data.Properties())
                        entry[property.Name] = property.Value;
                var line = Utf8.GetBytes(entry.ToString(Formatting.None) + "\n");
                events.Write(line, 0, line.Length);
                events.Flush();
                return true;
            }
        }

        public JObject Stop(string reason) {
            lock (sync) {
                if (stopped)
                    return stoppedSummary;
                stopped = true;
                var summary = new JObject {
                    ["id"] = Id,
                    ["status"] = "stopped",
                    ["stop_reason"] = reason,
                    ["started"] = startedUtc.ToString("o", CultureInfo.InvariantCulture),
                    ["stopped"] = DateTime.UtcNow.ToString("o", CultureInfo.InvariantCulture),
                    ["duration_ms"] = (long)clock.ElapsedMilliseconds,
                    ["event_count"] = sequence,
                    ["dropped_events"] = dropped,
                    ["options"] = Options.ToJson(),
                };
                try {
                    File.WriteAllText(Path.Combine(Directory, "recording.json"), summary.ToString(Formatting.Indented), Utf8);
                }
                finally {
                    events.Dispose();
                    activeLock.Dispose();
                }
                stoppedSummary = summary;
                return summary;
            }
        }

        /// <summary>
        /// Deletes recordings older than <see cref="Retention"/> and, beyond that, all but the
        /// newest <see cref="MaxRecordings"/>; the folder named by <paramref name="keep"/> is never deleted.
        /// </summary>
        public static int Prune(string root, DateTime now, string keep) {
            if (!System.IO.Directory.Exists(root))
                return 0;
            var removed = 0;
            var directories = System.IO.Directory.GetDirectories(root)
                .OrderByDescending(Path.GetFileName, StringComparer.Ordinal)
                .ToList();
            for (var index = 0; index < directories.Count; index++) {
                var directory = directories[index];
                if (string.Equals(directory, keep, StringComparison.OrdinalIgnoreCase) || AgentRecordingReader.IsLive(directory))
                    continue;
                var expired = System.IO.Directory.GetLastWriteTime(directory) < now - Retention;
                if (!expired && index < MaxRecordings)
                    continue;
                try {
                    System.IO.Directory.Delete(directory, recursive: true);
                    removed++;
                }
                catch (Exception) {
                }
            }
            return removed;
        }
    }
}

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Merges consecutive output writes into one event, so a chatty script does not use up the
    /// event cap one line at a time.
    /// </summary>
    internal sealed class AgentOutputBuffer {
        private readonly StringBuilder text = new StringBuilder();

        public void Add(string chunk) {
            lock (text) {
                if (text.Length < AgentRecordingStore.MaxTextLength * 2)
                    text.Append(chunk);
            }
        }

        public string Drain() {
            lock (text) {
                if (text.Length == 0)
                    return null;
                var drained = AgentRecordingStore.Truncate(text.ToString());
                text.Clear();
                return drained;
            }
        }
    }
}
