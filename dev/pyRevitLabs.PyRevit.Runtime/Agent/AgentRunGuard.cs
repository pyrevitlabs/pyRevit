using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Wraps one agent run in a <see cref="TransactionGroup"/> and watches the document while
    /// the script runs.
    /// </summary>
    /// <remarks>
    /// While armed, the guard:
    /// <list type="bullet">
    /// <item>records added, modified and deleted element ids from <c>DocumentChanged</c>;</item>
    /// <item>records failure messages, deletes warnings, and rolls back pending transactions that have errors;</item>
    /// <item>closes Revit dialogs instead of letting them block the main thread;</item>
    /// <item>cancels save, save-as, close and synchronize requests.</item>
    /// </list>
    /// Invariant: the group must be closed before the ExternalEvent callback returns;
    /// Revit doesn't allow an open group to outlive the callback. <see cref="Dispose"/> rolls back
    /// anything still open and always unsubscribes every handler.
    /// </remarks>
    internal sealed class AgentRunGuard : IDisposable {
        private const int MaxRecordedEntries = 200;

        private readonly UIApplication uiApp;
        private readonly Application app;
        private readonly Document doc;
        private readonly AgentChangeSet changes = new AgentChangeSet();
        private readonly JArray failures = new JArray();
        private readonly JArray dialogs = new JArray();
        private readonly JArray blocked = new JArray();
        private TransactionGroup group;
        private bool documentEventsArmed;
        private bool dialogCaptureArmed;

        public AgentRunGuard(UIApplication uiApp, Document doc) {
            this.uiApp = uiApp;
            app = uiApp.Application;
            this.doc = doc;
        }

        public AgentChangeSet Changes => changes;
        public JArray Failures => failures;
        public JArray Dialogs => dialogs;
        public JArray Blocked => blocked;
        public bool HasOpenGroup => group != null && group.HasStarted() && !group.HasEnded();

        /// <summary>
        /// Transactions Revit rolled back during the run because of error-level failures.
        /// The script's own Commit() still returns, so without this the run would look successful.
        /// </summary>
        public int ErrorRollbacks { get; private set; }
        public string FirstErrorDescription { get; private set; }

        public void Arm(string groupName) {
            app.DocumentChanged += OnDocumentChanged;
            app.FailuresProcessing += OnFailuresProcessing;
            app.DocumentSaving += OnDocumentSaving;
            app.DocumentSavingAs += OnDocumentSavingAs;
            app.DocumentClosing += OnDocumentClosing;
            app.DocumentSynchronizingWithCentral += OnDocumentSynchronizingWithCentral;
            documentEventsArmed = true;

            uiApp.DialogBoxShowing += OnDialogBoxShowing;
            dialogCaptureArmed = true;

            if (doc.IsReadOnly)
                return;

            group = new TransactionGroup(doc, groupName);
            group.Start();
        }

        /// <summary>
        /// Stops auto-closing dialogs, so the approval prompt shown by the host itself stays
        /// visible.
        /// </summary>
        public void DisarmDialogCapture() {
            if (!dialogCaptureArmed)
                return;
            uiApp.DialogBoxShowing -= OnDialogBoxShowing;
            dialogCaptureArmed = false;
        }

        public void RollBack() {
            if (HasOpenGroup)
                group.RollBack();
        }

        public void Assimilate() {
            if (HasOpenGroup)
                group.Assimilate();
        }

        public void Dispose() {
            try {
                if (HasOpenGroup)
                    group.RollBack();
            }
            catch (Exception) {
            }
            finally {
                group?.Dispose();
                group = null;
                DisarmDialogCapture();
                if (documentEventsArmed) {
                    app.DocumentChanged -= OnDocumentChanged;
                    app.FailuresProcessing -= OnFailuresProcessing;
                    app.DocumentSaving -= OnDocumentSaving;
                    app.DocumentSavingAs -= OnDocumentSavingAs;
                    app.DocumentClosing -= OnDocumentClosing;
                    app.DocumentSynchronizingWithCentral -= OnDocumentSynchronizingWithCentral;
                    documentEventsArmed = false;
                }
            }
        }

        private void OnDocumentChanged(object sender, DocumentChangedEventArgs e) {
            if (!IsWatchedDocument(e.GetDocument()))
                return;
            changes.Record(e);
        }

        private void OnFailuresProcessing(object sender, FailuresProcessingEventArgs e) {
            var accessor = e.GetFailuresAccessor();
            if (!IsWatchedDocument(accessor.GetDocument()))
                return;

            var hasErrors = false;
            foreach (var message in accessor.GetFailureMessages()) {
                var severity = message.GetSeverity();
                if (failures.Count < MaxRecordedEntries) {
                    failures.Add(new JObject {
                        ["severity"] = severity.ToString(),
                        ["description"] = message.GetDescriptionText(),
                        ["element_ids"] = new JArray(message.GetFailingElementIds().Select(AgentIds.ToValue)),
                        ["transaction"] = accessor.GetTransactionName(),
                    });
                }

                if (severity == FailureSeverity.Warning)
                    accessor.DeleteWarning(message);
                else {
                    hasErrors = true;
                    if (FirstErrorDescription == null)
                        FirstErrorDescription = message.GetDescriptionText();
                }
            }

            if (hasErrors)
                ErrorRollbacks++;

            e.SetProcessingResult(
                hasErrors ? FailureProcessingResult.ProceedWithRollBack : FailureProcessingResult.Continue);
        }

        private void OnDialogBoxShowing(object sender, DialogBoxShowingEventArgs e) {
            var entry = new JObject { ["dialog_id"] = e.DialogId };
            if (e is TaskDialogShowingEventArgs taskDialog)
                entry["message"] = taskDialog.Message;
            else if (e is MessageBoxShowingEventArgs messageBox)
                entry["message"] = messageBox.Message;

            entry["dismissed"] = TryDismiss(e);
            if (dialogs.Count < MaxRecordedEntries)
                dialogs.Add(entry);
        }

        private static bool TryDismiss(DialogBoxShowingEventArgs e) {
            foreach (var result in new[] { TaskDialogResult.Cancel, TaskDialogResult.Close, TaskDialogResult.Ok }) {
                try {
                    if (e.OverrideResult((int)result))
                        return true;
                }
                catch (Exception) {
                }
            }
            return false;
        }

        private void OnDocumentSaving(object sender, DocumentSavingEventArgs e) {
            Block(e, e.Document, "save");
        }

        private void OnDocumentSavingAs(object sender, DocumentSavingAsEventArgs e) {
            Block(e, e.Document, "save_as");
        }

        private void OnDocumentClosing(object sender, DocumentClosingEventArgs e) {
            Block(e, e.Document, "close");
        }

        private void OnDocumentSynchronizingWithCentral(object sender, DocumentSynchronizingWithCentralEventArgs e) {
            Block(e, e.Document, "synchronize_with_central");
        }

        private void Block(RevitAPIPreEventArgs e, Document target, string operation) {
            if (!e.Cancellable)
                return;
            e.Cancel();
            blocked.Add(new JObject {
                ["operation"] = operation,
                ["document"] = target?.Title,
            });
        }

        private bool IsWatchedDocument(Document other) {
            return other != null && other.Equals(doc);
        }
    }

    /// <summary>
    /// Element ids touched during one agent run, accumulated across every transaction the
    /// script commits inside the run's group.
    /// </summary>
    internal sealed class AgentChangeSet {
        private readonly HashSet<ElementId> added = new HashSet<ElementId>();
        private readonly HashSet<ElementId> modified = new HashSet<ElementId>();
        private readonly HashSet<ElementId> deleted = new HashSet<ElementId>();
        private readonly List<string> transactions = new List<string>();

        public bool IsEmpty => added.Count == 0 && modified.Count == 0 && deleted.Count == 0;

        public ICollection<ElementId> Touched =>
            added.Concat(modified).Distinct().ToList();

        public void Record(DocumentChangedEventArgs e) {
            foreach (var id in e.GetAddedElementIds())
                added.Add(id);
            foreach (var id in e.GetDeletedElementIds()) {
                if (!added.Remove(id))
                    deleted.Add(id);
                modified.Remove(id);
            }
            foreach (var id in e.GetModifiedElementIds())
                if (!added.Contains(id))
                    modified.Add(id);
            transactions.AddRange(e.GetTransactionNames());
        }

        /// <summary>
        /// Summarizes the change set. Must be called while the group is still open, because
        /// added and modified elements no longer exist in their changed form after a rollback.
        /// </summary>
        public JObject Describe(Document doc, int maxSamples) {
            return new JObject {
                ["added_count"] = added.Count,
                ["modified_count"] = modified.Count,
                ["deleted_count"] = deleted.Count,
                ["transactions"] = new JArray(transactions.Distinct()),
                ["by_category"] = CountByCategory(doc),
                ["added"] = DescribeElements(doc, added, maxSamples),
                ["modified"] = DescribeElements(doc, modified, maxSamples),
                ["deleted"] = new JArray(deleted.Take(maxSamples).Select(AgentIds.ToValue)),
            };
        }

        private JObject CountByCategory(Document doc) {
            var counts = new SortedDictionary<string, int>();
            foreach (var id in added.Concat(modified)) {
                var category = doc.GetElement(id)?.Category?.Name ?? "(no category)";
                counts[category] = counts.TryGetValue(category, out var count) ? count + 1 : 1;
            }
            var result = new JObject();
            foreach (var pair in counts)
                result[pair.Key] = pair.Value;
            return result;
        }

        private static JArray DescribeElements(Document doc, IEnumerable<ElementId> ids, int maxSamples) {
            var described = new JArray();
            foreach (var id in ids.Take(maxSamples)) {
                var element = doc.GetElement(id);
                described.Add(new JObject {
                    ["id"] = AgentIds.ToValue(id),
                    ["category"] = element?.Category?.Name,
                    ["name"] = SafeName(element),
                    ["class"] = element?.GetType().Name,
                });
            }
            return described;
        }

        private static string SafeName(Element element) {
            if (element == null)
                return null;
            try {
                return element.Name;
            }
            catch (Exception) {
                return null;
            }
        }
    }
}
