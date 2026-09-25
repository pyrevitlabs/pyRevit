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
                ["instructions"] = Instructions,
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
                        : ToolResult(payload.ToString(Formatting.None), isError);
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
                case "list_revit_instances":
                    return ListInstances();
                case "get_context":
                    return CallRevit(arguments, "get_context", new JObject());
                case "inspect_elements":
                    return CallRevit(arguments, "inspect_elements", new JObject {
                        ["ids"] = arguments["ids"],
                        ["parameters"] = arguments["parameters"] ?? true,
                    });
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
        private const string Instructions =
@"pyRevit MCP server: read and change live Revit models by running Python inside Revit.

Workflow:
1. Call get_context first. It reports the Revit version, the open document, the active view, the selection, levels, the agent policy, and `scripting`: which engine runs your scripts and its exact Python version and syntax limits.
2. Explore with run_query, inspect_elements and lookup_revit_api. Filter and aggregate inside the script; return only what you need.
3. To show the user elements (select, zoom, temporarily isolate or hide them in the active view), call show_elements. It needs no approval and changes no model elements; don't write run_modify scripts for this.
4. To change the model, call run_modify with dry_run=true first and review the change set. Then call run_modify without dry_run. With agent policy 'ask' the user approves it in Revit, and status 'rejected' means they discarded it, so don't retry without asking them. With policy 'auto' (see get_context.agent.policy) the change is committed without a prompt, so dry-run first and keep each change focused. With 'readonly', modify runs are refused.

Script conventions:
- The script is Python executed in Revit. Injected names: doc, uidoc, app, uiapp, DB (Autodesk.Revit.DB), UI (Autodesk.Revit.UI), inputs (dict from the 'inputs' argument).
- Return data by assigning `result` (JSON-serializable; ElementId, Element and XYZ are converted automatically). print() output is returned too but is for short notes.
- Before writing code, read get_context.scripting. Scripts run on scripting.default_engine unless you pass engine; write for that engine's `python` version and respect its `syntax` notes (IronPython 2.7 is Python 2 syntax; IronPython 3.4 has f-strings but no walrus, async or 1_000 literals). Pass engine='cpython' only when scripting.engines.cpython.available is true and you need modern Python. Each run response's `engine` field confirms what actually ran.
- run_query must not open transactions; if the model changes, the run fails with query_modified_model and is rolled back.
- In run_modify, open your own transactions: t = DB.Transaction(doc, 'name'); t.Start(); ...; t.Commit(). The whole run becomes one undo entry.
- Revit internal units are feet and radians. Use DB.UnitUtils to convert when reporting values.
- ElementId: use .Value on Revit 2024+ (IntegerValue before). Build ids with DB.ElementId(value).
- Revit shows no dialogs during a run: they are closed automatically and reported in 'dialogs'. Warnings are removed and reported in 'failures'.
- If unsure about a class or method, call lookup_revit_api instead of guessing; it reflects the exact Revit version that is running.
- When a run fails with AttributeError or TypeError on a Revit object, call lookup_revit_api before the next attempt. The error's `hint` names the lookup to make.

Revit API idioms (common mistakes):
- Collect elements with DB.FilteredElementCollector(doc); there is no DB.Collector. Instances of a class: .OfClass(DB.Wall). Instances in a category: .OfCategory(DB.BuiltInCategory.OST_Doors).WhereElementIsNotElementType().
- OfCategory takes a BuiltInCategory, not a Category object.
- A category can hold several element classes (OST_Walls also returns in-place walls as FamilyInstance). Use OfClass(...) or isinstance() when you need members of one class, such as Wall.WallType.
- DB.Category.GetCategory(doc, DB.BuiltInCategory.OST_Walls) needs the document as its first argument.
- Element type: doc.GetElement(element.GetTypeId()). Parameters: element.LookupParameter('Mark') by name, element.get_Parameter(DB.BuiltInParameter.ALL_MODEL_MARK) for built-ins.
- Collector counts: collector.GetElementCount() is cheaper than len(collector.ToElements()).
- OfClass only accepts classes that exist in Revit's native object model. For rooms, areas, spaces, family symbols of a category and similar API-only classes use OfCategory(DB.BuiltInCategory.OST_Rooms) (or OfClass(DB.SpatialElement)) and filter with isinstance().
- There is no DB.Roof: roofs are DB.RoofBase (FootPrintRoof, ExtrusionRoof); rooms are DB.Architecture.Room.
- Methods typed ICollection<ElementId> or IList<...> need a .NET collection, not a Python list: from System.Collections.Generic import List; ids = List[DB.ElementId](python_ids).
- Anything that changes the document needs a transaction and run_modify, including persistent view changes such as graphic overrides and view properties. For selecting, zooming, and temporary hide/isolate use show_elements instead.
- Enum values differ from UI names (TemporaryViewMode.TemporaryHideIsolate, not .Isolate). Look up the enum with lookup_revit_api before using a value you haven't seen.
- lookup_revit_api lists a type's declared members only; for inherited members, look up its base_type.
- A status 'error' with type revit_failure means Revit rolled back a transaction because of an error; 'failures' lists the messages (for example an opening that can't cut its host wall).

Modeling idioms:
- DB and UI are injected; don't import them. Types outside Autodesk.Revit.DB live in sub-namespaces (DB.Structure.StructuralType, DB.Architecture.Room); lookup_revit_api returns each type's python_import line.
- To create an element, read lookup_revit_api(name='<Type>').creation first. Some types have static factories (Wall.Create, Floor.Create, Point.Create); others are created through doc.Create.New... (NewFootPrintRoof, NewRoom(level, uv), NewFamilyInstance).
- Out parameters: omit them from Python calls; the call returns a tuple (result, out values...).
- Geometry: Line.CreateBound(XYZ, XYZ); Floor.Create(doc, List[DB.CurveLoop]([loop]), floor_type.Id, level.Id) takes ElementIds and closed CurveLoops.
- Prefer native elements (walls, floors, roofs, families) over DirectShape. Native elements carry their type's materials and stay editable.
- Gable roof: one rectangular footprint through doc.Create.NewFootPrintRoof(curve_array, level, roof_type), which returns the roof and its footprint ModelCurveArray. Call roof.set_DefinesSlope(curve, True) and roof.set_SlopeAngle(curve, slope) on the two eave edges only; the gable-end edges keep DefinesSlope False. Check the member names with lookup_revit_api(name='FootPrintRoof').
- DirectShape materials: build the solid with GeometryCreationUtilities.CreateExtrusionGeometry(loops, direction, distance, DB.SolidOptions(material_id, DB.ElementId.InvalidElementId)).
- Check your work visually: after a modeling step, capture_view(view='3d') shows the whole model, and capture_view(view='<plan name>') shows a plan. Compare it with what you intended before moving on.
- Build large models in steps (shell, openings, roofs, rooms) with a dry run for each. A failed or rejected step leaves the earlier steps intact, and each committed step is its own undo entry.";

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

            return new JArray(
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
                    + "isometric 3D view of the whole model (never saved). The image is also saved under "
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
                        ["revit"] = revitProperty,
                    }, new string[0], readOnly: true),

                Tool("run_query",
                    "Run a read-only Python script in Revit and return `result`, printed output, and any error with traceback. Always rolled back; must not change the model.",
                    new JObject {
                        ["script"] = new JObject { ["type"] = "string", ["description"] = "Python source. Assign `result` to return data." },
                        ["title"] = new JObject { ["type"] = "string", ["description"] = "Short label for the run record." },
                        ["inputs"] = inputsProperty,
                        ["engine"] = engineProperty,
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
