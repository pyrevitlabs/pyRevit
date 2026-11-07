using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;

namespace pyRevitCLI {
    /// <summary>
    /// <c>pyrevit mcp</c>: a Model Context Protocol server over stdio that exposes running
    /// Revit sessions to MCP clients (Claude Code, Codex, Cursor, VS Code, ...).
    /// </summary>
    /// <remarks>
    /// The server is a thin translator: every tool call maps to one request on the in-Revit
    /// agent host's pipe (see <see cref="PyRevitAgentClient"/>), except <c>get_run</c>, which
    /// reads the local run records. Safety lives in the host, not here: the host enforces the
    /// policy, the transaction group and the approval prompt.
    /// Invariant: stdout carries protocol messages only. Logging is silenced for the whole
    /// session and every write goes through one lock.
    /// Implements the tools subset of MCP (initialize, ping, tools/list, tools/call) with
    /// newline-delimited JSON-RPC 2.0; no SDK dependency.
    /// Malformed request fields receive JSON-RPC errors; notifications receive no response.
    /// Unexpected dispatch failures receive an internal error without ending the session.
    /// Calls to one Revit are serialized, because its host serves one connection at a time; calls
    /// to different Revit sessions never wait for each other. <c>notifications/cancelled</c> stops
    /// a call that waits for its turn or for Revit's answer, but cannot stop what Revit already runs.
    /// </remarks>
    internal sealed class PyRevitMcpServer {
        private const string LatestProtocolVersion = "2025-06-18";
        private static readonly string[] SupportedProtocolVersions = {
            "2025-06-18", "2025-03-26", "2024-11-05",
        };
        private static readonly TimeSpan ProgressInterval = TimeSpan.FromSeconds(10);
        private const int MaxRunResultPage = 200 * 1024;
        private const int MaxTitleLength = 120;
        private const int MaxReasonLength = 300;

        private readonly string defaultRevit;
        private readonly object writeLock = new object();
        private readonly ConcurrentDictionary<string, SemaphoreSlim> revitGates = new ConcurrentDictionary<string, SemaphoreSlim>();
        private readonly ConcurrentDictionary<string, CancellationTokenSource> pendingCalls = new ConcurrentDictionary<string, CancellationTokenSource>();
        private readonly AsyncLocal<CancellationToken> callCancellation = new AsyncLocal<CancellationToken>();
        private readonly List<McpTool> tools;
        private TextWriter output;
        private volatile string clientName;

        private PyRevitMcpServer(string defaultRevit) {
            this.defaultRevit = defaultRevit;
            tools = CreateTools();
        }

        public static void Serve(string defaultRevit) {
            var utf8 = new UTF8Encoding(false);
            Serve(
                defaultRevit,
                new StreamReader(System.Console.OpenStandardInput(), utf8),
                new StreamWriter(System.Console.OpenStandardOutput(), utf8) { AutoFlush = true, NewLine = "\n" });
        }

        /// <summary>
        /// Serves requests read from <paramref name="input"/> until it ends, writing responses to
        /// <paramref name="output"/>. Lets tests drive the server without a process.
        /// </summary>
        internal static void Serve(string defaultRevit, TextReader input, TextWriter output) {
            new PyRevitMcpServer(defaultRevit).Run(input, output);
        }

        private void Run(TextReader input, TextWriter output) {
            LogManager.Configuration = new LoggingConfiguration();
            this.output = output;

            var inFlight = new List<Task>();
            string line;
            while ((line = input.ReadLine()) != null) {
                if (string.IsNullOrWhiteSpace(line))
                    continue;

                JObject message;
                try {
                    using var reader = new JsonTextReader(new StringReader(line)) { DateParseHandling = DateParseHandling.None };
                    message = JObject.Load(reader);
                    while (reader.Read()) { }
                }
                catch (JsonException) {
                    Write(Error(null, -32700, "Parse error"));
                    continue;
                }

                var method = (message["method"] as JValue)?.Value as string;
                var id = message["id"];
                if (id == null) {
                    if (method == "notifications/cancelled")
                        Cancel((message["params"] as JObject)?["requestId"]);
                    continue;
                }
                if (id.Type != JTokenType.Integer && id.Type != JTokenType.Float
                    && id.Type != JTokenType.String && id.Type != JTokenType.Null) {
                    Write(Error(null, -32600, "Invalid Request"));
                    continue;
                }
                if (method == null) {
                    Write(Error(id, -32600, "Invalid Request"));
                    continue;
                }

                var parameters = message["params"] as JObject ?? new JObject();
                try {
                    switch (method) {
                        case "initialize":
                            if ((parameters["protocolVersion"] as JValue)?.Value is not string) {
                                Write(Error(id, -32602, "Invalid params: missing or invalid 'protocolVersion'; expected a string."));
                                break;
                            }
                            Write(Result(id, Initialize(parameters)));
                            break;
                        case "ping":
                            Write(Result(id, new JObject()));
                            break;
                        case "tools/list":
                            Write(Result(id, new JObject { ["tools"] = new JArray(tools.Select(tool => tool.Describe())) }));
                            break;
                        case "tools/call":
                            inFlight.RemoveAll(task => task.IsCompleted);
                            var cancellation = new CancellationTokenSource();
                            var key = id.ToString(Formatting.None);
                            var tracked = pendingCalls.TryAdd(key, cancellation);
                            inFlight.Add(Task.Run(() => {
                                try {
                                    CallTool(id, parameters, cancellation.Token);
                                }
                                finally {
                                    if (tracked)
                                        pendingCalls.TryRemove(key, out _);
                                }
                            }));
                            break;
                        default:
                            Write(Error(id, -32601, "Method not found"));
                            break;
                    }
                }
                catch (Exception) {
                    Write(Error(id, -32603, "Internal error"));
                }
            }

            Task.WaitAll(inFlight.ToArray());
        }

