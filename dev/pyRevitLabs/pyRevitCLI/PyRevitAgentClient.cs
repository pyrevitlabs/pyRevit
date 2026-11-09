using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.IO.Pipes;
using System.Linq;
using System.Runtime.InteropServices;
using System.Security.Principal;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;

using Microsoft.Win32.SafeHandles;

using pyRevitLabs.Common;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// A running Revit whose pyRevit agent host registered itself under
    /// <c>%APPDATA%\pyRevit\agent\instances</c>.
    /// </summary>
    internal sealed class AgentInstance {
        public int ProcessId { get; set; }
        public string Pipe { get; set; }
        public string RevitVersion { get; set; }
        public string RevitBuild { get; set; }
        public string Started { get; set; }

        /// <summary>Name of the pyRevit clone the session runs; null when the host did not record it.</summary>
        public string Clone { get; set; }
        public string ClonePath { get; set; }
        public string Engine { get; set; }
        public string EngineVersion { get; set; }
        public string Commit { get; set; }
        public string ConfigRoot { get; set; }

        /// <summary>True for a session started by <c>pyrevit launch</c> rather than through the shared attachment.</summary>
        public bool PerLaunch { get; set; }

        public JObject ToJson() {
            var json = new JObject {
                ["pid"] = ProcessId,
                ["revit_version"] = RevitVersion,
                ["revit_build"] = RevitBuild,
                ["started"] = Started,
            };
            if (Clone != null) {
                json["clone"] = Clone;
                json["clone_path"] = ClonePath;
                json["engine"] = Engine;
                json["engine_version"] = EngineVersion;
                json["commit"] = Commit;
                json["config_root"] = ConfigRoot;
                json["per_launch"] = PerLaunch;
            }
            return json;
        }

        public string Describe() {
            var description = $"{RevitVersion} (pid {ProcessId})";
            return Clone == null ? description : $"{description} on {Clone}" + (Engine == null ? "" : $" {Engine}");
        }
    }

    /// <summary>
    /// What became of a request whose call failed.
    /// </summary>
    internal static class AgentOutcome {
        /// <summary>The request never reached the host. Safe to send again.</summary>
        public const string NotSent = "not_sent";

        /// <summary>The host refused the request before running any of it. Safe to send again.</summary>
        public const string NotRun = "not_run";

        /// <summary>
        /// The request was sent but no answer came back, so it may have run, may still run, or
        /// may never run. Look it up by its request id before sending it again.
        /// </summary>
        public const string Unknown = "unknown";
    }

    /// <summary>
    /// Error returned by an agent host, or raised while reaching one. <see cref="Code"/> is the
    /// host's stable error type (for example <c>revit_busy</c> or <c>no_active_document</c>).
    /// </summary>
    /// <remarks>
    /// <see cref="Message"/> is the text the host sent, followed by the request id, and by the run
    /// record or the lookup command when one can find the request; <see cref="HostMessage"/> is the
    /// text alone.
    /// </remarks>
    internal sealed class AgentClientException : Exception {
        public AgentClientException(
            string code, string message, string outcome = null, string requestId = null, string runId = null, JObject details = null)
            : base(message) {
            Code = code;
            Outcome = outcome;
            RequestId = requestId;
            RunId = runId;
            Details = details;
        }

        public string Code { get; }

        /// <summary>One of <see cref="AgentOutcome"/>, or null when the failure says nothing about it.</summary>
        public string Outcome { get; }

        /// <summary>The id the client gave the request, when it got as far as sending one.</summary>
        public string RequestId { get; }

        /// <summary>The run record the host left for a refused <c>run</c> request.</summary>
        public string RunId { get; }

        /// <summary>
        /// The host's other <c>error.data</c> fields, such as the candidate <c>views</c> of a
        /// <c>view_ambiguous</c> error, passed on to the caller unchanged.
        /// </summary>
        public JObject Details { get; }

        public string HostMessage => base.Message;

        public override string Message {
            get {
                if (Outcome == null || RequestId == null)
                    return base.Message;
                if (RunId != null)
                    return base.Message + " (request " + RequestId + ", run record " + RunId + "; see 'pyrevit agent show " + RunId + "')";
                if (Outcome == AgentOutcome.Unknown)
                    return base.Message + " (request " + RequestId + "; look it up with 'pyrevit agent show " + RequestId + "')";
                return base.Message + " (request " + RequestId + ")";
            }
        }

        public JObject ToJson() {
            var json = new JObject { ["error"] = Code, ["message"] = HostMessage };
            if (Outcome != null)
                json["outcome"] = Outcome;
            if (RequestId != null)
                json["request_id"] = RequestId;
            if (RunId != null)
                json["run_id"] = RunId;
            if (Details != null) {
                foreach (var detail in Details.Properties()) {
                    if (json[detail.Name] == null)
                        json[detail.Name] = detail.Value;
                }
            }
            return json;
        }
    }

    /// <summary>
    /// Client side of the agent host's pipe protocol (newline-delimited JSON-RPC 2.0), plus
    /// discovery of running hosts and of recorded runs.
    /// </summary>
    /// <remarks>
    /// Each call opens its own pipe connection. The host serves one connection at a time,
    /// so callers that may overlap (the MCP server) must serialize their calls to each host.
    /// </remarks>
    internal static class PyRevitAgentClient {
        private static readonly Encoding Utf8 = new UTF8Encoding(false);
        private static readonly Regex RunIdPattern = new Regex("^[A-Za-z0-9]+$", RegexOptions.Compiled);
        private static readonly Regex RequestIdPattern = new Regex("^req-[0-9a-f]{12}$", RegexOptions.Compiled);

        /// <summary>
        /// How long <see cref="Call"/> waits for the host's pipe. Shortened by tests.
        /// </summary>
        internal static int ConnectTimeoutMs = 10000;

        internal const string CloneSelectorPrefix = "clone:";

        /// <summary>
        /// How long <see cref="Ping"/> waits for the answer once connected. Shortened by tests.
        /// </summary>
        internal static int PingTimeoutMs = 5000;

        /// <summary>
        /// How long <see cref="Ping"/> waits for the host's pipe. A host serving another client
        /// never accepts, so a ping must not wait the full <see cref="ConnectTimeoutMs"/>.
        /// Shortened by tests.
        /// </summary>
        internal static int PingConnectTimeoutMs = 1500;

        /// <summary>
        /// Replaces the folder that holds host registrations and run records. Set by tests so
        /// they never read or write the real user profile.
        /// </summary>
        internal static string AgentDirOverride;

        internal static Func<Process, string> ProcessNameReader = process => process.ProcessName;
        internal static Func<Process, DateTime> ProcessStartTimeReader = process => process.StartTime;
        /// <summary>
        /// Whether a pipe exists, read from the pipe namespace listing.
        /// </summary>
        /// <remarks>
        /// Invariant: never open the pipe to check it. Opening it, as <c>File.Exists</c> does,
        /// connects to the host's only server instance and can lock a real client out.
        /// </remarks>
        internal static Func<string, bool> PipeExists = pipeName => Directory.EnumerateFiles(PipeRoot)
            .Any(path => string.Equals(path, PipeRoot + pipeName, StringComparison.OrdinalIgnoreCase));

        private const string PipeRoot = @"\\.\pipe\";
        internal static Action<int> DiscoveryDelay = Thread.Sleep;

        private enum InstanceLiveness {
            Live,
            Stale,
            Uncertain,
        }

        public static string AgentDir => AgentDirOverride ?? PyRevitLabsConsts.AgentPath;
        public static string InstancesDir => Path.Combine(AgentDir, "instances");
        public static string RunsDir => Path.Combine(AgentDir, "runs");

        /// <summary>
        /// Registered hosts whose process metadata or named pipe establishes liveness, newest first.
        /// Only certainly stale registration files are removed best-effort.
        /// </summary>
        public static List<AgentInstance> GetInstances() {
            var instances = new List<AgentInstance>();
            if (!Directory.Exists(InstancesDir))
                return instances;

            foreach (var file in Directory.GetFiles(InstancesDir, "*.json")) {
                try {
                    var data = JObject.Parse(File.ReadAllText(file));
                    var instance = new AgentInstance {
                        ProcessId = data.Value<int>("pid"),
                        Pipe = data.Value<string>("pipe"),
                        RevitVersion = data.Value<string>("revit_version"),
                        RevitBuild = data.Value<string>("revit_build"),
                        Started = data["started"]?.ToString(Formatting.None).Trim('"'),
                        Clone = data.Value<string>("clone"),
                        ClonePath = data.Value<string>("clone_path"),
                        Engine = data.Value<string>("engine"),
                        EngineVersion = data.Value<string>("engine_version"),
                        Commit = data.Value<string>("commit"),
                        ConfigRoot = data.Value<string>("config_root"),
                        PerLaunch = data.Value<bool?>("per_launch") ?? false,
                    };
                    var liveness = GetLiveness(instance);
                    if (liveness == InstanceLiveness.Live || (liveness == InstanceLiveness.Uncertain && HasPipe(instance)))
                        instances.Add(instance);
                    else if (liveness == InstanceLiveness.Stale)
                        File.Delete(file);
                }
                catch (Exception) {
                }
            }

            return instances.OrderByDescending(instance => instance.Started).ToList();
        }

        /// <summary>
        /// Picks the target host. <paramref name="selector"/> is a Revit process id, a Revit
        /// year (e.g. 2024) or the name or path of the pyRevit clone the session runs; an exact
        /// process id match wins over a year, see <see cref="Match"/>.
        /// Without a selector, exactly one running host is required.
        /// </summary>
        /// <exception cref="AgentClientException">
        /// <c>no_revit</c> when nothing matches, <c>ambiguous_revit</c> when several hosts match.
        /// </exception>
        public static AgentInstance Resolve(string selector) {
            var instances = GetInstances();
            if (instances.Count == 0)
                throw new AgentClientException(
                    "no_revit",
                    "No running Revit with the pyRevit agent host was found. Start Revit with "
                    + "'[agent] enabled = true' (pyrevit configs agent enable).");

            var matches = Match(instances, selector);
            if (matches.Count == 0)
                throw new AgentClientException("no_revit", "No running Revit matches '" + selector + "'.");

            if (matches.Count > 1)
                throw new AgentClientException(
                    "ambiguous_revit",
                    "Several Revit sessions are running; pick one with a year, process id or clone name: "
                    + string.Join(", ", matches.Select(m => m.Describe())));

            return matches[0];
        }

        /// <summary>
        /// Filters <paramref name="instances"/> by a Revit selector without checking liveness.
        /// A blank selector keeps every instance.
        /// </summary>
        /// <remarks>
        /// Invariant: a selector equal to an instance's process id selects by process id, whatever
        /// its value. Only when no process id matches is a number in [2000, 2100) read as a Revit
        /// year; any other number is a process id that matched nothing. Windows can hand out
        /// process ids in the year range, so the year rule must never shadow an exact pid match.
        /// Years compare in canonical form, so " 2024 " or "02024" select Revit 2024.
        /// A selector that is not a number selects the sessions whose clone has that name
        /// (ignoring case) or that path; a bare word is only ever a name, so it can't select
        /// another clone through a folder of that name under the current directory. Sessions
        /// that recorded no clone never match it.
        /// A clone whose name is a number is selected as <c>clone:&lt;name&gt;</c>, which is never
        /// read as a process id or a year.
        /// </remarks>
        internal static List<AgentInstance> Match(IReadOnlyList<AgentInstance> instances, string selector) {
            if (string.IsNullOrWhiteSpace(selector))
                return instances.ToList();
            var trimmed = selector.Trim();
            if (trimmed.StartsWith(CloneSelectorPrefix, StringComparison.OrdinalIgnoreCase))
                return instances.Where(instance => MatchesClone(instance, trimmed.Substring(CloneSelectorPrefix.Length).Trim())).ToList();
            if (!int.TryParse(selector, out var number))
                return instances.Where(instance => MatchesClone(instance, trimmed)).ToList();

            var byProcessId = instances.Where(instance => instance.ProcessId == number).ToList();
            if (byProcessId.Count > 0 || number < 2000 || number >= 2100)
                return byProcessId;
            var year = number.ToString(CultureInfo.InvariantCulture);
            return instances.Where(instance => instance.RevitVersion == year).ToList();
        }

        private static bool MatchesClone(AgentInstance instance, string selector) {
            if (instance.Clone == null)
                return false;
            if (string.Equals(instance.Clone, selector, StringComparison.OrdinalIgnoreCase))
                return true;
            if (!LooksLikePath(selector))
                return false;
            var recordedPath = NormalizePath(instance.ClonePath);
            return recordedPath != null && string.Equals(recordedPath, NormalizePath(selector), StringComparison.OrdinalIgnoreCase);
        }

        private static bool LooksLikePath(string selector) {
            return Path.IsPathRooted(selector) || selector.IndexOfAny(new[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar }) >= 0;
        }

        private static string NormalizePath(string path) {
            try {
                return Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            }
            catch (Exception) {
                return null;
            }
        }

        [DllImport("kernel32.dll", SetLastError = true)]
        private static extern bool GetNamedPipeServerProcessId(SafePipeHandle pipe, out uint serverProcessId);

        private static void RequireServerProcess(NamedPipeClientStream pipe, AgentInstance instance) {
            if (!GetNamedPipeServerProcessId(pipe.SafePipeHandle, out var serverProcessId) || serverProcessId != (uint)instance.ProcessId)
                throw new AgentClientException(
                    "pipe_error",
                    $"The agent pipe of Revit {instance.RevitVersion} (pid {instance.ProcessId}) is served by another process; "
                    + "no request was sent.",
                    AgentOutcome.NotSent);
        }

        /// <summary>
        /// Pings a host, waiting at most <see cref="PingConnectTimeoutMs"/> for the pipe and
        /// <see cref="PingTimeoutMs"/> for its answer, so a busy or hung Revit can't stall a status check.
        /// </summary>
        /// <exception cref="AgentClientException">
        /// See <see cref="Call"/>; <c>revit_busy</c> when the pipe isn't accepted in time and
        /// <c>no_answer</c> when the answer doesn't come in time.
        /// </exception>
        public static void Ping(AgentInstance instance) {
            Call(instance, "ping", answerTimeoutMs: PingTimeoutMs, connectTimeoutMs: PingConnectTimeoutMs);
        }

        /// <summary>
        /// Sends one request and waits for its response. By default there is no read timeout:
        /// a modify run legitimately waits for the user to answer the approval prompt in Revit.
        /// </summary>
        /// <remarks>
        /// The request goes out under a fresh <see cref="NewRequestId"/>, which the host keeps in
        /// the run record. A failure carries an <see cref="AgentClientException.Outcome"/>: a
        /// request that was never sent, one the host refused, or one whose answer was lost.
        /// Important: giving up on the answer, through <paramref name="cancellation"/> or
        /// <paramref name="answerTimeoutMs"/>, only closes the connection. A request already sent
        /// keeps running in Revit, so its outcome is <see cref="AgentOutcome.Unknown"/>.
        /// A caller that must name the request in its own errors passes <paramref name="requestId"/>.
        /// </remarks>
        /// <exception cref="AgentClientException">
        /// <c>cancelled</c> when <paramref name="cancellation"/> fires and <c>no_answer</c> when
        /// <paramref name="answerTimeoutMs"/> passes, besides the connection and host errors.
        /// </exception>
        public static JToken Call(
            AgentInstance instance, string method, JObject parameters = null,
            CancellationToken cancellation = default, int? answerTimeoutMs = null, int? connectTimeoutMs = null,
            string requestId = null) {
            requestId ??= NewRequestId();
            var request = new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = requestId,
                ["method"] = method,
                ["params"] = parameters ?? new JObject(),
            };

            var sent = false;
            string responseLine;
            try {
                using (var pipe = new NamedPipeClientStream(".", instance.Pipe, PipeDirection.InOut, PipeOptions.Asynchronous, TokenImpersonationLevel.Identification))
                using (var answer = CancellationTokenSource.CreateLinkedTokenSource(cancellation)) {
                    pipe.ConnectAsync(connectTimeoutMs ?? ConnectTimeoutMs, cancellation).GetAwaiter().GetResult();
                    RequireServerProcess(pipe, instance);
                    var writer = new StreamWriter(pipe, Utf8) { AutoFlush = true, NewLine = "\n" };
                    var reader = new BoundedLineReader(new StreamReader(pipe, Utf8));
                    writer.WriteLine(request.ToString(Formatting.None));
                    sent = true;
                    if (answerTimeoutMs.HasValue)
                        answer.CancelAfter(answerTimeoutMs.Value);
                    responseLine = reader.ReadLineAsync(answer.Token).GetAwaiter().GetResult();
                }
            }
            catch (OperationCanceledException) when (cancellation.IsCancellationRequested) {
                throw new AgentClientException(
                    "cancelled",
                    "The call was cancelled." + LostAnswerNotice(sent),
                    sent ? AgentOutcome.Unknown : AgentOutcome.NotSent,
                    requestId);
            }
            catch (OperationCanceledException) {
                throw new AgentClientException(
                    "no_answer",
                    $"Revit {instance.RevitVersion} (pid {instance.ProcessId}) accepted the connection but did not answer "
                    + $"within {answerTimeoutMs / 1000.0:0.#}s." + LostAnswerNotice(sent),
                    AgentOutcome.Unknown,
                    requestId);
            }
            catch (TimeoutException) {
                throw new AgentClientException(
                    "revit_busy",
                    $"Could not connect to Revit {instance.RevitVersion} (pid {instance.ProcessId}); "
                    + "another client may be using it. The request was not sent, so it is safe to send again.",
                    AgentOutcome.NotSent,
                    requestId);
            }
            catch (IOException ex) {
                throw new AgentClientException(
                    "pipe_error",
                    "Connection to Revit failed: " + ex.Message + LostAnswerNotice(sent),
                    sent ? AgentOutcome.Unknown : AgentOutcome.NotSent,
                    requestId);
            }
            catch (InvalidDataException ex) {
                throw new AgentClientException(
                    "pipe_error",
                    "Revit's answer was refused: " + ex.Message + LostAnswerNotice(sent),
                    AgentOutcome.Unknown,
                    requestId);
            }
            catch (Exception ex) when (ex is not AgentClientException) {
                throw new AgentClientException(
                    "pipe_error",
                    "Connection to Revit failed (" + ex.GetType().Name + ")." + LostAnswerNotice(sent),
                    sent ? AgentOutcome.Unknown : AgentOutcome.NotSent,
                    requestId);
            }

            if (responseLine == null)
                throw new AgentClientException(
                    "pipe_error",
                    "Revit closed the connection without answering." + LostAnswerNotice(sent),
                    sent ? AgentOutcome.Unknown : AgentOutcome.NotSent,
                    requestId);

            JObject response;
            try {
                response = JObject.Parse(responseLine);
            }
            catch (JsonException) {
                throw new AgentClientException(
                    "pipe_error",
                    "Revit sent an answer that could not be read." + LostAnswerNotice(sent: true),
                    AgentOutcome.Unknown,
                    requestId);
            }
            if (response["error"] is JObject error) {
                var data = error["data"] as JObject;
                var details = data == null ? null : new JObject(data.Properties()
                    .Where(field => field.Name != "type" && field.Name != "outcome" && field.Name != "run_id"));
                throw new AgentClientException(
                    data?.Value<string>("type") ?? "error",
                    error.Value<string>("message"),
                    data?.Value<string>("outcome"),
                    requestId,
                    data?.Value<string>("run_id"),
                    details != null && details.HasValues ? details : null);
            }
            return response["result"];
        }

        /// <summary>
        /// A fresh id for one request, in the form <c>req-</c> and twelve hex digits.
        /// </summary>
        public static string NewRequestId() {
            return "req-" + Guid.NewGuid().ToString("N").Substring(0, 12);
        }

        internal static string LostAnswerNotice(bool sent) {
            return sent
                ? " The request was sent and its outcome is unknown: it may have run or may still run. "
                    + "Look it up by its request id before sending it again."
                : " The request was not sent, so it is safe to send again.";
        }

        /// <summary>
        /// Finds a recorded run folder by its run id (the folder name ends with the id), or by the
        /// request id (<c>req-</c> and twelve hex digits) the host kept in the record.
        /// </summary>
        /// <remarks>
        /// A request id is matched against <c>request.json</c>, see <see cref="FindRunDirByRequestId"/>.
        /// Any other id that isn't letters and digits matches nothing: a run id is used in a directory
        /// search pattern, where a wildcard would match an unrelated run and a path segment would throw.
        /// </remarks>
        public static string FindRunDir(string runId) {
            if (string.IsNullOrWhiteSpace(runId) || !Directory.Exists(RunsDir))
                return null;
            var trimmed = runId.Trim();
            if (RequestIdPattern.IsMatch(trimmed))
                return FindRunDirByRequestId(trimmed);
            if (!RunIdPattern.IsMatch(trimmed))
                return null;
            return Directory.GetDirectories(RunsDir, "*-" + trimmed).FirstOrDefault();
        }

        /// <summary>
        /// Finds the run folder the host recorded for a request id, newest first. The folder
        /// is either a run that started or a <c>not_run</c> record of a refused request.
        /// </summary>
        public static string FindRunDirByRequestId(string requestId) {
            if (!RequestIdPattern.IsMatch(requestId ?? string.Empty) || !Directory.Exists(RunsDir))
                return null;
            foreach (var runDir in GetRecentRunDirs(int.MaxValue)) {
                try {
                    var requestPath = Path.Combine(runDir, "request.json");
                    if (File.Exists(requestPath) && JObject.Parse(File.ReadAllText(requestPath)).Value<string>("request_id") == requestId)
                        return runDir;
                }
                catch (Exception) {
                }
            }
            return null;
        }

        public static List<string> GetRecentRunDirs(int limit) {
            if (!Directory.Exists(RunsDir))
                return new List<string>();
            return Directory.GetDirectories(RunsDir)
                .OrderByDescending(Path.GetFileName, StringComparer.Ordinal)
                .Take(limit)
                .ToList();
        }

        private static InstanceLiveness GetLiveness(AgentInstance instance) {
            try {
                using (var process = Process.GetProcessById(instance.ProcessId)) {
                    try {
                        if (process.HasExited)
                            return InstanceLiveness.Stale;
                    }
                    catch (Exception) {
                    }

                    var hasRevitName = false;
                    try {
                        if (!string.Equals(ProcessNameReader(process), "Revit", StringComparison.OrdinalIgnoreCase))
                            return InstanceLiveness.Stale;
                        hasRevitName = true;
                    }
                    catch (Exception) {
                    }

                    if (DateTimeOffset.TryParse(instance.Started, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal, out var started)) {
                        try {
                            if (ProcessStartTimeReader(process).ToUniversalTime() - started.UtcDateTime > TimeSpan.FromSeconds(2))
                                return InstanceLiveness.Stale;
                            if (hasRevitName)
                                return InstanceLiveness.Live;
                        }
                        catch (Exception) {
                        }
                    }

                    return InstanceLiveness.Uncertain;
                }
            }
            catch (ArgumentException) {
                return InstanceLiveness.Stale;
            }
            catch (Exception) {
                return InstanceLiveness.Uncertain;
            }
        }

        private static bool HasPipe(AgentInstance instance) {
            if (string.IsNullOrWhiteSpace(instance.Pipe))
                return false;

            for (var attempt = 0; attempt < 3; attempt++) {
                if (attempt > 0)
                    DiscoveryDelay(300);
                if (PipeExists(instance.Pipe))
                    return true;
            }

            return false;
        }
    }
}
