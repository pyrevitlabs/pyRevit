using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
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
    /// <item>A looser policy than the one in force applies only after the user confirms it in
    /// Revit, so a script that rewrites the policy can't loosen it for later runs either. Only
    /// a modify run asks; a query or dry run never waits on the prompt.</item>
    /// <item>A script error always rolls back.</item>
    /// <item><c>[agent] reckless</c> is read once before the script starts and only turns off
    /// the Python runner's in-script checks (timeout, per-line transaction tracking). Every
    /// guarantee in this list still holds for a reckless run, which the response marks with
    /// <c>"reckless": true</c>. Turning it on applies only after the user confirms it in Revit,
    /// like a looser policy, so a script that rewrites the config can't make later runs
    /// reckless. Unlike the policy prompt, any run mode asks, since reckless also affects
    /// queries and dry runs.</item>
    /// <item>A run that changes any document other than the active one fails and rolls back,
    /// whatever its mode and the policy.</item>
    /// <item>A modify run requires an active document. Query and dry-run requests with no active
    /// document remain subject to their individual operation restrictions.</item>
    /// <item>Background documents the run created or opened are closed without saving when it
    /// ends, whatever its outcome, and listed in <c>closed_documents</c>. The guard blocks their
    /// save and save-as operations while the run is active.</item>
    /// <item>A host error reports <c>committed</c> only when the change set was already kept,
    /// and <c>rollback_incomplete</c> when its rollback failed.</item>
    /// </list>
    /// The host attempts to write <c>script.py</c>, <c>request.json</c> and <c>response.json</c>
    /// under <c>%APPDATA%\pyRevit\agent\runs\</c>. A failure to persist an outcome never
    /// changes an already-final model decision.
    /// </remarks>
    internal static class AgentRunService {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly Encoding Utf8 = new UTF8Encoding(false);

        private const int MaxResultChars = 256 * 1024;
        private const int MaxOutputChars = 64 * 1024;
        private const int MaxChangeSamples = 50;

        private static AgentPolicy ReadPolicy() {
            var policy = PyRevitConfigs.GetAgentPolicy();
            if (policy == PyRevitConsts.ConfigsAgentPolicyReadOnly)
                return AgentPolicy.ReadOnly;
            return policy == PyRevitConsts.ConfigsAgentPolicyAuto ? AgentPolicy.Auto : AgentPolicy.Ask;
        }

        private static readonly AgentPolicyInForce policyInForce = new AgentPolicyInForce();

        /// <summary>
        /// The policy the next run starts under unless the user confirms a looser one; never
        /// prompts. Main thread only.
        /// </summary>
        /// <remarks>
        /// Records a stricter configured policy, like every other place the host acts on one,
        /// so a policy reported as in force can't be loosened later without confirmation.
        /// </remarks>
        internal static string PolicyNameInForce() {
            return AgentApproval.Name(policyInForce.Tighten(ReadPolicy()));
        }

        private static readonly AgentRecklessInForce recklessInForce = new AgentRecklessInForce();

        /// <summary>
        /// Whether the next run is reckless unless the user confirms turning it on; never
        /// prompts. Main thread only.
        /// </summary>
        internal static bool RecklessInForce() {
            return recklessInForce.Tighten(PyRevitConfigs.GetAgentReckless());
        }

        private static AgentRunVerdict CarryOut(
            AgentRunVerdict verdict, AgentRunGuard guard, AgentScriptContext context, UIDocument uidoc,
            AgentRunRequest request, string runId, int exitCode, JObject changes, AgentTabHighlight.Lease highlight,
            AgentRunTimings timings) {
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
                        + "document. See 'changes.other_documents' for rollback and discard outcomes.",
                        null);
                    guard.RollBack();
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
                    timings.Lap("decide");
                    AgentHost.AwaitTabApproval(highlight);
                    var approved = AgentApproval.Ask(uidoc, request.Title, guard.Changes, changes, guard.Failures);
                    timings.Lap("approval");
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
        /// Invariant: runs never nest. A script that calls <see cref="AgentHost.HandleRequest"/>
        /// would otherwise start a run inside its own guard, whose rollback undoes a change the
        /// inner run reports as kept.
        /// </remarks>
        public static JToken Execute(UIApplication app, AgentRunRequest request) {
            if (runInProgress)
                throw new AgentException("nested_run", "An agent run can't start from inside another agent run.");
            runInProgress = true;
            try {
                return ExecuteRun(app, request);
            }
            finally {
                runInProgress = false;
            }
        }

        private static bool runInProgress;

        private static JToken ExecuteRun(UIApplication app, AgentRunRequest request) {
            var timings = new AgentRunTimings((Stopwatch.GetTimestamp() - request.ReceivedTimestamp) * 1000.0 / Stopwatch.Frequency);
            var uidoc = app.ActiveUIDocument;
            var doc = uidoc?.Document;
            if (request.Document != null && (doc == null || !AgentDocumentBinding.Matches(request.Document, doc.Title, doc.PathName)))
                throw AgentDocumentBinding.Refusal(request.Document, doc?.Title);
            if (doc == null && request.Mode == AgentRunMode.Modify)
                throw new AgentException("no_active_document", "A modify run requires an active document.");
            if (doc != null && doc.IsReadOnly && request.Mode != AgentRunMode.Query)
                throw new AgentException("document_read_only", "The active document is read-only.");
            if (doc != null && doc.IsModifiable)
                throw AgentException.NotRun("Another transaction is open in the active document.");

            AgentHost.RefreshConfigIfChanged();
            var policyAtStart = request.Mode == AgentRunMode.Modify
                ? policyInForce.Start(ReadPolicy(),
                    (inForce, configured) => AgentApproval.ConfirmLoosening(app.MainWindowHandle, inForce, configured))
                : policyInForce.Tighten(ReadPolicy());
            if (request.Mode == AgentRunMode.Modify && policyAtStart == AgentPolicy.ReadOnly)
                throw new AgentException(
                    "policy_readonly",
                    "The pyRevit agent policy is 'readonly': modify runs are disabled. Use query or dry_run.");
            var reckless = recklessInForce.Start(PyRevitConfigs.GetAgentReckless(),
                (inForce, configured) => AgentApproval.ConfirmReckless(app.MainWindowHandle));

            var highlight = AgentHost.BeginTabHighlight(app, doc, request.Title);
            try {
                var runId = Guid.NewGuid().ToString("N").Substring(0, 12);
                var runDir = AgentPaths.CreateRunDir(runId);
                WriteRequestRecord(runDir, request);

                var warnings = new JArray();
                var lostBefore = doc == null ? null : AgentCommitSentinel.Check(doc, afterRollback: false);
                if (lostBefore != null)
                    warnings.Add(lostBefore);

                var stopwatch = Stopwatch.StartNew();
                var context = new AgentScriptContext(app, runId, request.ModeName, request.Script, request.InputsJson, request.Workspace, request.TimeoutSeconds, reckless) {
                    Timings = timings,
                };
                var response = new JObject {
                    ["run_id"] = runId,
                    ["run_dir"] = runDir,
                    ["request_id"] = request.RequestId,
                    ["mode"] = request.ModeName,
                    ["title"] = request.Title,
                };

                timings.Lap("prepare");
                var openAtStart = AgentDocuments.Snapshot(app.Application);
                var guard = new AgentRunGuard(app, doc);
                var scriptStarted = false;
                using (guard) {
                    try {
                        guard.Arm("Agent: " + request.Title);
                        timings.Lap("guard_arm");
                        int exitCode;
                        using (reckless ? null : AgentHost.Dispatcher?.BeginScript(TimeSpan.FromSeconds(request.TimeoutSeconds), runId, request.RequestId))
                            exitCode = AgentScriptRunner.Execute(context, request, runDir, AgentHost.SearchPaths, () => scriptStarted = true);
                        timings.Lap("engine");

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
                        timings.Lap("changes");
                        AgentHost.RefreshConfigIfChanged();
                        var verdict = AgentRunDecision.Decide(new AgentRunFacts {
                            Mode = request.Mode,
                            HasDocument = doc != null,
                            TransactionLeftOpen = transactionLeftOpen,
                            ScriptFailed = context.HasError || exitCode != ScriptExecutorResultCodes.Succeeded,
                            ChangedOtherOpenDocument = guard.ChangedOtherOpenDocument,
                            HasChanges = !guard.Changes.IsEmpty,
                            Policy = AgentRunDecision.Stricter(policyAtStart, policyInForce.Tighten(ReadPolicy())),
                        });
                        timings.Lap("decide");
                        verdict = CarryOut(verdict, guard, context, uidoc, request, runId, exitCode, changes, highlight, timings);
                        timings.Lap("guard_release");

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
                        response["decision"] = AgentRunDecision.AfterHostError(guard.Committed, scriptStarted);
                        response["failures"] = guard.Failures;
                        response["dialogs"] = guard.Dialogs;
                        response["blocked"] = guard.Blocked;
                    }
                }
                timings.Lap("guard_release");
                if (guard.RollbackFailed) {
                    response["status"] = "error";
                    response["decision"] = "rollback_incomplete";
                    SetErrorIfMissing(context, "rollback_incomplete",
                        "The host could not roll back the run, so its changes may remain in the active document. "
                        + "Ask the user to undo them in Revit or close the document without saving.");
                }

                if (doc != null && scriptStarted && !guard.RollbackFailed && response.Value<string>("decision") != "committed") {
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
                var blockedExplanation = guard.DescribeBlockedOperations();
                if (blockedExplanation != null)
                    warnings.Add(blockedExplanation);
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
                timings.Lap("cleanup");

                AddScriptOutcome(response, context, runDir, request.Engine == AgentEngine.CPython ? "cpython" : "ironpython", warnings);
                response["elapsed_ms"] = stopwatch.ElapsedMilliseconds;
                timings.Lap("outcome");
                if (reckless)
                    response["reckless"] = true;
                response["timings_ms"] = timings.ToJson();
                logger.Debug("[PERF] agent run {0} ({1}, {2}): {3}", runId, request.ModeName, response["engine"]?["implementation"], timings.Describe());

                try {
                    File.WriteAllText(Path.Combine(runDir, "response.json"), response.ToString(Formatting.Indented), Utf8);
                }
                catch (Exception ex) {
                    logger.Warn("Could not write agent run record: {0}", ex.Message);
                    warnings.Add("Could not write the agent run record: " + ex.Message);
                }

                return response;
            }
            finally {
                AgentHost.EndTabHighlight(highlight);
            }
        }

        private static void WriteRequestRecord(string runDir, AgentRunRequest request) {
            File.WriteAllText(Path.Combine(runDir, "script.py"), request.Script, Utf8);
            File.WriteAllText(Path.Combine(runDir, "request.json"), request.ToJson().ToString(Formatting.Indented), Utf8);
        }

        /// <summary>
        /// Leaves a run folder for a request the host refused before running any of it
        /// (<c>revit_busy</c> or <c>document_changed</c>), with
        /// <c>status</c> and <c>decision</c> <c>not_run</c>, and adds its <c>run_id</c> and
        /// <c>run_dir</c> to <paramref name="refusal"/>.
        /// </summary>
        /// <remarks>
        /// Without it a refused request leaves no trace, so a caller that got no answer can not tell
        /// a request that never ran from one still queued. Best effort: a failure to write the
        /// record only means the error carries no <c>run_id</c>.
        /// </remarks>
        public static void RecordNotRun(AgentRunRequest request, AgentException refusal) {
            try {
                var runId = Guid.NewGuid().ToString("N").Substring(0, 12);
                var runDir = AgentPaths.CreateRunDir(runId);
                WriteRequestRecord(runDir, request);
                var record = new JObject {
                    ["run_id"] = runId,
                    ["run_dir"] = runDir,
                    ["request_id"] = request.RequestId,
                    ["mode"] = request.ModeName,
                    ["title"] = request.Title,
                    ["status"] = "not_run",
                    ["decision"] = "not_run",
                    ["error"] = new JObject { ["type"] = refusal.Code, ["message"] = refusal.Message },
                };
                File.WriteAllText(Path.Combine(runDir, "response.json"), record.ToString(Formatting.Indented), Utf8);
                refusal.Details["run_id"] = runId;
                refusal.Details["run_dir"] = runDir;
            }
            catch (Exception ex) {
                logger.Warn("Could not write the record of a refused agent request: {0}", ex.Message);
            }
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
    /// Important: the prompt is a native Windows message box, not a Revit <c>TaskDialog</c>.
    /// Revit raises <c>DialogBoxShowing</c> for a <c>TaskDialog</c>, so a handler the script
    /// subscribed could answer the prompt for the user.
    /// </remarks>
    internal static class AgentApproval {
        private const int MaxListedCategories = 15;
        private const uint YesNoQuestionDefaultNo = 0x4 | 0x20 | 0x100;
        private const int Yes = 6;

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int MessageBox(IntPtr owner, string text, string caption, uint type);

        public static bool ConfirmLoosening(IntPtr owner, AgentPolicy inForce, AgentPolicy configured) {
            var text = string.Format(
                "The pyRevit agent policy changed from '{0}' to '{1}'.{2}{2}"
                + "Allow agents to work under '{1}'? No keeps '{0}' until Revit restarts.",
                Name(inForce), Name(configured), Environment.NewLine);
            return MessageBox(owner, text, "pyRevit Agent policy", YesNoQuestionDefaultNo) == Yes;
        }

        public static bool ConfirmReckless(IntPtr owner) {
            var text = "pyRevit agent reckless mode was turned on." + Environment.NewLine + Environment.NewLine
                + "Reckless runs have no timeout and no in-script transaction checks. "
                + "Allow agents to run reckless? No keeps it off until Revit restarts or the setting changes again.";
            return MessageBox(owner, text, "pyRevit Agent reckless mode", YesNoQuestionDefaultNo) == Yes;
        }

        internal static string Name(AgentPolicy policy) => policy.ToString().ToLowerInvariant();

        public static bool Ask(UIDocument uidoc, string title, AgentChangeSet changeSet, JObject changes, JArray failures) {
            var previousSelection = uidoc.Selection.GetElementIds();
            var preview = AgentViewPreview.Show(uidoc, changeSet.Touched);

            var text = "An agent wants to modify the model." + Environment.NewLine + Environment.NewLine
                + BuildSummary(uidoc.Document.Title, title, changes, failures, preview.Description) + Environment.NewLine + Environment.NewLine
                + "Keep these changes? Yes commits them as a single undoable operation. "
                + "No rolls the model back to its state before the run.";
            var approved = MessageBox(uidoc.Application.MainWindowHandle, text, "pyRevit Agent", YesNoQuestionDefaultNo) == Yes;
            try {
                preview.End();
            }
            catch (Exception) when (!approved) {
            }
            if (!approved) {
                try {
                    uidoc.Selection.SetElementIds(previousSelection);
                }
                catch (Exception) {
                }
            }
            return approved;
        }

        private static string BuildSummary(string documentTitle, string title, JObject changes, JArray failures, string previewDescription) {
            var summary = new StringBuilder();
            summary.AppendLine("Document: " + documentTitle);
            summary.AppendLine(string.Format(
                "Added: {0}   Modified: {1}   Deleted: {2}",
                changes.Value<int>("added_count"),
                changes.Value<int>("modified_count"),
                changes.Value<int>("deleted_count")));
            summary.AppendLine("Operation: " + title);

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

        /// <summary>
        /// Turns the isolation off again.
        /// </summary>
        /// <exception cref="Exception">
        /// Revit refused the transaction. The caller must not keep the run then: assimilating the
        /// group would put the isolation into the user's undo entry and leave the view isolated.
        /// </exception>
        public void End() {
            if (view == null)
                return;
            using (var transaction = new Transaction(doc, TransactionName)) {
                transaction.Start();
                view.DisableTemporaryViewMode(TemporaryViewMode.TemporaryHideIsolate);
                if (transaction.Commit() != TransactionStatus.Committed)
                    throw new InvalidOperationException("Revit did not end the approval preview's temporary isolation.");
            }
        }
    }
}