        /// <remarks>
        /// Remembers the client's name from <c>clientInfo</c>, so every request to Revit can say
        /// which client sent it and the agent panel can show it. The name is only a label, so a
        /// malformed <c>clientInfo</c> is ignored rather than refused.
        /// </remarks>
        private JObject Initialize(JObject parameters) {
            clientName = ((parameters["clientInfo"] as JObject)?["name"] as JValue)?.Value as string;
            var requested = (parameters["protocolVersion"] as JValue)?.Value as string;
            return new JObject {
                ["protocolVersion"] = SupportedProtocolVersions.Contains(requested) ? requested : LatestProtocolVersion,
                ["capabilities"] = new JObject { ["tools"] = new JObject { ["listChanged"] = false } },
                ["serverInfo"] = new JObject {
                    ["name"] = "pyrevit",
                    ["title"] = "pyRevit",
                    ["version"] = PyRevitCLI.CLIInfoVersion,
                },
                ["instructions"] = PyRevitAgentSkills.Instructions(PyRevitAgentSkills.Load()),
            };
        }

        private void Cancel(JToken requestId) {
            if (requestId != null && pendingCalls.TryGetValue(requestId.ToString(Formatting.None), out var cancellation))
                cancellation.Cancel();
        }

        private void CallTool(JToken id, JObject parameters, CancellationToken cancellation) {
            callCancellation.Value = cancellation;
            Timer progress = null;
            try {
                JObject result;
                try {
                    var name = (parameters["name"] as JValue)?.Value as string;
                    if (string.IsNullOrWhiteSpace(name)) {
                        Write(Error(id, -32602, "Invalid params: missing or invalid 'name'; expected a non-empty string."));
                        return;
                    }
                    if (parameters["arguments"] != null && parameters["arguments"] is not JObject) {
                        Write(Error(id, -32602, "Invalid params: 'arguments' must be an object."));
                        return;
                    }
                    var arguments = parameters["arguments"] as JObject ?? new JObject();
                    var progressToken = (parameters["_meta"] as JObject)?["progressToken"];
                    progress = StartProgress(progressToken);
                    var payload = Dispatch(name, arguments);
                    var isError = payload is JObject run && run.Value<string>("status") == "error";
                    result = payload is JObject captured && captured["image_base64"] != null
                        ? ImageResult(captured)
                        : ToolResult(payload.Type == JTokenType.String ? payload.ToString() : payload.ToString(Formatting.None), isError);
                }
                catch (AgentClientException ex) {
                    result = ToolResult(ex.ToJson().ToString(Formatting.None), true);
                }
                catch (InvalidCastException) {
                    result = ToolResult(new JObject { ["error"] = "invalid_params", ["message"] = "Invalid tool argument type." }.ToString(Formatting.None), true);
                }
                catch (FormatException) {
                    result = ToolResult(new JObject { ["error"] = "invalid_params", ["message"] = "Invalid tool argument format." }.ToString(Formatting.None), true);
                }
                catch (OverflowException) {
                    result = ToolResult(new JObject { ["error"] = "invalid_params", ["message"] = "Tool argument out of range." }.ToString(Formatting.None), true);
                }
                catch (Exception ex) {
                    result = ToolResult(new JObject { ["error"] = "server_error", ["message"] = ex.Message }.ToString(Formatting.None), true);
                }
                StopProgress(progress);
                progress = null;
                Write(Result(id, result));
            }
            finally {
                StopProgress(progress);
            }
        }

        private JToken Dispatch(string name, JObject arguments) {
            var tool = tools.FirstOrDefault(candidate => candidate.Name == name)
                ?? throw new AgentClientException("unknown_tool", "Unknown tool: " + name);
            return tool.Handle(arguments);
        }

        /// <summary>
        /// When a run failed on <c>DB.X</c> or <c>UI.X</c> that doesn't exist, look X up in the
        /// running Revit and put the answer in the hint: agents rarely act on "call
        /// lookup_revit_api", but they do act on "use DB.Architecture.Room".
        /// </summary>
        private JObject ResolveMissingApiName(JObject arguments, JObject run) {
            var error = run["error"] as JObject;
            var library = error == null ? null : PyRevitMcpRunResults.MissingLibraryName(error);
            if (library != null) {
                try {
                    var similar = PyRevitLibraryIndex.Similar(library.Value.Member, library.Value.Module);
                    if (similar.Count == 0 && library.Value.Module != null)
                        similar = PyRevitLibraryIndex.Similar(library.Value.Member);
                    error["hint"] = similar.Count > 0
                        ? $"'{library.Value.Member}' is not in {library.Value.Module ?? "that module"}. Similar: {string.Join("; ", similar)}. "
                            + "lookup_pyrevit_api(query=...) shows the full docstring."
                        : $"Nothing named like '{library.Value.Member}' in pyrevitlib or rpw; search with lookup_pyrevit_api(query='<what you need>').";
                }
                catch (Exception) {
                }
                return run;
            }

            var missing = error == null ? null : PyRevitMcpRunResults.MissingRevitApiName(error);
            if (missing == null)
                return run;

            try {
                var lookup = CallRevit(arguments, "lookup_api", new JObject { ["name"] = missing }) as JObject;
                var hint = PyRevitMcpRunResults.HintFromLookup(missing, lookup);
                if (hint != null)
                    error["hint"] = hint;
            }
            catch (Exception) {
            }
            return run;
        }

