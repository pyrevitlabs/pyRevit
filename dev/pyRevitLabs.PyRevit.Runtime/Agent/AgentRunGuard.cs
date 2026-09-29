using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Wraps one agent run in a <see cref="TransactionGroup"/> per open document and watches
    /// every document while the script runs.
    /// </summary>
    /// <remarks>
    /// While armed, the guard:
    /// <list type="bullet">
    /// <item>records added, modified and deleted element ids from <c>DocumentChanged</c>, for the
    /// active document and, separately, for every other document;</item>
    /// <item>holds a group on every other open, editable, non-linked document, so changes a
    /// script makes there through <c>app.Documents</c> can be rolled back;</item>
    /// <item>records failure messages, deletes warnings, and rolls back pending transactions that
    /// have errors, in every non-linked document, so a failure in a family or a new document
    /// fails the run with Revit's message instead of raising a dialog;</item>
    /// <item>closes Revit dialogs instead of letting them block the main thread;</item>
    /// <item>cancels synchronize requests, and saving, saving as or closing any document that was
    /// open when the run started. A document the script opened or created itself, such as a
    /// family from <c>EditFamily</c> or a new project, may be saved and closed.</item>
    /// </list>
    /// Invariant: only the active document's group may ever be assimilated. The groups on other
    /// documents are always rolled back, so a run can never keep a change outside the document
    /// the user sees and approves.
    /// Invariant: every group must be closed before the ExternalEvent callback returns;
    /// Revit doesn't allow an open group to outlive the callback. <see cref="Dispose"/> rolls back
    /// anything still open and always unsubscribes every handler.
    /// Documents the script opens during the run have no group; their changes are only reported.
    /// </remarks>
    internal sealed class AgentRunGuard : IDisposable {
        private const int MaxRecordedEntries = 200;

        private readonly UIApplication uiApp;
        private readonly Application app;
        private readonly Document doc;
        private readonly AgentChangeSet changes = new AgentChangeSet();
        private readonly JArray failures = new JArray();
        private readonly JArray blocked = new JArray();
        private readonly List<AgentOtherDocument> others = new List<AgentOtherDocument>();
        private readonly List<Document> openAtStart = new List<Document>();
        private TransactionGroup group;
        private bool documentEventsArmed;
        private AgentDialogCapture dialogCapture;

        public AgentRunGuard(UIApplication uiApp, Document doc) {
            this.uiApp = uiApp;
            app = uiApp.Application;
            this.doc = doc;
        }

        public AgentChangeSet Changes => changes;
        public JArray Failures => failures;
        public JArray Dialogs => dialogCapture?.Dialogs ?? new JArray();
        public JArray Blocked => blocked;
        public bool HasOpenGroup => group != null && group.HasStarted() && !group.HasEnded();

        /// <summary>
        /// True when the script changed a document that was already open when the run started.
        /// Those changes are outside what the run may keep, so the run must fail.
        /// </summary>
        public bool ChangedOtherOpenDocument => others.Any(other => !other.OpenedDuringRun && !other.Changes.IsEmpty);

        public bool LeftTransactionOpenInOtherDocument => others.Any(other => other.HasOpenTransaction);

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

            dialogCapture = new AgentDialogCapture(uiApp);

            foreach (Document other in app.Documents) {
                openAtStart.Add(other);
                if (other.IsLinked || IsWatchedDocument(other))
                    continue;
                var tracked = new AgentOtherDocument(other, openedDuringRun: false);
                tracked.StartGroup(groupName);
                others.Add(tracked);
            }

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
            dialogCapture?.Disarm();
        }

        public void RollBack() {
            if (HasOpenGroup)
                group.RollBack();
            RollBackOtherDocuments();
        }

        public void Assimilate() {
            if (HasOpenGroup)
                group.Assimilate();
            RollBackOtherDocuments();
        }

        /// <summary>
        /// Describes every other document the script changed. Call it before rolling back.
        /// </summary>
        public JArray DescribeOtherDocuments() {
            return new JArray(others.Where(other => !other.Changes.IsEmpty).Select(other => other.Describe()));
        }

        private void RollBackOtherDocuments() {
            foreach (var other in others)
                other.RollBack();
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
                foreach (var other in others)
                    other.Dispose();
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
            var changed = e.GetDocument();
            if (IsWatchedDocument(changed))
                changes.Record(e);
            else if (changed != null)
                TrackOther(changed).Changes.Record(e);
        }

        private AgentOtherDocument TrackOther(Document other) {
            var tracked = others.FirstOrDefault(candidate => candidate.Document.Equals(other));
            if (tracked == null) {
                tracked = new AgentOtherDocument(other, openedDuringRun: true);
                others.Add(tracked);
            }
            return tracked;
        }

        private void OnFailuresProcessing(object sender, FailuresProcessingEventArgs e) {
            var accessor = e.GetFailuresAccessor();
            var failing = accessor.GetDocument();
            if (failing == null || failing.IsLinked)
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
                        ["document"] = failing.Title,
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

        private void OnDocumentSaving(object sender, DocumentSavingEventArgs e) {
            if (WasOpenAtStart(e.Document))
                Block(e, e.Document, "save");
        }

        private void OnDocumentSavingAs(object sender, DocumentSavingAsEventArgs e) {
            if (WasOpenAtStart(e.Document))
                Block(e, e.Document, "save_as");
        }

        private void OnDocumentClosing(object sender, DocumentClosingEventArgs e) {
            if (WasOpenAtStart(e.Document))
                Block(e, e.Document, "close");
        }

        private bool WasOpenAtStart(Document target) {
            return target != null && openAtStart.Any(open => open.Equals(target));
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
    /// A document other than the active one, watched for the length of one agent run.
    /// </summary>
    /// <remarks>
    /// Invariant: <see cref="HasOpenTransaction"/> reports only a transaction the run left
    /// open. A document that already had one when tracking started, for example after an
    /// earlier failure, must not fail every later run.
    /// </remarks>
    internal sealed class AgentOtherDocument : IDisposable {
        private readonly bool modifiableAtStart;
        private TransactionGroup group;

        public AgentOtherDocument(Document document, bool openedDuringRun) {
            Document = document;
            OpenedDuringRun = openedDuringRun;
            Title = document.Title;
            modifiableAtStart = document.IsModifiable;
        }

        public Document Document { get; }
        public bool OpenedDuringRun { get; }
        public string Title { get; }
        public AgentChangeSet Changes { get; } = new AgentChangeSet();

        public bool HasOpenTransaction => !modifiableAtStart && Document.IsValidObject && Document.IsModifiable;

        private bool HasOpenGroup => group != null && group.HasStarted() && !group.HasEnded();

        /// <summary>
        /// Opens a group when the document can take one; a read-only document or one with a
        /// transaction already open is left unguarded.
        /// </summary>
        public void StartGroup(string groupName) {
            if (Document.IsReadOnly || Document.IsModifiable)
                return;
            try {
                group = new TransactionGroup(Document, groupName);
                group.Start();
            }
            catch (Exception) {
                group?.Dispose();
                group = null;
            }
        }

        public void RollBack() {
            if (HasOpenGroup)
                group.RollBack();
        }

        public JObject Describe() {
            var description = Changes.Summarize();
            description["document"] = Title;
            description["opened_during_run"] = OpenedDuringRun;
            description["rolled_back"] = group != null;
            return description;
        }

        public void Dispose() {
            try {
                RollBack();
            }
            catch (Exception) {
            }
            finally {
                group?.Dispose();
                group = null;
            }
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

        public ICollection<ElementId> Added => added.ToList();

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
            var description = Summarize();
            description["by_category"] = CountByCategory(doc);
            description["added"] = DescribeElements(doc, added, maxSamples);
            description["modified"] = DescribeElements(doc, modified, maxSamples);
            description["deleted"] = new JArray(deleted.Take(maxSamples).Select(AgentIds.ToValue));
            return description;
        }

        public JObject Summarize() {
            return new JObject {
                ["added_count"] = added.Count,
                ["modified_count"] = modified.Count,
                ["deleted_count"] = deleted.Count,
                ["transactions"] = new JArray(transactions.Distinct()),
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
