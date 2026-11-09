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
    /// <item>cancels synchronize, save, save-as, file-export, view-export and print operations while
    /// armed when Revit marks their event cancellable. It cancels closing only for documents
    /// that were open when the run started.</item>
    /// </list>
    /// Invariant: only the groups of the run's document and of the other documents in the agent
    /// session may be assimilated, and only when the run is kept. The groups on documents outside
    /// the session are always rolled back, so a run can never keep a change in a document the
    /// user didn't let agents work in.
    /// Invariant: every group must be closed before the ExternalEvent callback returns;
    /// Revit doesn't allow an open group to outlive the callback. <see cref="Dispose"/> rolls back
    /// anything still open and always unsubscribes every handler.
    /// A project or family the script opens from disk during the run counts as a document that
    /// was already open: changing it fails the run. It gets no group, so the script can still
    /// close it; its changes are discarded when it is closed without saving, by the script or by
    /// the host when the run ends. Documents created during a run are also never saved while the
    /// guard is armed, so an unapproved run cannot persist them to disk.
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
        private readonly List<Document> documentsCreatedDuringRun = new List<Document>();
        private readonly List<Document> documentsOpenedFromDisk = new List<Document>();
        private readonly Func<Document, bool> inSession;
        private TransactionGroup group;
        private bool documentEventsArmed;
        private AgentDialogCapture dialogCapture;

        /// <param name="inSession">
        /// Whether an open document is in the agent session, so the run may change it and keep the
        /// change with its own. Null lets the run keep changes to its own document only.
        /// </param>
        public AgentRunGuard(UIApplication uiApp, Document doc, Func<Document, bool> inSession = null) {
            this.uiApp = uiApp;
            app = uiApp.Application;
            this.doc = doc;
            this.inSession = inSession;
        }

        public AgentChangeSet Changes => changes;
        public JArray Failures => failures;
        public JArray Dialogs => dialogCapture?.Dialogs ?? new JArray();
        public JArray Blocked => blocked;

        public List<string> CleanupFailures { get; } = new List<string>();
        public bool HasOpenGroup => group != null && group.HasStarted() && !group.HasEnded();

        /// <summary>
        /// True once the run was kept: its own document's group, or another session document's,
        /// was assimilated.
        /// </summary>
        public bool Committed { get; private set; }

        /// <summary>
        /// True when rolling back the group of the document the run works in threw or did not
        /// report it rolled back, so the run's changes may still be in that model.
        /// </summary>
        public bool RollbackFailed { get; private set; }

        /// <summary>
        /// True when the script changed a document outside the agent session that was already open
        /// when the run started. Those changes are outside what the run may keep, so the run must
        /// fail.
        /// </summary>
        public bool ChangedOtherOpenDocument => ChangedOutsideSession.Any();

        /// <summary>
        /// Titles of the documents that make <see cref="ChangedOtherOpenDocument"/> true; never
        /// documents the run created.
        /// </summary>
        public IList<string> ChangedOtherOpenDocumentTitles => ChangedOutsideSession.Select(other => other.Title).ToList();

        /// <summary>
        /// The other documents in the session the script changed; their changes are kept with the
        /// run's own.
        /// </summary>
        public IList<AgentOtherDocument> ChangedSessionDocuments => others.Where(IsKeepable).ToList();

        /// <summary>
        /// Whether the script changed anything the run may keep: its own document, or another one
        /// in the session.
        /// </summary>
        public bool HasChanges => !changes.IsEmpty || others.Any(IsKeepable);

        /// <summary>
        /// Session documents whose changes Revit wouldn't keep after <see cref="Assimilate"/> kept
        /// others; each was rolled back and says why in <see cref="AgentOtherDocument.KeepError"/>.
        /// </summary>
        public IList<AgentOtherDocument> NotKept => others.Where(other => other.KeepError != null).ToList();

        private IEnumerable<AgentOtherDocument> ChangedOutsideSession =>
            others.Where(other => !other.OpenedDuringRun && !other.InSession && !other.Changes.IsEmpty);

        private static bool IsKeepable(AgentOtherDocument other) {
            return other.InSession && !other.Changes.IsEmpty;
        }

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
            app.FileExporting += OnFileExporting;
            app.ViewExporting += OnViewExporting;
            app.DocumentPrinting += OnDocumentPrinting;
            app.DocumentCreated += OnDocumentCreated;
            app.DocumentOpened += OnDocumentOpened;
            app.DocumentClosing += OnDocumentClosing;
            app.DocumentSynchronizingWithCentral += OnDocumentSynchronizingWithCentral;
            documentEventsArmed = true;

            dialogCapture = new AgentDialogCapture(uiApp);

            foreach (Document other in app.Documents) {
                openAtStart.Add(other);
                if (other.IsLinked || IsWatchedDocument(other))
                    continue;
                var tracked = new AgentOtherDocument(other, openedDuringRun: false) {
                    InSession = inSession?.Invoke(other) == true,
                };
                tracked.StartGroup(groupName);
                others.Add(tracked);
            }

            if (doc == null || doc.IsReadOnly)
                return;

            group = new TransactionGroup(doc, groupName);
            if (group.Start() != TransactionStatus.Started)
                throw new InvalidOperationException(
                    "Revit did not start the run's transaction group on the active document, so the run could not be rolled back; the script was not run.");
        }

        private void DisarmDialogCapture() {
            dialogCapture?.Disarm();
        }

        public void RollBack() {
            try {
                RollBackGroup();
            }
            finally {
                RollBackOtherDocuments();
            }
        }

        private void RollBackGroup() {
            try {
                if (HasOpenGroup && group.RollBack() != TransactionStatus.RolledBack)
                    RollbackFailed = true;
            }
            catch (Exception) {
                RollbackFailed = true;
                throw;
            }
        }

        /// <summary>
        /// Keeps the run: rolls back every document outside the session, then keeps the run's own
        /// document and each other session document it changed, as one undo entry in each.
        /// </summary>
        /// <remarks>
        /// Revit can't keep several documents at once. A session document that fails to keep after
        /// others were kept is rolled back and listed in <see cref="NotKept"/>, so the run can report
        /// the partial result. A failure to roll back a document outside the session throws before
        /// anything is kept.
        /// </remarks>
        public void Assimilate() {
            RollBackOtherDocuments(other => !IsKeepable(other));
            if (HasOpenGroup) {
                group.Assimilate();
                Committed = true;
            }
            foreach (var other in others.Where(IsKeepable)) {
                other.Keep();
                if (other.Kept)
                    Committed = true;
            }
        }

        /// <summary>
        /// Describes every other document the script changed, with confirmed rollback and
        /// discard outcomes. Refresh after disposing the guard and closing leftovers.
        /// </summary>
        public JArray DescribeOtherDocuments() {
            return new JArray(others.Where(other => !other.Changes.IsEmpty).Select(other => other.Describe()));
        }

        public bool HasUnrevertedOtherDocumentChanges => others.Any(other =>
            !other.OpenedDuringRun && !other.Changes.IsEmpty && !other.ChangesReverted && !other.Kept);

        private void RollBackOtherDocuments(Func<AgentOtherDocument, bool> which = null) {
            var errors = new List<Exception>();
            foreach (var other in others.Where(which ?? (_ => true))) {
                try {
                    other.RollBack();
                }
                catch (Exception ex) {
                    errors.Add(ex);
                }
            }
            if (errors.Count > 0)
                throw new AggregateException("Could not roll back other documents.", errors);
        }

        public void Dispose() {
            try {
                RollBackGroup();
            }
            catch (Exception ex) {
                CleanupFailures.Add("Rolling back the run failed: " + ex.Message);
            }
            finally {
                TryCleanup(() => group?.Dispose());
                group = null;
                foreach (var other in others)
                    TryCleanup(other.Dispose);
                TryCleanup(DisarmDialogCapture);
                if (documentEventsArmed) {
                    app.DocumentChanged -= OnDocumentChanged;
                    app.FailuresProcessing -= OnFailuresProcessing;
                    app.DocumentSaving -= OnDocumentSaving;
                    app.DocumentSavingAs -= OnDocumentSavingAs;
                    app.FileExporting -= OnFileExporting;
                    app.ViewExporting -= OnViewExporting;
                    app.DocumentPrinting -= OnDocumentPrinting;
                    app.DocumentCreated -= OnDocumentCreated;
                    app.DocumentOpened -= OnDocumentOpened;
                    app.DocumentClosing -= OnDocumentClosing;
                    app.DocumentSynchronizingWithCentral -= OnDocumentSynchronizingWithCentral;
                    documentEventsArmed = false;
                }
            }
        }

        private void TryCleanup(Action cleanup) {
            try {
                cleanup();
            }
            catch (Exception ex) {
                CleanupFailures.Add(ex.Message);
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
            var tracked = others.FirstOrDefault(candidate => AgentDocuments.IsSame(candidate.Document, other));
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

        private void OnDocumentCreated(object sender, DocumentCreatedEventArgs e) {
            var created = e.Document;
            if (created == null || created.IsLinked)
                return;
            documentsCreatedDuringRun.Add(created);
            if (IsWatchedDocument(created))
                return;
            others.Add(new AgentOtherDocument(created, openedDuringRun: true));
        }

        private void OnDocumentOpened(object sender, DocumentOpenedEventArgs e) {
            var opened = e.Document;
            if (opened == null || opened.IsLinked)
                return;
            documentsOpenedFromDisk.Add(opened);
            if (IsWatchedDocument(opened))
                return;
            var tracked = others.FirstOrDefault(candidate => AgentDocuments.IsSame(candidate.Document, opened));
            if (tracked != null)
                tracked.MarkOpenedFromDisk();
            else
                others.Add(new AgentOtherDocument(opened, openedDuringRun: false, openedFromDisk: true));
        }

        private void OnDocumentSaving(object sender, DocumentSavingEventArgs e) {
            if (IsProtectedFromSave(e.Document))
                Block(e, e.Document, "save");
        }

        private void OnDocumentSavingAs(object sender, DocumentSavingAsEventArgs e) {
            if (IsProtectedFromSave(e.Document))
                Block(e, e.Document, "save_as");
        }

        private void OnFileExporting(object sender, FileExportingEventArgs e) {
            Block(e, null, "file_export");
        }

        private void OnViewExporting(object sender, ViewExportingEventArgs e) {
            Block(e, null, "view_export");
        }

        private void OnDocumentPrinting(object sender, DocumentPrintingEventArgs e) {
            Block(e, e.Document, "print");
        }

        private bool IsProtectedFromSave(Document target) {
            return WasOpenAtStart(target)
                || documentsCreatedDuringRun.Any(created => AgentDocuments.IsSame(created, target))
                || documentsOpenedFromDisk.Any(opened => AgentDocuments.IsSame(opened, target));
        }

        private void OnDocumentClosing(object sender, DocumentClosingEventArgs e) {
            if (WasOpenAtStart(e.Document))
                Block(e, e.Document, "close");
        }

        private bool WasOpenAtStart(Document target) {
            return openAtStart.Any(open => AgentDocuments.IsSame(open, target));
        }

        private void OnDocumentSynchronizingWithCentral(object sender, DocumentSynchronizingWithCentralEventArgs e) {
            Block(e, e.Document, "synchronize_with_central");
        }

        /// <summary>
        /// Explains each cancelled operation, or returns null when none was cancelled. Revit
        /// reports a cancelled save only as a generic failure, so this ties it to the guard.
        /// Operations the guard could not cancel are not recorded and not described.
        /// </summary>
        public string DescribeBlockedOperations() {
            if (blocked.Count == 0)
                return null;
            var operations = blocked.Select(DescribeBlockedOperation).Distinct();
            return "operation_blocked: " + string.Join(", ", operations) + " not allowed in agent runs.";
        }

        private static string DescribeBlockedOperation(JToken entry) {
            var operation = entry.Value<string>("operation");
            var document = entry.Value<string>("document");
            return document == null ? operation : $"{operation} of '{document}'";
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
            return AgentDocuments.IsSame(other, doc);
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
        private bool openedFromDisk;
        private bool rolledBack;
        private TransactionGroup group;

        public AgentOtherDocument(Document document, bool openedDuringRun, bool openedFromDisk = false) {
            Document = document;
            OpenedDuringRun = openedDuringRun;
            this.openedFromDisk = openedFromDisk;
            Title = document.Title;
            modifiableAtStart = document.IsModifiable;
        }

        public Document Document { get; }
        public bool OpenedDuringRun { get; private set; }
        public string Title { get; }
        public AgentChangeSet Changes { get; } = new AgentChangeSet();

        /// <summary>Whether the agent session holds the document, so the run may keep its changes.</summary>
        public bool InSession { get; set; }

        /// <summary>Whether the run's changes in the document were kept.</summary>
        public bool Kept { get; private set; }

        /// <summary>Why Revit wouldn't keep the run's changes in the document, or null.</summary>
        public string KeepError { get; private set; }

        public bool HasOpenTransaction => !modifiableAtStart && Document.IsValidObject && Document.IsModifiable;

        private bool HasOpenGroup => group != null && group.HasStarted() && !group.HasEnded();

        public bool ChangesReverted => rolledBack || (openedFromDisk && !Document.IsValidObject);

        public void MarkOpenedFromDisk() {
            openedFromDisk = true;
            OpenedDuringRun = false;
        }

        /// <summary>
        /// Opens a group when the document can take one; a read-only document or one with a
        /// transaction already open is left unguarded.
        /// </summary>
        public void StartGroup(string groupName) {
            if (Document.IsReadOnly || Document.IsModifiable)
                return;
            try {
                group = new TransactionGroup(Document, groupName);
                if (group.Start() != TransactionStatus.Started) {
                    group.Dispose();
                    group = null;
                }
            }
            catch (Exception) {
                group?.Dispose();
                group = null;
            }
        }

        public void RollBack() {
            try {
                if (HasOpenGroup)
                    rolledBack = group.RollBack() == TransactionStatus.RolledBack;
            }
            catch (Exception) {
                if (Document.IsValidObject)
                    throw;
            }
        }

        /// <summary>
        /// Keeps the run's changes in the document as one undo entry. When Revit refuses, the
        /// changes are rolled back and <see cref="KeepError"/> says why. Without a group, which a
        /// document that couldn't take one at the start has, the changes are already in it.
        /// </summary>
        public void Keep() {
            if (!HasOpenGroup) {
                Kept = true;
                return;
            }
            try {
                group.Assimilate();
                Kept = true;
            }
            catch (Exception ex) {
                KeepError = ex.Message;
                try {
                    RollBack();
                }
                catch (Exception) {
                }
            }
        }

        public JObject Describe() {
            var description = Changes.Summarize();
            description["document"] = Title;
            description["opened_during_run"] = OpenedDuringRun;
            description["in_session"] = InSession;
            description["kept"] = Kept;
            if (KeepError != null)
                description["keep_error"] = KeepError;
            if (OpenedDuringRun)
                description["scope"] = "created during the run; not rolled back";
            else
                description["rolled_back"] = rolledBack;
            if (openedFromDisk)
                description["discarded_on_close"] = !Document.IsValidObject;
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
        /// <remarks>
        /// <c>added_families</c> lists loaded families and types found among all added
        /// elements, not only the first <paramref name="maxSamples"/>, so a family load stays
        /// reviewable when regeneration adds many other elements.
        /// </remarks>
        public JObject Describe(Document doc, int maxSamples) {
            var description = Summarize();
            description["by_category"] = CountByCategory(doc);
            description["added"] = DescribeElements(doc, added, maxSamples);
            description["added_families"] = DescribeElements(doc, added.Where(id => IsFamilyOrType(doc.GetElement(id))), maxSamples);
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

        private static bool IsFamilyOrType(Element element) {
            return element is Family || element is FamilySymbol;
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