        private SemaphoreSlim GateFor(AgentInstance instance) {
            return revitGates.GetOrAdd(instance.Pipe ?? string.Empty, _ => new SemaphoreSlim(1, 1));
        }

        private JToken ListInstances() {
            var probes = PyRevitAgentClient.GetInstances()
                .Select(instance => Task.Run(() => DescribeInstance(instance)))
                .ToArray();
            Task.WaitAll(probes);
            return new JObject {
                ["instances"] = new JArray(probes.Select(probe => probe.Result)),
                ["default_selector"] = defaultRevit,
            };
        }

        private JObject DescribeInstance(AgentInstance instance) {
            var entry = instance.ToJson();
            var gate = GateFor(instance);
            if (!gate.Wait(0)) {
                entry["busy"] = true;
                return entry;
            }
            try {
                var pong = PyRevitAgentClient.Ping(instance, WithClient(new JObject()));
                entry["responding"] = true;
                if (pong?["session"] is JObject session)
                    entry["session"] = session;
            }
            catch (AgentClientException ex) when (ex.Code == "revit_busy" && PyRevitAgentClient.PipeExists(instance.Pipe)) {
                entry["busy"] = true;
            }
            catch (AgentClientException) {
                entry["responding"] = false;
            }
            finally {
                gate.Release();
            }
            return entry;
        }

        private JToken CallRevit(JObject arguments, string method, JObject parameters) {
            var requested = arguments["revit"]?.ToString();
            var instance = PyRevitAgentClient.Resolve(string.IsNullOrWhiteSpace(requested) ? defaultRevit : requested);
            var gate = GateFor(instance);
            var cancellation = callCancellation.Value;
            try {
                gate.Wait(cancellation);
            }
            catch (OperationCanceledException) {
                throw new AgentClientException(
                    "cancelled",
                    "The call was cancelled while it waited for an earlier call to the same Revit. "
                    + "The request was not sent, so it is safe to send again.",
                    AgentOutcome.NotSent);
            }
            try {
                return PyRevitAgentClient.Call(instance, method, WithClient(parameters), cancellation);
            }
            finally {
                gate.Release();
            }
        }

        private JObject WithClient(JObject parameters) {
            var name = clientName;
            if (!string.IsNullOrWhiteSpace(name))
                parameters["client"] = name;
            return parameters;
        }

        private JToken RunScript(JObject arguments, string mode) {
            return ResolveMissingApiName(arguments, PyRevitMcpRunResults.Compact(
                (JObject)CallRevit(arguments, "run", RunParameters(arguments, mode))));
        }

        private JToken LookupRevitApi(JObject arguments) {
            var name = arguments.Value<string>("name");
            if (string.IsNullOrWhiteSpace(name))
                name = arguments.Value<string>("query");
            if (string.IsNullOrWhiteSpace(name))
                throw new AgentClientException("invalid_params", "'name' (or its alias 'query') is required.");
            return CallRevit(arguments, "lookup_api", new JObject { ["name"] = name });
        }

        private JToken NavigateRevitLink(JObject arguments) {
            var link = arguments["link"] as JObject
                ?? throw new AgentClientException("invalid_params", "'link' must be an element reference returned by inspect_elements.");
            if (link.Value<string>("destination") != "element" || link["ids"] is not JArray ids || ids.Count == 0)
                throw new AgentClientException("invalid_params", "Only non-empty element links are supported.");
            var expected = link["document"] as JObject
                ?? throw new AgentClientException("invalid_params", "The link has no document reference.");
            var parameters = WithTitle(arguments, new JObject {
                ["action"] = arguments.Value<string>("action") ?? "select",
                ["ids"] = ids,
                ["zoom"] = arguments.Value<bool?>("zoom") ?? true,
                ["link_document"] = expected,
            });
            if (expected["key"] is JValue key && key.Type == JTokenType.String)
                parameters["document"] = key;
            return CallRevit(arguments, "show", parameters);
        }

        private static JObject RunParameters(JObject arguments, string mode) {
            var script = arguments.Value<string>("script");
            if (string.IsNullOrWhiteSpace(script))
                throw new AgentClientException("invalid_params", "'script' is required.");

            var parameters = WithDocument(arguments, WithTitle(arguments, new JObject {
                ["script"] = script,
                ["mode"] = mode,
                ["inputs"] = arguments["inputs"] ?? new JObject(),
            }));
            if (arguments["engine"] != null)
                parameters["engine"] = arguments["engine"];
            if (arguments["workspace"] != null)
                parameters["workspace"] = arguments["workspace"];
            if (arguments["timeout_s"] != null)
                parameters["timeout_s"] = arguments["timeout_s"];
            return parameters;
        }

