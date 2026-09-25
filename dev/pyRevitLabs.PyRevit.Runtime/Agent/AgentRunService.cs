using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text;

using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Executes one agent <c>run</c> request end to end on the Revit main thread: guard,
    /// script, decision (roll back, ask, commit), and the run folder record.
    /// </summary>
    /// <remarks>
    /// Invariants:
    /// <list type="bullet">
    /// <item>A query or dry run never leaves a change in the model.</item>
    /// <item>A modify run changes the model only after the user approves it in Revit.</item>
    /// <item>A script error always rolls back.</item>
    /// </list>
    /// Every run writes <c>script.py</c>, <c>request.json</c> and <c>response.json</c> under
    /// <c>%APPDATA%\pyRevit\agent\runs\</c>.
    /// </remarks>
    internal static class AgentRunService {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly Encoding Utf8 = new UTF8Encoding(false);

        private const int MaxResultChars = 256 * 1024;
        private const int MaxOutputChars = 64 * 1024;
        private const int MaxChangeSamples = 50;

        public static JToken Execute(UIApplication app, AgentRunRequest request) {
            var uidoc = app.ActiveUIDocument
                ?? throw new AgentException("no_active_document", "Revit has no active document.");
            var doc = uidoc.Document;
            if (doc.IsReadOnly && request.Mode != AgentRunMode.Query)
                throw new AgentException("document_read_only", "The active document is read-only.");
            if (doc.IsModifiable)
                throw new AgentException("revit_busy", "Another transaction is open in the active document.");

            var runId = Guid.NewGuid().ToString("N").Substring(0, 12);
            var runDir = AgentPaths.CreateRunDir(runId);
            File.WriteAllText(Path.Combine(runDir, "script.py"), request.Script, Utf8);
            File.WriteAllText(Path.Combine(runDir, "request.json"), request.ToJson().ToString(Formatting.Indented), Utf8);

            var stopwatch = Stopwatch.StartNew();
            var context = new AgentScriptContext(app, runId, request.ModeName, request.Script, request.InputsJson);
            var response = new JObject {
                ["run_id"] = runId,
                ["run_dir"] = runDir,
                ["mode"] = request.ModeName,
                ["title"] = request.Title,
            };

            using (var guard = new AgentRunGuard(app, doc)) {
                try {
                    guard.Arm("Agent: " + request.Title);
                    var exitCode = AgentScriptRunner.Execute(context, request, runDir, AgentHost.SearchPaths);

                    var transactionLeftOpen = doc.IsModifiable;
                    if (guard.ErrorRollbacks > 0 && !context.HasError)
                        context.SetError(
                            "revit_failure",
                            $"Revit rolled back {guard.ErrorRollbacks} transaction(s) because of errors: "
                            + $"{guard.FirstErrorDescription} See 'failures' for every message. Fix the cause "
                            + "(for example an opening wider than its host wall) and run again.",
                            null);
                    var changes = guard.Changes.Describe(doc, MaxChangeSamples);
                    var status = "ok";
                    string decision;

                    if (transactionLeftOpen) {
                        status = "error";
                        decision = "rolled_back";
                        SetErrorIfMissing(context, "transaction_left_open",
                            "The script left a transaction open. Commit or roll back every transaction it starts.");
                    }
                    else if (context.HasError || exitCode != ScriptExecutorResultCodes.Succeeded) {
                        status = "error";
                        decision = "rolled_back";
                        SetErrorIfMissing(context, "engine_error",
                            "The script engine failed with exit code " + exitCode + ". Check the pyRevit log.");
                        guard.RollBack();
                    }
                    else if (request.Mode == AgentRunMode.Query) {
                        decision = "rolled_back";
                        guard.RollBack();
                        if (!guard.Changes.IsEmpty) {
                            status = "error";
                            context.SetError("query_modified_model",
                                "A query run changed the model. The changes were rolled back; use mode 'dry_run' or 'modify'.",
                                null);
                        }
                    }
                    else if (request.Mode == AgentRunMode.DryRun || guard.Changes.IsEmpty) {
                        decision = guard.Changes.IsEmpty ? "no_changes" : "rolled_back";
                        guard.RollBack();
                    }
                    else {
                        guard.DisarmDialogCapture();
                        var approved = AgentApproval.Ask(uidoc, request.Title, guard.Changes, changes, guard.Failures);
                        if (approved) {
                            guard.Assimilate();
                            decision = "committed";
                        }
                        else {
                            guard.RollBack();
                            decision = "discarded";
                            status = "rejected";
                        }
                    }

                    response["status"] = status;
                    response["decision"] = decision;
                    response["exit_code"] = exitCode;
                    response["changes"] = changes;
                    response["failures"] = guard.Failures;
                    response["dialogs"] = guard.Dialogs;
                    response["blocked"] = guard.Blocked;
                }
                catch (Exception ex) {
                    logger.Error(ex, "Agent run {0} failed in the host", runId);
                    context.SetError("host_error", ex.Message, ex.ToString());
                    response["status"] = "error";
                    response["decision"] = "rolled_back";
                    response["failures"] = guard.Failures;
                    response["dialogs"] = guard.Dialogs;
                    response["blocked"] = guard.Blocked;
                }
            }

            AddScriptOutcome(response, context, runDir, request.Engine == AgentEngine.CPython ? "cpython" : "ironpython");
            response["elapsed_ms"] = stopwatch.ElapsedMilliseconds;

            try {
                File.WriteAllText(Path.Combine(runDir, "response.json"), response.ToString(Formatting.Indented), Utf8);
            }
            catch (Exception ex) {
                logger.Warn("Could not write agent run record: {0}", ex.Message);
            }

            return response;
        }

        private static void SetErrorIfMissing(AgentScriptContext context, string type, string message) {
            if (!context.HasError)
                context.SetError(type, message, null);
        }

        private static void AddScriptOutcome(JObject response, AgentScriptContext context, string runDir, string requestedEngine) {
            var output = context.Output ?? string.Empty;
            response["output_truncated"] = output.Length > MaxOutputChars;
            response["output"] = output.Length > MaxOutputChars ? output.Substring(0, MaxOutputChars) : output;

            response["result"] = null;
            response["result_truncated"] = false;
            if (context.ResultJson != null) {
                if (context.ResultJson.Length > MaxResultChars) {
                    var resultPath = Path.Combine(runDir, "result.json");
                    File.WriteAllText(resultPath, context.ResultJson, Utf8);
                    response["result_truncated"] = true;
                    response["result_path"] = resultPath;
                }
                else {
                    response["result"] = JToken.Parse(context.ResultJson);
                }
            }

            response["engine"] = new JObject {
                ["requested"] = requestedEngine,
                ["implementation"] = context.EngineImplementation,
                ["python"] = context.EnginePythonVersion,
                ["sys_version"] = context.EngineVersionText,
            };

            response["error"] = context.HasError
                ? new JObject {
                    ["type"] = context.ErrorType,
                    ["message"] = context.ErrorMessage,
                    ["traceback"] = context.ErrorTraceback,
                }
                : null;
        }
    }

    /// <summary>
    /// Asks the user, inside Revit, whether to keep the changes of a modify run.
    /// </summary>
    /// <remarks>
    /// Runs while the run's transaction group is still open, so the changed elements are
    /// selected and temporarily isolated in the live active view while the user decides.
    /// Invariant: the preview never outlives the prompt. Isolation is switched off again
    /// before this returns, so a kept change set never leaves the view isolated.
    /// </remarks>
    internal static class AgentApproval {
        private const int MaxListedCategories = 15;

        public static bool Ask(UIDocument uidoc, string title, AgentChangeSet changeSet, JObject changes, JArray failures) {
            var previousSelection = uidoc.Selection.GetElementIds();
            var preview = AgentViewPreview.Show(uidoc, changeSet.Touched);

            var dialog = new TaskDialog("pyRevit Agent") {
                MainInstruction = "An agent wants to modify the model",
                MainContent = BuildSummary(title, changes, failures, preview.Description),
                ExpandedContent = changes.ToString(Formatting.Indented),
                CommonButtons = TaskDialogCommonButtons.None,
                AllowCancellation = true,
            };
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink1, "Keep these changes",
                "Commit them as a single undoable operation.");
            dialog.AddCommandLink(TaskDialogCommandLinkId.CommandLink2, "Discard these changes",
                "Roll the model back to its state before the run.");
            dialog.DefaultButton = TaskDialogResult.CommandLink2;

            var approved = dialog.Show() == TaskDialogResult.CommandLink1;
            preview.End();
            if (!approved) {
                try {
                    uidoc.Selection.SetElementIds(previousSelection);
                }
                catch (Exception) {
                }
            }
            return approved;
        }

        private static string BuildSummary(string title, JObject changes, JArray failures, string previewDescription) {
            var summary = new StringBuilder();
            summary.AppendLine("Operation: " + title);
            summary.AppendLine(string.Format(
                "Added: {0}   Modified: {1}   Deleted: {2}",
                changes.Value<int>("added_count"),
                changes.Value<int>("modified_count"),
                changes.Value<int>("deleted_count")));

            var byCategory = changes["by_category"] as JObject;
            if (byCategory != null && byCategory.Count > 0) {
                summary.AppendLine();
                foreach (var pair in byCategory.Properties().Take(MaxListedCategories))
                    summary.AppendLine("  " + pair.Name + ": " + pair.Value);
            }

            if (failures.Count > 0) {
                summary.AppendLine();
                summary.AppendLine(failures.Count + " warning(s) were raised and removed during the run.");
            }

            summary.AppendLine();
            summary.Append(previewDescription);
            return summary.ToString();
        }
    }

    /// <summary>
    /// Selects and temporarily isolates the changed elements in the active view for the
    /// duration of the approval prompt.
    /// </summary>
    /// <remarks>
    /// Isolation changes view state, so it runs in its own transaction inside the run's
    /// open group. <see cref="End"/> turns it off in a second transaction, so the group ends
    /// with no net view change whether it is assimilated or rolled back. A view that already
    /// has a temporary hide/isolate is left alone, so the user's own isolation is never lost.
    /// </remarks>
    internal sealed class AgentViewPreview {
        private const string TransactionName = "pyRevit Agent preview";

        private readonly Document doc;
        private readonly View view;

        private AgentViewPreview(Document doc, View view, string description) {
            this.doc = doc;
            this.view = view;
            Description = description;
        }

        public string Description { get; }

        public static AgentViewPreview Show(UIDocument uidoc, ICollection<ElementId> touched) {
            var doc = uidoc.Document;
            var visibleCandidates = touched
                .Where(id => doc.GetElement(id)?.Category != null)
                .ToList();

            if (visibleCandidates.Count == 0)
                return new AgentViewPreview(doc, null, "None of the changed elements can be shown in a view.");

            try {
                uidoc.Selection.SetElementIds(visibleCandidates);
            }
            catch (Exception) {
            }

            var view = uidoc.ActiveView;
            if (view == null || view.IsTemplate || view.IsTemporaryHideIsolateActive()) {
                uidoc.RefreshActiveView();
                return new AgentViewPreview(doc, null,
                    "The changed elements are selected in the active view.");
            }

            try {
                using (var transaction = new Transaction(doc, TransactionName)) {
                    transaction.Start();
                    view.IsolateElementsTemporary(visibleCandidates);
                    transaction.Commit();
                }
                uidoc.RefreshActiveView();
                return new AgentViewPreview(doc, view,
                    "The changed elements are selected and temporarily isolated in the active view.");
            }
            catch (Exception) {
                uidoc.RefreshActiveView();
                return new AgentViewPreview(doc, null,
                    "The changed elements are selected in the active view (this view can't isolate them).");
            }
        }

        public void End() {
            if (view == null)
                return;
            try {
                using (var transaction = new Transaction(doc, TransactionName)) {
                    transaction.Start();
                    view.DisableTemporaryViewMode(TemporaryViewMode.TemporaryHideIsolate);
                    transaction.Commit();
                }
            }
            catch (Exception) {
            }
        }
    }
}
