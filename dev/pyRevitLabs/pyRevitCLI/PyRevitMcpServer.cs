using System;
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
    /// </remarks>
    internal sealed class PyRevitMcpServer {
        private const string LatestProtocolVersion = "2025-06-18";
        private static readonly string[] SupportedProtocolVersions = {
            "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05",
        };
        private static readonly TimeSpan ProgressInterval = TimeSpan.FromSeconds(10);
        private const int MaxRunResultPage = 200 * 1024;

        private readonly string defaultRevit;
        private readonly object writeLock = new object();
        private readonly SemaphoreSlim revitGate = new SemaphoreSlim(1, 1);
        private readonly List<McpTool> tools;
        private TextWriter output;

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
                    message = JObject.Parse(line);
                }
                catch (JsonException) {
                    Write(Error(null, -32700, "Parse error"));
                    continue;
                }

                var method = message.Value<string>("method");
                var id = message["id"];
                if (method == null || id == null)
                    continue;

                var parameters = message["params"] as JObject ?? new JObject();
                switch (method) {
                    case "initialize":
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
                        inFlight.Add(Task.Run(() => CallTool(id, parameters)));
                        break;
                    default:
                        Write(Error(id, -32601, "Method not found: " + method));
                        break;
                }
            }

            Task.WaitAll(inFlight.ToArray());
        }

        private static JObject Initialize(JObject parameters) {
            var requested = parameters.Value<string>("protocolVersion");
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

        private void CallTool(JToken id, JObject parameters) {
            var name = parameters.Value<string>("name");
            var arguments = parameters["arguments"] as JObject ?? new JObject();
            var progressToken = parameters["_meta"]?["progressToken"];

            var progress = StartProgress(progressToken);
            try {
                JObject result;
                try {
                    var payload = Dispatch(name, arguments);
                    var isError = payload is JObject run && run.Value<string>("status") == "error";
                    result = payload is JObject captured && captured["image_base64"] != null
                        ? ImageResult(captured)
                        : ToolResult(payload.Type == JTokenType.String ? payload.ToString() : payload.ToString(Formatting.None), isError);
                }
                catch (AgentClientException ex) {
                    result = ToolResult(new JObject { ["error"] = ex.Code, ["message"] = ex.Message }.ToString(Formatting.None), true);
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
                catch (AgentClientException) {
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
            catch (AgentClientException) {
            }
            return run;
        }

        private JToken ListInstances() {
            var instances = new JArray();
            foreach (var instance in PyRevitAgentClient.GetInstances()) {
                var entry = instance.ToJson();
                revitGate.Wait();
                try {
                    PyRevitAgentClient.Call(instance, "ping");
                    entry["responding"] = true;
                }
                catch (AgentClientException) {
                    entry["responding"] = false;
                }
                finally {
                    revitGate.Release();
                }
                instances.Add(entry);
            }
            return new JObject { ["instances"] = instances, ["default_selector"] = defaultRevit };
        }

        private JToken CallRevit(JObject arguments, string method, JObject parameters) {
            var selector = arguments["revit"]?.ToString() ?? defaultRevit;
            var instance = PyRevitAgentClient.Resolve(selector);
            revitGate.Wait();
            try {
                return PyRevitAgentClient.Call(instance, method, parameters);
            }
            finally {
                revitGate.Release();
            }
        }

        private JToken RunScript(JObject arguments, string mode) {
            return ResolveMissingApiName(arguments, PyRevitMcpRunResults.Compact(
                (JObject)CallRevit(arguments, "run", RunParameters(arguments, mode))));
        }

        private JToken NavigateRevitLink(JObject arguments) {
            var link = arguments["link"] as JObject
                ?? throw new AgentClientException("invalid_params", "'link' must be an element reference returned by inspect_elements.");
            if (link.Value<string>("destination") != "element" || link["ids"] is not JArray ids || ids.Count == 0)
                throw new AgentClientException("invalid_params", "Only non-empty element links are supported.");
            var expected = link["document"] as JObject
                ?? throw new AgentClientException("invalid_params", "The link has no document reference.");
            var context = CallRevit(arguments, "get_context", new JObject()) as JObject;
            var active = context?["document"] as JObject;
            if (active == null || !SameDocument(active, expected))
                throw new AgentClientException("stale_link", "The link belongs to a different or closed document. Activate its document, then inspect the elements again.");
            return CallRevit(arguments, "show", new JObject {
                ["action"] = arguments.Value<string>("action") ?? "select",
                ["ids"] = ids,
                ["zoom"] = arguments.Value<bool?>("zoom") ?? true,
            });
        }

        private static bool SameDocument(JObject active, JObject expected) {
            var expectedPath = expected.Value<string>("path");
            if (!string.IsNullOrEmpty(expectedPath))
                return string.Equals(active.Value<string>("path"), expectedPath, StringComparison.OrdinalIgnoreCase);
            return string.Equals(active.Value<string>("title"), expected.Value<string>("title"), StringComparison.Ordinal);
        }

        private static JObject RunParameters(JObject arguments, string mode) {
            var script = arguments.Value<string>("script");
            if (string.IsNullOrWhiteSpace(script))
                throw new AgentClientException("invalid_params", "'script' is required.");

            var parameters = new JObject {
                ["script"] = script,
                ["mode"] = mode,
                ["title"] = arguments.Value<string>("title") ?? (mode == "query" ? "Agent query" : "Agent change"),
                ["inputs"] = arguments["inputs"] ?? new JObject(),
            };
            if (arguments["engine"] != null)
                parameters["engine"] = arguments["engine"];
            if (arguments["workspace"] != null)
                parameters["workspace"] = arguments["workspace"];
            if (arguments["timeout_s"] != null)
                parameters["timeout_s"] = arguments["timeout_s"];
            return parameters;
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

        private static JObject RevitProperty() {
            return new JObject {
                ["type"] = "string",
                ["description"] = "Target Revit: a year (e.g. \"2024\") or a process id. Leave it out unless list_revit_instances shows more than one session.",
            };
        }

        private static JObject EngineProperty() {
            return new JObject {
                ["type"] = "string",
                ["enum"] = new JArray("ironpython", "cpython"),
                ["description"] = "Script engine. Defaults to get_context.scripting.default_engine; see scripting.engines for each engine's Python version and syntax limits.",
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
                ["description"] = "Seconds the script may run before it is stopped and rolled back with error 'timeout' (default 300, max 3600). "
                    + "Stops Python code, not a single long Revit API call.",
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
                            + "Use list_skills for source and hash metadata. Skills: " + string.Join(", ", skills.Select(skill => skill.Name)),
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
                    () => ("List running Revit sessions that have the pyRevit agent host, with their version and process id.",
                        new JObject()),
                    _ => ListInstances()),

                new McpTool("get_context", readOnly: true, new string[0],
                    () => ("Snapshot of the target Revit: versions, engines, agent policy, open document, active view, selection and levels. Call this first.",
                        new JObject { ["revit"] = RevitProperty() }),
                    arguments => CallRevit(arguments, "get_context", new JObject())),

                new McpTool("inspect_elements", readOnly: true, new[] { "ids" },
                    () => ("Describe elements by id: class, category, name, type, level, location, bounding box and (by default) every parameter with display and raw values.",
                        new JObject {
                            ["ids"] = new JObject {
                                ["type"] = "array",
                                ["items"] = new JObject { ["type"] = "integer" },
                                ["description"] = "Element ids (at most 50).",
                            },
                            ["parameters"] = new JObject { ["type"] = "boolean", ["description"] = "Include parameters (default true)." },
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "inspect_elements", new JObject {
                        ["ids"] = arguments["ids"],
                        ["parameters"] = arguments["parameters"] ?? true,
                    })),

                new McpTool("lookup_pyrevit_api", readOnly: true, new[] { "query" },
                    () => ("Search pyrevitlib (pyrevit.revit: query, create, update, units, ui, Transaction) and rpw (rpw.db) before writing "
                        + "raw Revit API code. Pass a module ('pyrevit.revit.db.create') to list its functions, a function name ('find_type', "
                        + "'pyrevit.revit.db.create.create_gable_roof') for its signature and docstring, or words ('section box', 'room') to search. "
                        + "Works without Revit.",
                        new JObject {
                            ["query"] = new JObject { ["type"] = "string", ["description"] = "Module, function or class name, or search words." },
                        }),
                    arguments => PyRevitLibraryIndex.Lookup(arguments.Value<string>("query"))),

                new McpTool("lookup_revit_api", readOnly: true, new[] { "name" },
                    () => ("Look up a Revit API type or member in the running Revit version, e.g. 'Wall', 'Autodesk.Revit.DB.Wall', 'Wall.Create', 'ElementId.Value'. Returns signatures, enum values and obsolete markers.",
                        new JObject {
                            ["name"] = new JObject { ["type"] = "string", ["description"] = "Type name or Type.Member." },
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "lookup_api", new JObject { ["name"] = arguments["name"] })),

                new McpTool("show_elements", readOnly: true, new string[0],
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
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "show", new JObject {
                        ["action"] = arguments["action"] ?? "select",
                        ["ids"] = arguments["ids"],
                        ["categories"] = arguments["categories"],
                        ["zoom"] = arguments["zoom"] ?? false,
                    })),

                new McpTool("navigate_revit_link", readOnly: true, new[] { "link" },
                    () => ("Navigate an element link returned by inspect_elements. The active Revit document must still match the link; stale links return an actionable error. This selects or temporarily presents elements only.",
                        new JObject {
                            ["link"] = new JObject { ["type"] = "object", ["description"] = "An element link from inspect_elements." },
                            ["action"] = new JObject { ["type"] = "string", ["enum"] = new JArray("select", "isolate", "hide") },
                            ["zoom"] = new JObject { ["type"] = "boolean", ["description"] = "Zoom to the linked elements (default true)." },
                            ["revit"] = RevitProperty(),
                        }),
                    NavigateRevitLink),

                new McpTool("capture_view", readOnly: true, new string[0],
                    () => ("Take a PNG of a Revit view to check your work visually. mode 'export' (default) renders the view "
                        + "through Revit and works for any view by name or id. mode 'viewport' renders an open view through Revit "
                        + "cropped to the region its window shows now: the user's zoom, pan and temporary isolate, without "
                        + "selection highlight, and unaffected by other windows. mode 'screen' captures the active view's window "
                        + "exactly as the user sees it, including selection and temporary isolate; it fails with view_obscured "
                        + "when another application covers the view. view '3d' renders a temporary "
                        + "3D view of model categories only, framed by a section box around the whole model or around 'elements', "
                        + "seen from 'direction' (never saved). The image is also saved under "
                        + "%APPDATA%\\pyRevit\\agent\\captures for the user.",
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
                                ["description"] = "view '3d' only: element ids to frame; default is the whole model.",
                            },
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => CallRevit(arguments, "capture", new JObject {
                        ["view"] = arguments["view"],
                        ["mode"] = arguments["mode"],
                        ["width"] = arguments["width"],
                        ["direction"] = arguments["direction"],
                        ["elements"] = arguments["elements"],
                    })),

                new McpTool("run_query", readOnly: false, new[] { "script" },
                    () => ("Run a read-only Python script in Revit and return `result`, printed output, and any error with traceback. Model changes made during the run are rolled back and must not be made. The script itself runs with full access to Revit and the machine; the guard only covers what happens while it runs.",
                        new JObject {
                            ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Assign `result` to return data." },
                            ["title"] = new JObject { ["type"] = "string", ["description"] = "Short label for the run record." },
                            ["inputs"] = InputsProperty(),
                            ["engine"] = EngineProperty(),
                            ["timeout_s"] = TimeoutProperty(),
                            ["workspace"] = WorkspaceProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => RunScript(arguments, "query")),

                new McpTool("run_modify", readOnly: false, new[] { "script", "title" },
                    () => ("Run a Python script that changes the model. With dry_run=true the change set is returned and everything is rolled back. Otherwise, under agent policy 'ask', Revit shows the user an approval prompt with the changed elements isolated; under policy 'auto' the change is committed directly. Kept changes become one undo entry named 'Agent: <title>'. Status 'rejected' means the user discarded the changes.",
                        new JObject {
                            ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Open transactions with DB.Transaction; assign `result` to return data." },
                            ["title"] = new JObject { ["type"] = "string", ["description"] = "What the change does; shown to the user and used as the undo name." },
                            ["dry_run"] = new JObject { ["type"] = "boolean", ["description"] = "Preview only: run, report the change set, roll back." },
                            ["inputs"] = InputsProperty(),
                            ["engine"] = EngineProperty(),
                            ["timeout_s"] = TimeoutProperty(),
                            ["workspace"] = WorkspaceProperty(),
                            ["revit"] = RevitProperty(),
                        }),
                    arguments => RunScript(arguments, (arguments.Value<bool?>("dry_run") ?? false) ? "dry_run" : "modify")),

                new McpTool("get_run", readOnly: true, new[] { "run_id" },
                    () => ("Read a recorded run by run_id: response, script, and pages of a result too large to return inline (use offset/length).",
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
            private readonly string[] required;
            private readonly Func<(string Description, JObject Properties)> schema;
            private readonly Func<JObject, JToken> handler;

            public McpTool(
                string name, bool readOnly, string[] required,
                Func<(string Description, JObject Properties)> schema, Func<JObject, JToken> handler) {
                Name = name;
                this.readOnly = readOnly;
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
                        ["destructiveHint"] = !readOnly,
                        ["openWorldHint"] = false,
                    },
                };
            }
        }
    }
}