        /// <remarks>
        /// An operation that needs a document runs in the one <c>document</c> names, after a
        /// <c>get_context</c> with <c>keep_changes</c> that relays <c>since_last_call</c> without
        /// clearing it, so the run's own response still reports every change. A refusal carries
        /// the summary the check received.
        /// </remarks>
        private JToken RunAutomation(JObject arguments) {
            var operation = PyRevitAutomationOperations.Resolve(
                arguments.Value<string>("id"), arguments["inputs"]);
            var reason = Reason(arguments);
            JToken sinceLastCall = null;
            string document = null;
            if (operation.Value<bool>("requires_document")) {
                document = DocumentKey(arguments)
                    ?? throw new AgentClientException("invalid_params",
                        $"'{operation.Value<string>("id")}' works in a document: pass 'document', a key from get_context.");
                var context = CallRevit(arguments, "get_context", new JObject { ["keep_changes"] = true }) as JObject;
                sinceLastCall = context?["since_last_call"];
            }
            var parameters = new JObject {
                ["script"] = operation.Value<string>("source"),
                ["mode"] = "query",
                ["title"] = operation.Value<string>("title"),
                ["inputs"] = operation["inputs"],
            };
            if (document != null)
                parameters["document"] = document;
            if (reason != null)
                parameters["reason"] = reason;
            if (arguments["engine"] != null)
                parameters["engine"] = arguments["engine"];
            if (arguments["timeout_s"] != null)
                parameters["timeout_s"] = arguments["timeout_s"];
            JObject run;
            try {
                run = (JObject)CallRevit(arguments, "run", parameters);
            }
            catch (AgentClientException ex) when (sinceLastCall != null) {
                throw ex.WithDetails(new JObject { ["since_last_call"] = sinceLastCall });
            }
            var result = PyRevitMcpRunResults.Compact(run);
            if (sinceLastCall != null && result["since_last_call"] == null)
                result["since_last_call"] = sinceLastCall;
            return result;
        }

        /// <summary>
        /// Adds the agent's <c>title</c> and <c>reason</c> to a request for Revit, where the agent
        /// panel shows them to the user.
        /// </summary>
        /// <exception cref="AgentClientException">
        /// <c>invalid_params</c> when the title is missing, blank or too long, or the reason is
        /// too long.
        /// </exception>
        /// <exception cref="InvalidCastException">
        /// A title or reason that isn't a string; the tool call reports it as <c>invalid_params</c>.
        /// </exception>
        private static JObject WithTitle(JObject arguments, JObject parameters) {
            var title = Text(arguments, "title");
            if (string.IsNullOrEmpty(title))
                throw new AgentClientException("invalid_params",
                    "'title' is required: say in a few words what this call is for. The user sees it in Revit's agent panel.");
            if (title.Length > MaxTitleLength)
                throw new AgentClientException("invalid_params", $"'title' must be at most {MaxTitleLength} characters.");
            parameters["title"] = title;
            var reason = Reason(arguments);
            if (reason != null)
                parameters["reason"] = reason;
            return parameters;
        }

        /// <summary>
        /// Adds the <c>document</c> the agent named to a model request, so the host runs it in that
        /// document and reads element ids there.
        /// </summary>
        /// <exception cref="AgentClientException">
        /// <c>invalid_params</c> when <c>document</c> is missing or not a string.
        /// </exception>
        private static JObject WithDocument(JObject arguments, JObject parameters) {
            parameters["document"] = DocumentKey(arguments)
                ?? throw new AgentClientException("invalid_params",
                    "'document' is required: the key of the document to work in, from get_context's open_documents.");
            return parameters;
        }

        /// <exception cref="AgentClientException"><c>invalid_params</c> when <c>document</c> isn't a string.</exception>
        private static string DocumentKey(JObject arguments) {
            var token = arguments["document"];
            if (token == null || token.Type == JTokenType.Null)
                return null;
            if (token.Type != JTokenType.String)
                throw new AgentClientException("invalid_params", "'document' must be a document key string, such as 'doc-1'.");
            var key = token.Value<string>().Trim();
            return key.Length == 0 ? null : key;
        }

        private static string Reason(JObject arguments) {
            var reason = Text(arguments, "reason");
            if (reason != null && reason.Length > MaxReasonLength)
                throw new AgentClientException("invalid_params", $"'reason' must be at most {MaxReasonLength} characters.");
            return string.IsNullOrEmpty(reason) ? null : reason;
        }

        private static string Text(JObject arguments, string name) {
            return arguments.Value<string>(name)?.Trim();
        }

        private static JToken GetRun(JObject arguments) {
            var runId = arguments.Value<string>("run_id");
            var runDir = PyRevitAgentClient.FindRunDir(runId)
                ?? throw new AgentClientException("run_not_found", "No recorded run with id " + runId);

            var responsePath = Path.Combine(runDir, "response.json");
            var run = File.Exists(responsePath) ? JObject.Parse(File.ReadAllText(responsePath)) : new JObject();
            run["script"] = ReadIfExists(Path.Combine(runDir, "script.py"));

            var resultPath = Path.Combine(runDir, "result.json");
            if (File.Exists(resultPath)) {
                var full = File.ReadAllText(resultPath);
                var offset = Math.Max(0, arguments.Value<int?>("offset") ?? 0);
                var length = Math.Min(MaxRunResultPage, Math.Max(1, arguments.Value<int?>("length") ?? MaxRunResultPage));
                var page = offset < full.Length ? full.Substring(offset, Math.Min(length, full.Length - offset)) : string.Empty;
                run["result_page"] = new JObject {
                    ["offset"] = offset,
                    ["length"] = page.Length,
                    ["total_length"] = full.Length,
                    ["text"] = page,
                };
            }
            return run;
        }

        private static string ReadIfExists(string path) {
            return File.Exists(path) ? File.ReadAllText(path) : null;
        }

        private static void StopProgress(Timer progress) {
            if (progress == null)
                return;
            using (var finished = new ManualResetEvent(false)) {
                progress.Dispose(finished);
                finished.WaitOne();
            }
        }

