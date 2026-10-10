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
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Executes one agent <c>run</c> request end to end on the Revit main thread: guard,
    /// script, decision (roll back, ask, commit), and the run folder record.
    /// </summary>
    /// <remarks>
    /// Invariants:
    /// <list type="bullet">
    /// <item>A query or dry run never leaves a change in the model.</item>
    /// <item>A modify run changes the model only after the user approves it in Revit, unless the
    /// <c>[agent] policy</c> is <c>auto</c>, the user's explicit opt-in to skip the prompt.</item>
    /// <item>The policy is read before the script starts and again after it finishes, and the
    /// stricter of the two (<c>readonly</c> over <c>ask</c> over <c>auto</c>) decides. A switch
    /// to <c>readonly</c> while a run was queued or running still stops its commit, and a script
    /// that rewrites the policy can't loosen it for its own run.</item>
    /// <item>A script error always rolls back.</item>
    /// <item>A run that changes any document other than the active one fails, rolls back and
    /// pauses the session, whatever its mode and the policy.</item>
    /// <item>A modify run requires an active document. Query and dry-run requests with no active
    /// document remain subject to their individual operation restrictions.</item>
    /// <item>Background documents the run created or opened are closed without saving when it
    /// ends, whatever its outcome, and listed in <c>closed_documents</c>. The guard blocks their
    /// save and save-as operations while the run is active.</item>
    /// </list>
    /// The host attempts to write <c>script.py</c>, <c>request.json</c> and <c>response.json</c>
    /// under <c>%APPDATA%\pyRevit\agent\runs\</c>; both JSON records carry the session id and the
    /// active document's title. A failure to persist an outcome never changes an already-final
    /// model decision.
    /// </remarks>
    internal static class AgentRunService {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly Encoding Utf8 = new UTF8Encoding(false);

        private const int MaxResultChars = 256 * 1024;
        private const int MaxOutputChars = 64 * 1024;
        private const int MaxChangeSamples = 50;

        internal static AgentPolicy ReadPolicy() {
            var policy = PyRevitConfigs.GetAgentPolicy();
            if (policy == PyRevitConsts.ConfigsAgentPolicyReadOnly)
                return AgentPolicy.ReadOnly;
            return policy == PyRevitConsts.ConfigsAgentPolicyAuto ? AgentPolicy.Auto : AgentPolicy.Ask;
        }

        private static AgentRunVerdict CarryOut(
            AgentRunVerdict verdict, AgentRunGuard guard, AgentScriptContext context, UIDocument uidoc,
            AgentRunRequest request, string runId, int exitCode, JObject changes) {
            switch (verdict) {
                case AgentRunVerdict.TransactionLeftOpen:
                    SetErrorIfMissing(context, "transaction_left_open",
                        "The script left a transaction open. Commit or roll back every transaction it starts.");
                    return verdict;
                case AgentRunVerdict.ScriptFailed:
                    SetErrorIfMissing(context, "engine_error",
                        "The script engine failed with exit code " + exitCode + ". Check the pyRevit log.");
                    guard.RollBack();
                    return verdict;
                case AgentRunVerdict.OtherDocumentChanged:
                    context.SetError("other_document_modified",
                        "The script changed another open document. Agent runs may change only the active "
                        + "document. See 'changes.other_documents' for rollback and discard outcomes. "
                        + "The agent session is now paused until the user resumes it.",
                        null);
                    try {
                        guard.RollBack();
                    }
                    finally {
                        AgentSessions.PauseForOtherDocument(guard.ChangedOtherOpenDocumentTitles);
                    }
                    return verdict;
                case AgentRunVerdict.NoDocument:
                    return verdict;
                case AgentRunVerdict.QueryModifiedModel:
                    guard.RollBack();
                    context.SetError("query_modified_model",
                        "A query run changed the model. The changes were rolled back; use mode 'dry_run' or 'modify'.",
                        null);
                    return verdict;
                case AgentRunVerdict.PolicyReadOnly:
                    context.SetError("policy_readonly",
                        "The pyRevit agent policy changed to 'readonly' during the run; its changes were rolled back.",
                        null);
                    guard.RollBack();
                    return verdict;
                case AgentRunVerdict.AutoCommit:
                    Commit(guard, uidoc.Document, request, runId);
                    return verdict;
                case AgentRunVerdict.AskUser:
                    guard.DisarmDialogCapture();
                    bool approved;
                    AgentHost.Activity.SetAwaitingApproval(true);
                    try {
                        approved = AgentApproval.Ask(uidoc, request.Title, guard.Changes, changes, guard.Failures);
                    }
                    finally {
                        AgentHost.Activity.SetAwaitingApproval(false);
                    }
                    if (approved) {
                        Commit(guard, uidoc.Document, request, runId);
                        return AgentRunVerdict.UserApproved;
                    }
                    guard.RollBack();
                    return AgentRunVerdict.UserDiscarded;
                default:
                    guard.RollBack();
                    return verdict;
            }
        }

        private static void Commit(AgentRunGuard guard, Document doc, AgentRunRequest request, string runId) {
            guard.Assimilate();
            AgentCommitSentinel.Remember(doc, runId, request.Title, guard.Changes.Added);
        }

        /// <remarks>
        /// The session is locked for the whole run, approval prompt included: the script can pause
        /// or end it, but can't start, resume or stop requiring one.
        /// </remarks>
        public static JToken Execute(UIApplication app, AgentRunRequest request) {
            using (AgentSessions.Tracker.BeginRun())
                return ExecuteRun(app, request);
        }

        private static JToken ExecuteRun(UIApplication app, AgentRunRequest request) {
            var uidoc = app.ActiveUIDocument;
            var doc = uidoc?.Document;
            if (doc == null && request.Mode == AgentRunMode.Modify)
                throw new AgentException("no_active_document", "A modify run requires an active document.");
            if (doc != null && doc.IsReadOnly && request.Mode != AgentRunMode.Query)
                throw new AgentException("document_read_only", "The active document is read-only.");
            if (doc != null && doc.IsModifiable)
                throw new AgentException("revit_busy", "Another transaction is open in the active document.");

            var runId = Guid.NewGuid().ToString("N").Substring(0, 12);
            var runDir = AgentPaths.CreateRunDir(runId);
            var sessionId = AgentSessions.Tracker.SessionId;
            var requestRecord = request.ToJson();
            requestRecord["session_id"] = sessionId;
            requestRecord["document"] = doc?.Title;
            File.WriteAllText(Path.Combine(runDir, "script.py"), request.Script, Utf8);
            File.WriteAllText(Path.Combine(runDir, "request.json"), requestRecord.ToString(Formatting.Indented), Utf8);

            var warnings = new JArray();
            var lostBefore = doc == null ? null : AgentCommitSentinel.Check(doc, afterRollback: false);
            if (lostBefore != null)
                warnings.Add(lostBefore);

            AgentHost.RefreshConfigIfChanged();
            var policyAtStart = ReadPolicy();

            var stopwatch = Stopwatch.StartNew();
            var context = new AgentScriptContext(app, runId, request.ModeName, request.Script, request.InputsJson, request.Workspace, request.TimeoutSeconds);
            var response = new JObject {
                ["run_id"] = runId,
                ["run_dir"] = runDir,
                ["mode"] = request.ModeName,
                ["title"] = request.Title,
                ["reason"] = request.Reason,
                ["session_id"] = sessionId,
                ["document"] = doc?.Title,
            };

            var openAtStart = AgentDocuments.Snapshot(app.Application);
            var guard = new AgentRunGuard(app, doc);
            using (guard) {
                try {
                    guard.Arm("Agent: " + request.Title);
                    var exitCode = AgentScriptRunner.Execute(context, request, runDir, AgentHost.SearchPaths);

                    var transactionLeftOpen = (doc != null && doc.IsModifiable) || guard.LeftTransactionOpenInOtherDocument;
                    if (guard.ErrorRollbacks > 0 && !context.HasError)
                        context.SetError(
                            "revit_failure",
                            $"Revit rolled back {guard.ErrorRollbacks} transaction(s) because of errors: "
                            + $"{guard.FirstErrorDescription} See 'failures' for every message. Fix the cause "
                            + "(for example an opening wider than its host wall) and run again.",
                            null);
                    var changes = doc != null ? guard.Changes.Describe(doc, MaxChangeSamples) : guard.Changes.Summarize();
                    var otherDocuments = guard.DescribeOtherDocuments();
                    if (otherDocuments.Count > 0)
                        changes["other_documents"] = otherDocuments;
                    AgentHost.RefreshConfigIfChanged();
                    var verdict = AgentRunDecision.Decide(new AgentRunFacts {
                        Mode = request.Mode,
                        HasDocument = doc != null,
                        TransactionLeftOpen = transactionLeftOpen,
                        ScriptFailed = context.HasError || exitCode != ScriptExecutorResultCodes.Succeeded,
                        ChangedOtherOpenDocument = guard.ChangedOtherOpenDocument,
                        HasChanges = !guard.Changes.IsEmpty,
                        Policy = AgentRunDecision.Stricter(policyAtStart, ReadPolicy()),
                    });
                    verdict = CarryOut(verdict, guard, context, uidoc, request, runId, exitCode, changes);

                    var approval = AgentRunDecision.Approval(verdict);
                    if (approval != null)
                        response["approval"] = approval;
                    response["status"] = AgentRunDecision.Status(verdict);
                    response["decision"] = AgentRunDecision.Decision(verdict);
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

            if (doc != null && response.Value<string>("decision") != "committed") {
                var lostByRollback = AgentCommitSentinel.Check(doc, afterRollback: true);
                if (lostByRollback != null) {
                    logger.Error("Agent run {0}: {1}", runId, lostByRollback);
                    warnings.Add(lostByRollback);
                }
            }
            try {
                var leftovers = AgentDocuments.CloseLeftovers(app.Application, openAtStart);
                response["closed_documents"] = leftovers["closed"];
                response["unclosed_documents"] = leftovers["failed"];
                if (((JArray)leftovers["failed"]).Count > 0)
                    warnings.Add("Could not close background documents the run left open: "
                        + string.Join(", ", leftovers["failed"].Values<string>()));
            }
            catch (Exception ex) {
                logger.Warn("Agent run {0}: closing leftover documents failed: {1}", runId, ex.Message);
                warnings.Add("Closing leftover documents failed: " + ex.Message);
            }
            var finalOtherDocuments = guard.DescribeOtherDocuments();
            foreach (var failure in guard.CleanupFailures)
                warnings.Add("Guard cleanup failed: " + failure);
            if (finalOtherDocuments.Count > 0) {
                var changes = response["changes"] as JObject;
                if (changes == null) {
                    changes = new JObject();
                    response["changes"] = changes;
                }
                changes["other_documents"] = finalOtherDocuments;
            }
            if (guard.HasUnrevertedOtherDocumentChanges) {
                response["status"] = "error";
                response["decision"] = "rollback_incomplete";
                warnings.Add("Changes remain in another open document. Close it without saving to discard them. "
                    + "See 'changes.other_documents' for the documents that were not reverted.");
                SetErrorIfMissing(context, "rollback_incomplete",
                    "The host could not revert changes in another document. Close it without saving.");
            }
            response["warnings"] = warnings;

            AddScriptOutcome(response, context, runDir, request.Engine == AgentEngine.CPython ? "cpython" : "ironpython", warnings);
            response["elapsed_ms"] = stopwatch.ElapsedMilliseconds;

            try {
                File.WriteAllText(Path.Combine(runDir, "response.json"), response.ToString(Formatting.Indented), Utf8);
            }
            catch (Exception ex) {
                logger.Warn("Could not write agent run record: {0}", ex.Message);
                warnings.Add("Could not write the agent run record: " + ex.Message);
            }

            return response;
        }

        private static void SetErrorIfMissing(AgentScriptContext context, string type, string message) {
            if (!context.HasError)
                context.SetError(type, message, null);
        }

        private static void AddScriptOutcome(
            JObject response, AgentScriptContext context, string runDir, string requestedEngine, JArray warnings) {
            var output = context.Output ?? string.Empty;
            response["output_truncated"] = output.Length > MaxOutputChars;
            response["output"] = output.Length > MaxOutputChars ? output.Substring(0, MaxOutputChars) : output;

            response["result"] = null;
            response["result_truncated"] = false;
            if (context.ResultJson != null) {
                try {
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
                catch (Exception ex) {
                    logger.Warn("Could not record agent script result: {0}", ex.Message);
                    warnings.Add("Could not record the script result: " + ex.Message);
                    response["result"] = null;
                    response["result_truncated"] = false;
                    response.Remove("result_path");
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
