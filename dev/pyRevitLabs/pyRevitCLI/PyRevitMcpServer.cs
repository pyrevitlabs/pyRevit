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
        private TextWriter output;

        private PyRevitMcpServer(string defaultRevit) {
            this.defaultRevit = defaultRevit;
        }

        public static void Serve(string defaultRevit) {
            new PyRevitMcpServer(defaultRevit).Run();
        }

        private void Run() {
            LogManager.Configuration = new LoggingConfiguration();
            var utf8 = new UTF8Encoding(false);
            var input = new StreamReader(System.Console.OpenStandardInput(), utf8);
            output = new StreamWriter(System.Console.OpenStandardOutput(), utf8) { AutoFlush = true, NewLine = "\n" };

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
                        Write(Result(id, new JObject { ["tools"] = ToolDefinitions() }));
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

        // tools ============================================================================================
        private void CallTool(JToken id, JObject parameters) {
            var name = parameters.Value<string>("name");
            var arguments = parameters["arguments"] as JObject ?? new JObject();
            var progressToken = parameters["_meta"]?["progressToken"];

            using (StartProgress(progressToken)) {
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
                Write(Result(id, result));
            }
        }

        private JToken Dispatch(string name, JObject arguments) {
            switch (name) {
                case "get_skill":
                    return new JValue(PyRevitAgentSkills.Read(arguments.Value<string>("name"), arguments.Value<string>("file")));
                case "list_revit_instances":
                    return ListInstances();
                case "get_context":
                    return CallRevit(arguments, "get_context", new JObject());
                case "inspect_elements":
                    return CallRevit(arguments, "inspect_elements", new JObject {
                        ["ids"] = arguments["ids"],
                        ["parameters"] = arguments["parameters"] ?? true,
                    });
                case "lookup_pyrevit_api":
                    return PyRevitLibraryIndex.Lookup(arguments.Value<string>("query"));
                case "lookup_revit_api":
                    return CallRevit(arguments, "lookup_api", new JObject { ["name"] = arguments["name"] });
                case "show_elements":
                    return CallRevit(arguments, "show", new JObject {
                        ["action"] = arguments["action"] ?? "select",
                        ["ids"] = arguments["ids"],
                        ["categories"] = arguments["categories"],
                        ["zoom"] = arguments["zoom"] ?? false,
                    });
                case "capture_view":
                    return CallRevit(arguments, "capture", new JObject {
                        ["view"] = arguments["view"],
                        ["mode"] = arguments["mode"],
                        ["width"] = arguments["width"],
                        ["direction"] = arguments["direction"],
                        ["elements"] = arguments["elements"],
                    });
                case "run_query":
                    return ResolveMissingApiName(arguments, PyRevitMcpRunResults.Compact(
                        (JObject)CallRevit(arguments, "run", RunParameters(arguments, "query"))));
                case "run_modify":
                    var dryRun = arguments.Value<bool?>("dry_run") ?? false;
                    return ResolveMissingApiName(arguments, PyRevitMcpRunResults.Compact(
                        (JObject)CallRevit(arguments, "run", RunParameters(arguments, dryRun ? "dry_run" : "modify"))));
                case "get_run":
                    return GetRun(arguments);
                default:
                    throw new AgentClientException("unknown_tool", "Unknown tool: " + name);
            }
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

        // progress =========================================================================================
        private IDisposable StartProgress(JToken progressToken) {
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

        // protocol helpers =================================================================================
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

        // tool catalog =====================================================================================
        private static JArray ToolDefinitions() {
            var revitProperty = new JObject {
                ["type"] = "string",
                ["description"] = "Target Revit: a year (e.g. \"2024\") or a process id. Leave it out unless list_revit_instances shows more than one session.",
            };
            var engineProperty = new JObject {
                ["type"] = "string",
                ["enum"] = new JArray("ironpython", "cpython"),
                ["description"] = "Script engine. Defaults to get_context.scripting.default_engine; see scripting.engines for each engine's Python version and syntax limits.",
            };
            var inputsProperty = new JObject {
                ["type"] = "object",
                ["description"] = "Values exposed to the script as the `inputs` dict.",
            };

            var skills = PyRevitAgentSkills.Load();
            return new JArray(
                Tool("get_skill",
                    "Read a skill: task guidance for Revit scripting. Read revit-scripting before your first script, then the skill for your task. "
                    + "Skills: " + string.Join("; ", skills.Select(skill => skill.Name + " - " + skill.Description)),
                    new JObject {
                        ["name"] = new JObject {
                            ["type"] = "string",
                            ["enum"] = new JArray(skills.Select(skill => skill.Name)),
                        },
                        ["file"] = new JObject {
                            ["type"] = "string",
                            ["description"] = "Another markdown file in the skill folder, as listed at the end of the skill (default SKILL.md).",
                        },
                    }, new[] { "name" }, readOnly: true),

                Tool("list_revit_instances",
                    "List running Revit sessions that have the pyRevit agent host, with their version and process id.",
                    new JObject(), new string[0], readOnly: true),

                Tool("get_context",
                    "Snapshot of the target Revit: versions, engines, agent policy, open document, active view, selection and levels. Call this first.",
                    new JObject { ["revit"] = revitProperty }, new string[0], readOnly: true),

                Tool("inspect_elements",
                    "Describe elements by id: class, category, name, type, level, location, bounding box and (by default) every parameter with display and raw values.",
                    new JObject {
                        ["ids"] = new JObject {
                            ["type"] = "array",
                            ["items"] = new JObject { ["type"] = "integer" },
                            ["description"] = "Element ids (at most 50).",
                        },
                        ["parameters"] = new JObject { ["type"] = "boolean", ["description"] = "Include parameters (default true)." },
                        ["revit"] = revitProperty,
                    }, new[] { "ids" }, readOnly: true),

                Tool("lookup_pyrevit_api",
                    "Search pyrevitlib (pyrevit.revit: query, create, update, units, ui, Transaction) and rpw (rpw.db) before writing "
                    + "raw Revit API code. Pass a module ('pyrevit.revit.db.create') to list its functions, a function name ('find_type', "
                    + "'pyrevit.revit.db.create.create_gable_roof') for its signature and docstring, or words ('section box', 'room') to search. "
                    + "Works without Revit.",
                    new JObject {
                        ["query"] = new JObject { ["type"] = "string", ["description"] = "Module, function or class name, or search words." },
                    }, new[] { "query" }, readOnly: true),

                Tool("lookup_revit_api",
                    "Look up a Revit API type or member in the running Revit version, e.g. 'Wall', 'Autodesk.Revit.DB.Wall', 'Wall.Create', 'ElementId.Value'. Returns signatures, enum values and obsolete markers.",
                    new JObject {
                        ["name"] = new JObject { ["type"] = "string", ["description"] = "Type name or Type.Member." },
                        ["revit"] = revitProperty,
                    }, new[] { "name" }, readOnly: true),

                Tool("show_elements",
                    "Show elements to the user in the active view, without an approval prompt and without changing model elements: "
                    + "select them, temporarily isolate or hide them (Revit's temporary hide/isolate), or reset that mode. "
                    + "Target element ids and/or whole categories (resolved to the elements visible in the active view).",
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
                        ["revit"] = revitProperty,
                    }, new string[0], readOnly: true),

                Tool("capture_view",
                    "Take a PNG of a Revit view to check your work visually. mode 'export' (default) renders the view "
                    + "through Revit and works for any view by name or id. mode 'screen' captures the active view's window "
                    + "exactly as the user sees it, including selection and temporary isolate. view '3d' renders a temporary "
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
                            ["enum"] = new JArray("export", "screen"),
                            ["description"] = "export (default) or screen.",
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
                        ["revit"] = revitProperty,
                    }, new string[0], readOnly: true),

                Tool("run_query",
                    "Run a read-only Python script in Revit and return `result`, printed output, and any error with traceback. Always rolled back; must not change the model.",
                    new JObject {
                        ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Assign `result` to return data." },
                        ["title"] = new JObject { ["type"] = "string", ["description"] = "Short label for the run record." },
                        ["inputs"] = inputsProperty,
                        ["engine"] = engineProperty,
                        ["workspace"] = new JObject {
                            ["type"] = "string",
                            ["description"] = "Absolute path of a folder with your own helper modules (plan data, functions). It is on sys.path for the run and its modules are re-imported fresh every run, so `import house_plan` sees your latest edits.",
                        },
                        ["revit"] = revitProperty,
                    }, new[] { "script" }, readOnly: true),

                Tool("run_modify",
                    "Run a Python script that changes the model. With dry_run=true the change set is returned and everything is rolled back. Otherwise, under agent policy 'ask', Revit shows the user an approval prompt with the changed elements isolated; under policy 'auto' the change is committed directly. Kept changes become one undo entry named 'Agent: <title>'. Status 'rejected' means the user discarded the changes.",
                    new JObject {
                        ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Open transactions with DB.Transaction; assign `result` to return data." },
                        ["title"] = new JObject { ["type"] = "string", ["description"] = "What the change does; shown to the user and used as the undo name." },
                        ["dry_run"] = new JObject { ["type"] = "boolean", ["description"] = "Preview only: run, report the change set, roll back." },
                        ["inputs"] = inputsProperty,
                        ["engine"] = engineProperty,
                        ["workspace"] = new JObject {
                            ["type"] = "string",
                            ["description"] = "Absolute path of a folder with your own helper modules (plan data, functions). It is on sys.path for the run and its modules are re-imported fresh every run, so `import house_plan` sees your latest edits.",
                        },
                        ["revit"] = revitProperty,
                    }, new[] { "script", "title" }, readOnly: false),

                Tool("get_run",
                    "Read a recorded run by run_id: response, script, and pages of a result too large to return inline (use offset/length).",
                    new JObject {
                        ["run_id"] = new JObject { ["type"] = "string" },
                        ["offset"] = new JObject { ["type"] = "integer", ["description"] = "Character offset into a truncated result." },
                        ["length"] = new JObject { ["type"] = "integer", ["description"] = "Characters to return (max 204800)." },
                    }, new[] { "run_id" }, readOnly: true)
            );
        }

        private static JObject Tool(string name, string description, JObject properties, string[] required, bool readOnly) {
            return new JObject {
                ["name"] = name,
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