        private Timer StartProgress(JToken progressToken) {
            if (progressToken == null)
                return null;

            var ticks = 0;
            return new Timer(_ => {
                ticks++;
                Write(new JObject {
                    ["jsonrpc"] = "2.0",
                    ["method"] = "notifications/progress",
                    ["params"] = new JObject {
                        ["progressToken"] = progressToken,
                        ["progress"] = ticks,
                        ["message"] = "Waiting for Revit (a modify run waits for the user to approve it in Revit)",
                    },
                });
            }, null, ProgressInterval, ProgressInterval);
        }

        private void Write(JObject message) {
            var text = message.ToString(Formatting.None);
            lock (writeLock)
                output.WriteLine(text);
        }

        private static JObject Result(JToken id, JToken result) {
            return new JObject { ["jsonrpc"] = "2.0", ["id"] = id, ["result"] = result };
        }

        private static JObject Error(JToken id, int code, string message) {
            return new JObject {
                ["jsonrpc"] = "2.0",
                ["id"] = id,
                ["error"] = new JObject { ["code"] = code, ["message"] = message },
            };
        }

        /// <summary>
        /// Returns a capture as an MCP image block (what the model looks at) plus a short text
        /// block with the view and the saved file path; the base64 data is not repeated in text.
        /// </summary>
        private static JObject ImageResult(JObject captured) {
            var data = captured.Value<string>("image_base64");
            captured.Remove("image_base64");
            return new JObject {
                ["content"] = new JArray(
                    new JObject { ["type"] = "image", ["data"] = data, ["mimeType"] = "image/png" },
                    new JObject { ["type"] = "text", ["text"] = captured.ToString(Formatting.None) }),
                ["isError"] = false,
            };
        }

        private static JObject ToolResult(string text, bool isError) {
            return new JObject {
                ["content"] = new JArray(new JObject { ["type"] = "text", ["text"] = text }),
                ["isError"] = isError,
            };
        }

        private static JObject TitleProperty(string description = null) {
            return new JObject {
                ["type"] = "string",
                ["maxLength"] = MaxTitleLength,
                ["description"] = description ?? "What this call is for, in a few words. The user sees it in Revit's agent panel.",
            };
        }

        private static JObject ReasonProperty(string description = null) {
            return new JObject {
                ["type"] = "string",
                ["maxLength"] = MaxReasonLength,
                ["description"] = description ?? "Why you are doing this, when the title doesn't make it obvious. The user sees it in Revit's agent panel.",
            };
        }

        private static JObject DocumentProperty(string description = null) {
            return new JObject {
                ["type"] = "string",
                ["description"] = description
                    ?? "Key of the document to work in, from get_context (open_documents[].key). Element ids are read in this document.",
            };
        }

        private static JObject RevitProperty() {
            return new JObject {
                ["type"] = "string",
                ["description"] = "Target Revit: a year (e.g. \"2024\"), a process id, or the name of the pyRevit clone the session runs. Leave it out unless list_revit_instances shows more than one session.",
            };
        }

        private static JObject EngineProperty() {
            return new JObject {
                ["type"] = "string",
                ["enum"] = new JArray("ironpython", "cpython"),
                ["description"] = "Script engine. Defaults to get_context.scripting.default_engine; see scripting.engines for each engine's Python version and syntax limits.",
            };
        }

        private static JObject PointProperty(string description) {
            return new JObject {
                ["type"] = "array",
                ["items"] = new JObject { ["type"] = "number" },
                ["minItems"] = 3,
                ["maxItems"] = 3,
                ["description"] = description,
            };
        }

        private static JObject InputsProperty() {
            return new JObject {
                ["type"] = "object",
                ["description"] = "Values exposed to the script as the `inputs` dict.",
            };
        }

        private static JObject TimeoutProperty() {
            return new JObject {
                ["type"] = "number",
                ["minimum"] = 0.001,
                ["maximum"] = 3600,
                ["description"] = "Seconds the script may run before it is stopped and rolled back with error 'timeout' (default 300, max 3600). "
                    + "Stops Python code, not a single long Revit API call. Not enforced when get_context shows "
                    + "agent.reckless: true; then a script that never ends hangs Revit.",
            };
        }

        private static JObject WorkspaceProperty() {
            return new JObject {
                ["type"] = "string",
                ["description"] = "Absolute path of a folder with your own helper modules (plan data, functions). It is on sys.path for the run and its modules are re-imported fresh every run, so `import house_plan` sees your latest edits.",
            };
        }

        /// <summary>
        /// The MCP tools this server exposes, in the order <c>tools/list</c> reports them.
        /// </summary>
        /// <remarks>
        /// Invariant: each tool's schema and handler live in one entry, so a tool can't be
        /// listed without being callable or the other way round. Schemas are built on every
        /// <c>tools/list</c>, so <c>get_skill</c> always lists the skills on disk.
        /// </remarks>
        private List<McpTool> CreateTools() {
            return new List<McpTool> {
                new McpTool("list_skills", readOnly: true, new string[0],
                    () => ("List the available task skills with their source and content hash. User skills are disabled until the user explicitly enables them in pyRevit configuration.",
                        new JObject()),
                    _ => PyRevitAgentSkills.List()),

                new McpTool("get_skill", readOnly: true, new[] { "name" },
                    () => {
                        var skills = PyRevitAgentSkills.Load();
                        return ("Read a skill: task guidance for Revit scripting. Read revit-scripting before your first script, then the skill for your task. "
                            + "Use list_skills for source and hash metadata. Skills: " + string.Join("; ", skills.Select(PyRevitAgentSkills.Summary)),
                            new JObject {
                                ["name"] = new JObject {
                                    ["type"] = "string",
                                    ["enum"] = new JArray(skills.Select(skill => skill.Name)),
                                },
                                ["file"] = new JObject {
                                    ["type"] = "string",
                                    ["description"] = "Another markdown file in the skill folder, as listed at the end of the skill (default SKILL.md).",
                                },
                            });
                    },
                    arguments => new JValue(PyRevitAgentSkills.Read(arguments.Value<string>("name"), arguments.Value<string>("file")))),

                new McpTool("list_revit_instances", readOnly: true, new string[0],
                    () => ("List running Revit sessions that have the pyRevit agent host, with their version, process id and agent session state. "
                        + "'busy': true means that Revit is serving another call, from this session or another client, so it could not be pinged.",
                        new JObject()),
                    _ => ListInstances()),

                new McpTool("request_session", readOnly: true, new string[0],
                    () => ("Ask the user to start an agent session in Revit. Model tools answer session_inactive until the user starts one; "
                        + "only the user can, in Revit. Tell the user what you asked for and that you are waiting.",
                        new JObject {
                            ["reason"] = ReasonProperty("What you want to do in the model, shown to the user in Revit."),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "request_session", new JObject { ["reason"] = Reason(arguments) })),

                new McpTool("get_context", readOnly: true, new string[0],
                    () => ("Snapshot of the target Revit: versions, engines, agent policy and session, the open documents with the keys "
                        + "model tools take as 'document', the active document, view, selection and levels. Call this first.",
                        new JObject { ["revit"] = RevitProperty() }),
                    arguments => CallRevit(arguments, "get_context", new JObject())),

                new McpTool("inspect_elements", readOnly: true, new[] { "ids", "title", "document" },
                    () => ("Describe elements by id: class, category, name, type, level, location, bounding box and (by default) every parameter with display and raw values.",
                        new JObject {
                            ["ids"] = new JObject {
                                ["type"] = "array",
                                ["items"] = new JObject { ["type"] = "integer" },
                                ["description"] = "Element ids (at most 50).",
                            },
                            ["parameters"] = new JObject { ["type"] = "boolean", ["description"] = "Include parameters (default true)." },
                            ["document"] = DocumentProperty(),
                            ["title"] = TitleProperty(),
                            ["reason"] = ReasonProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "inspect_elements", WithDocument(arguments, WithTitle(arguments, new JObject {
                        ["ids"] = arguments["ids"],
                        ["parameters"] = arguments["parameters"] ?? true,
                    })))),

                new McpTool("lookup_pyrevit_api", readOnly: true, new[] { "query" },
                    () => ("Search pyrevitlib (pyrevit.revit: query, create, update, units, ui, Transaction) and rpw (rpw.db) before writing "
                        + "raw Revit API code. Pass a module ('pyrevit.revit.db.create') to list its functions, a function name ('find_type', "
                        + "'pyrevit.revit.db.create.create_gable_roof') for its signature and docstring, or words ('section box', 'room') to search. "
                        + "Works without Revit.",
                        new JObject {
                            ["query"] = new JObject { ["type"] = "string", ["description"] = "Module, function or class name, or search words." },
                        }),
                    arguments => PyRevitLibraryIndex.Lookup(arguments.Value<string>("query"))),

                new McpTool("list_automation", readOnly: true, new string[0],
                    () => ("List the reviewed pyRevit and rpw automation APIs by stable identifier. An entry with invocable true runs through run_automation, "
                        + "taking the inputs it lists (element = an element id). Results are paginated and work without Revit.",
                        new JObject {
                            ["offset"] = new JObject { ["type"] = "integer", ["minimum"] = 0, ["description"] = "Zero-based result offset." },
                            ["limit"] = new JObject { ["type"] = "integer", ["minimum"] = 1, ["maximum"] = 50, ["description"] = "Results to return, default 25." },
                        }),
                    arguments => PyRevitLibraryIndex.ListAutomation(
                        arguments.Value<int?>("offset") ?? 0,
                        arguments.Value<int?>("limit") ?? 25)),

                new McpTool("run_automation", readOnly: true, new[] { "id", "inputs" },
                    () => ("Run a reviewed read-only automation operation (invocable in list_automation) with the inputs it lists. "
                        + "Runs as a query, so model changes are rolled back. This does not accept Python source, module names or callable names.",
                        new JObject {
                            ["id"] = new JObject { ["type"] = "string", ["description"] = "Invocable automation identifier, such as pyrevit.units.parse-length." },
                            ["inputs"] = new JObject { ["type"] = "object", ["description"] = "Operation input object." },
                            ["engine"] = EngineProperty(),
                            ["timeout_s"] = TimeoutProperty(),
                            ["document"] = DocumentProperty(
                                "Key of the document to work in, from get_context (open_documents[].key). Required when the operation needs a document."),
                            ["reason"] = ReasonProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    RunAutomation),

                new McpTool("lookup_revit_api", readOnly: true, new string[0],
                    () => ("Look up a Revit API type or member in the running Revit version, e.g. 'Wall', 'Autodesk.Revit.DB.Wall', 'Wall.Create', 'ElementId.Value'. Returns signatures, enum values and obsolete markers. "
                        + "Pass it as name, or as query like lookup_pyrevit_api.",
                        new JObject {
                            ["name"] = new JObject { ["type"] = "string", ["description"] = "Type name or Type.Member." },
                            ["query"] = new JObject { ["type"] = "string", ["description"] = "Alias for name." },
                            ["revit"] = RevitProperty(),
                        }),
                    LookupRevitApi),

                new McpTool("show_elements", readOnly: false, destructive: false, new[] { "title", "document" },
                    () => ("Show elements to the user in the active view, without an approval prompt and without changing model elements: "
                        + "select them, temporarily isolate or hide them (Revit's temporary hide/isolate), or reset that mode. "
                        + "Target element ids and/or whole categories (resolved to the elements visible in the active view). "
                        + "When zoom fails, the response has zoomed=false and a zoom_failed error with Revit's message.",
                        new JObject {
                            ["action"] = new JObject {
                                ["type"] = "string",
                                ["enum"] = new JArray("select", "isolate", "hide", "reset"),
                                ["description"] = "select (default), isolate, hide, or reset (end temporary hide/isolate in the active view).",
                            },
                            ["ids"] = new JObject {
                                ["type"] = "array",
                                ["items"] = new JObject { ["type"] = "integer" },
                                ["description"] = "Element ids.",
                            },
                            ["categories"] = new JObject {
                                ["type"] = "array",
                                ["items"] = new JObject { ["type"] = "string" },
                                ["description"] = "BuiltInCategory names such as OST_Windows or OST_Doors.",
                            },
                            ["zoom"] = new JObject { ["type"] = "boolean", ["description"] = "Also zoom the view to the elements." },
                            ["document"] = DocumentProperty("Key of the document whose elements to show, from get_context. It must be the active document."),
                            ["title"] = TitleProperty(),
                            ["reason"] = ReasonProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "show", WithDocument(arguments, WithTitle(arguments, new JObject {
                        ["action"] = arguments["action"] ?? "select",
                        ["ids"] = arguments["ids"],
                        ["categories"] = arguments["categories"],
                        ["zoom"] = arguments["zoom"] ?? false,
                    })))),

                new McpTool("navigate_revit_link", readOnly: false, destructive: false, new[] { "link", "title" },
                    () => ("Navigate an element link returned by inspect_elements. The active Revit document must still match the link; stale links return an actionable error. This selects or temporarily presents elements only.",
                        new JObject {
                            ["link"] = new JObject { ["type"] = "object", ["description"] = "An element link from inspect_elements." },
                            ["action"] = new JObject { ["type"] = "string", ["enum"] = new JArray("select", "isolate", "hide") },
                            ["zoom"] = new JObject { ["type"] = "boolean", ["description"] = "Zoom to the linked elements (default true)." },
                            ["title"] = TitleProperty(),
                            ["reason"] = ReasonProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    NavigateRevitLink),

                new McpTool("capture_view", readOnly: false, destructive: false, new[] { "title", "document" },
                    () => ("Take a PNG of a Revit view to check your work visually. mode 'export' (default) renders the view "
                        + "through Revit and works for any view by name or id; a name shared by several views fails with "
                        + "view_ambiguous listing their ids. mode 'viewport' renders an open view through Revit "
                        + "cropped to the region its window shows now: the user's zoom, pan and temporary isolate, without "
                        + "selection highlight, and unaffected by other windows. mode 'screen' captures the active view's window "
                        + "exactly as the user sees it, including selection and temporary isolate; it fails with view_not_active "
                        + "for any other view and with view_obscured when another application covers the view. view '3d' renders a temporary "
                        + "3D view of model categories only, framed by a section box around the whole model or around 'elements', "
                        + "seen from 'direction' (never saved); give 'eye' and 'target' for a perspective camera instead, "
                        + "or 'section' for a temporary section, elevation or plan cut at a height. 'detail_level' and "
                        + "'display_style' override the view's own for this capture only, also for named views. "
                        + "The image is also saved under %APPDATA%\\pyRevit\\agent\\captures for the user.",
                        new JObject {
                            ["view"] = new JObject {
                                ["type"] = "string",
                                ["description"] = "'active' (default), '3d', a view name, or a view id.",
                            },
                            ["mode"] = new JObject {
                                ["type"] = "string",
                                ["enum"] = new JArray("export", "viewport", "screen"),
                                ["description"] = "export (default), viewport or screen.",
                            },
                            ["width"] = new JObject {
                                ["type"] = "integer",
                                ["description"] = "Image width in pixels, 320-2400 (default 1280). Larger images cost more tokens.",
                            },
                            ["direction"] = new JObject {
                                ["type"] = "string",
                                ["enum"] = new JArray("southeast", "southwest", "northeast", "northwest", "south", "north", "east", "west", "top"),
                                ["description"] = "view '3d' only: where the viewer stands (default southeast, looking down at 35 degrees).",
                            },
                            ["elements"] = new JObject {
                                ["type"] = "array",
                                ["items"] = new JObject { ["type"] = "integer" },
                                ["description"] = "view '3d' only: element ids to frame; default is the whole model. Ignored with 'eye' and 'target'.",
                            },
                            ["detail_level"] = new JObject {
                                ["type"] = "string",
                                ["enum"] = new JArray("coarse", "medium", "fine"),
                                ["description"] = "Detail level for this capture only (view '3d' default: medium; named views keep their own). Not for mode 'screen'.",
                            },
                            ["display_style"] = new JObject {
                                ["type"] = "string",
                                ["enum"] = new JArray("wireframe", "hidden_line", "shaded", "shaded_edges"),
                                ["description"] = "Display style for this capture only (view '3d' default: shaded_edges; named views keep their own). Not for mode 'screen'.",
                            },
                            ["eye"] = PointProperty("view '3d' only: camera position in model coordinates, feet. Needs 'target'. Renders a perspective view with no section box."),
                            ["target"] = PointProperty("view '3d' only: the point the camera looks at, feet. Needs 'eye'."),
                            ["section"] = new JObject {
                                ["type"] = "object",
                                ["description"] = "view '3d' only: a temporary section instead of the 3D views, framed on 'elements' or the whole model. "
                                    + "'normal' is the direction the view looks along: horizontal gives a section or elevation, [0,0,-1] a plan cut at origin z.",
                                ["properties"] = new JObject {
                                    ["origin"] = PointProperty("A point on the cutting plane, feet."),
                                    ["normal"] = PointProperty("Look direction: horizontal, or [0,0,-1] for a plan."),
                                    ["depth"] = new JObject {
                                        ["type"] = "number",
                                        ["description"] = "How far the view sees past the plane, feet. Default reaches the far side of the framed elements.",
                                    },
                                },
                                ["required"] = new JArray("origin", "normal"),
                            },
                            ["document"] = DocumentProperty(
                                "Key of the document to capture, from get_context. It must be the active document: Revit switches to any document it renders."),
                            ["title"] = TitleProperty(),
                            ["reason"] = ReasonProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "capture", WithDocument(arguments, WithTitle(arguments, new JObject {
                        ["view"] = arguments["view"],
                        ["mode"] = arguments["mode"],
                        ["width"] = arguments["width"],
                        ["direction"] = arguments["direction"],
                        ["elements"] = arguments["elements"],
                        ["detail_level"] = arguments["detail_level"],
                        ["display_style"] = arguments["display_style"],
                        ["eye"] = arguments["eye"],
                        ["target"] = arguments["target"],
                        ["section"] = arguments["section"],
                    })))),

                new McpTool("run_query", readOnly: false, new[] { "script", "title", "document" },
                    () => ("Run a read-only Python script in Revit and return `result`, printed output, and any error with traceback. Model changes made during the run are rolled back and must not be made. The script itself runs with full access to Revit and the machine; the guard only covers what happens while it runs.",
                        new JObject {
                            ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Assign `result` to return data." },
                            ["document"] = DocumentProperty("Key of the document to run in, from get_context; the script's `doc`. `uidoc` is set only when it is the active document."),
                            ["title"] = TitleProperty(),
                            ["reason"] = ReasonProperty(),
                            ["inputs"] = InputsProperty(),
                            ["engine"] = EngineProperty(),
                            ["timeout_s"] = TimeoutProperty(),
                            ["workspace"] = WorkspaceProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => RunScript(arguments, "query")),

                new McpTool("run_modify", readOnly: false, new[] { "script", "title", "document" },
                    () => ("Run a Python script that changes the model. With dry_run=true the change set is returned and everything is rolled back. Otherwise, under agent policy 'ask', Revit shows the user an approval prompt with the changed elements isolated; under policy 'auto' the change is committed directly. Kept changes become one undo entry named 'Agent: <title>'. Status 'rejected' means the user discarded the changes.",
                        new JObject {
                            ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Open transactions with DB.Transaction; assign `result` to return data." },
                            ["document"] = DocumentProperty("Key of the document to change, from get_context; the script's `doc`. The run may also change the session's other documents; changing a document outside the session fails it."),
                            ["title"] = TitleProperty("What the change does, in a few words. The user sees it in Revit's agent panel and approval prompt, and it becomes the undo name."),
                            ["reason"] = ReasonProperty(),
                            ["dry_run"] = new JObject { ["type"] = "boolean", ["description"] = "Preview only: run, report the change set, roll back." },
                            ["inputs"] = InputsProperty(),
                            ["engine"] = EngineProperty(),
                            ["timeout_s"] = TimeoutProperty(),
                            ["workspace"] = WorkspaceProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => RunScript(arguments, (arguments.Value<bool?>("dry_run") ?? false) ? "dry_run" : "modify")),

                new McpTool("get_run", readOnly: true, new[] { "run_id" },
                    () => ("Read a recorded run by run_id, or by the request_id of a request that got no answer: response, script, and pages of a result too large to return inline (use offset/length).",
                        new JObject {
                            ["run_id"] = new JObject { ["type"] = "string" },
                            ["offset"] = new JObject { ["type"] = "integer", ["description"] = "Character offset into a truncated result." },
                            ["length"] = new JObject { ["type"] = "integer", ["description"] = "Characters to return (max 204800)." },
                        }),
                    GetRun),
            };
        }

        private sealed class McpTool {
            private readonly bool readOnly;
            private readonly bool destructive;
            private readonly string[] required;
            private readonly Func<(string Description, JObject Properties)> schema;
            private readonly Func<JObject, JToken> handler;

            public McpTool(
                string name, bool readOnly, string[] required,
                Func<(string Description, JObject Properties)> schema, Func<JObject, JToken> handler)
                : this(name, readOnly, !readOnly, required, schema, handler) {
            }

            public McpTool(
                string name, bool readOnly, bool destructive, string[] required,
                Func<(string Description, JObject Properties)> schema, Func<JObject, JToken> handler) {
                Name = name;
                this.readOnly = readOnly;
                this.destructive = destructive;
                this.required = required;
                this.schema = schema;
                this.handler = handler;
            }

            public string Name { get; }

            public JToken Handle(JObject arguments) {
                return handler(arguments);
            }

            public JObject Describe() {
                var (description, properties) = schema();
                return new JObject {
                    ["name"] = Name,
                    ["description"] = description,
                    ["inputSchema"] = new JObject {
                        ["type"] = "object",
                        ["properties"] = properties,
                        ["required"] = new JArray(required),
                    },
                    ["annotations"] = new JObject {
                        ["readOnlyHint"] = readOnly,
                        ["destructiveHint"] = destructive,
                        ["openWorldHint"] = false,
                    },
                };
            }
        }
    }
}
