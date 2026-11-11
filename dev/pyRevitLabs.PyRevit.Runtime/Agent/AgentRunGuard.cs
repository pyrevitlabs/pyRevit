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
    /// Invariant: only the active document's group may ever be assimilated. The groups on other
    /// documents are always rolled back, so a run can never keep a change outside the document
    /// the user sees and approves.
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
        private readonly List<Document> openAtStart;
        private readonly List<Document> documentsCreatedDuringRun = new List<Document>();
        private readonly List<Document> documentsOpenedFromDisk = new List<Document>();
        private TransactionGroup group;
        private bool assimilationRequested;
        private bool documentEventsArmed;
        private AgentDialogCapture dialogCapture;

        public AgentRunGuard(UIApplication uiApp, Document doc) {
            this.uiApp = uiApp;
            app = uiApp.Application;
            this.doc = doc;
            openAtStart = AgentDocuments.Snapshot(app);
        }

        /// <summary>
        /// The documents open when the guard was created, before anything was armed, so the
        /// host can tell which background documents the run left behind even when arming failed.
        /// </summary>
        public IReadOnlyCollection<Document> OpenAtStart => openAtStart;

        public AgentChangeSet Changes => changes;
        public JArray Failures => failures;
        public JArray Dialogs => dialogCapture?.Dialogs ?? new JArray();
        public JArray Blocked => blocked;

        public List<string> CleanupFailures { get; } = new List<string>();
        public bool HasOpenGroup => group != null && group.HasStarted() && !group.HasEnded();

        /// <summary>
        /// True once the active document's group was assimilated, so its changes are kept.
        /// </summary>
        public bool Committed { get; private set; }

        /// <summary>
        /// True when rolling back the active document's group threw, did not report it rolled
        /// back, or left the model different from before the run (an element the run deleted is
        /// still missing, or one it added is still there), so the run's changes may still be in
        /// the model.
        /// </summary>
        /// <remarks>
        /// The model is checked even when the group already ended before the rollback was
        /// requested, unless the run asked to keep its changes.
        /// </remarks>
        public bool RollbackFailed { get; private set; }

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
            app.FileExporting += OnFileExporting;
            app.ViewExporting += OnViewExporting;
            app.DocumentPrinting += OnDocumentPrinting;
            app.DocumentCreated += OnDocumentCreated;
            app.DocumentOpened += OnDocumentOpened;
            app.DocumentClosing += OnDocumentClosing;
            app.DocumentSynchronizingWithCentral += OnDocumentSynchronizingWithCentral;
            documentEventsArmed = true;

            dialogCapture = new AgentDialogCapture(uiApp);

            foreach (var other in openAtStart) {
                if (other.IsLinked || IsWatchedDocument(other))
                    continue;
                var tracked = new AgentOtherDocument(other, openedDuringRun: false);
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
                if (HasOpenGroup) {
                    if (group.RollBack() != TransactionStatus.RolledBack || changes.LeavesTracesAfterRollback(doc))
                        RollbackFailed = true;
                }
                else if (group != null && !assimilationRequested && changes.LeavesTracesAfterRollback(doc))
                    RollbackFailed = true;
            }
            catch (Exception) {
                RollbackFailed = true;
                throw;
            }
        }

        public void Assimilate() {
            RollBackOtherDocuments();
            if (HasOpenGroup) {
                group.Assimilate();
                Committed = true;
            }
            assimilationRequested = true;
        }

        /// <summary>
        /// Describes every other document the script changed, with confirmed rollback and
        /// discard outcomes. Refresh after disposing the guard and closing leftovers.
        /// </summary>
        public JArray DescribeOtherDocuments() {
            return new JArray(others.Where(other => !other.Changes.IsEmpty).Select(other => other.Describe()));
        }

        public bool HasUnrevertedOtherDocumentChanges => others.Any(other =>
            !other.OpenedDuringRun && !other.Changes.IsEmpty && !other.ChangesReverted);

        private void RollBackOtherDocuments() {
            var errors = new List<Exception>();
            foreach (var other in others) {
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
            var tracked = others.FirstOrDefault(candidate => IsSameDocument(candidate.Document, other));
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
            var tracked = others.FirstOrDefault(candidate => IsSameDocument(candidate.Document, opened));
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
                || documentsCreatedDuringRun.Any(created => IsSameDocument(created, target))
                || documentsOpenedFromDisk.Any(opened => IsSameDocument(opened, target));
        }

        private void OnDocumentClosing(object sender, DocumentClosingEventArgs e) {
            if (WasOpenAtStart(e.Document))
                Block(e, e.Document, "close");
        }

        private static bool IsSameDocument(Document first, Document second) {
            if (first != null && ReferenceEquals(first, second))
                return true;
            try {
                return first != null && second != null && first.IsValidObject && second.IsValidObject && first.Equals(second);
            }
            catch (Exception) {
                return false;
            }
        }

        private bool WasOpenAtStart(Document target) {
            return openAtStart.Any(open => IsSameDocument(open, target));
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
            return "operation_blocked: " + string.Join(", ", operations) + " not allowed in agent runs; the user must do it in Revit.";
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
            return IsSameDocument(other, doc);
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
                    rolledBack = group.RollBack() == TransactionStatus.RolledBack && !Changes.LeavesTracesAfterRollback(Document);
            }
            catch (Exception) {
                if (Document.IsValidObject)
                    throw;
            }
        }

        public JObject Describe() {
            var description = Changes.Summarize();
            description["document"] = Title;
            description["opened_during_run"] = OpenedDuringRun;
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

        /// <summary>
        /// True when, after a rollback, an element the run deleted is still missing from
        /// <paramref name="document"/> or an element it added is still there.
        /// </summary>
        /// <remarks>
        /// Warning: a group's <c>RollBack()</c> status cannot prove the rollback worked. A
        /// committed transaction that borrows elements from a central model flushes Revit's
        /// undo stack while the group is open; the group then still reports
        /// <c>RolledBack</c> and the run's changes stay in the model. Call it only after the
        /// rollback, and only for a document the change set was recorded from.
        /// <para>
        /// Warning: modified elements are not verified. The run records no state from before
        /// it, so a modification that survives a flushed undo stack is invisible here unless
        /// the run also added or deleted an element.
        /// </para>
        /// </remarks>
        public bool LeavesTracesAfterRollback(Document document) {
            return deleted.Any(id => document.GetElement(id) == null)
                || added.Any(id => document.GetElement(id) != null);
        }

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
        /// <c>added_families</c> lists loaded families and every added type, system types such
        /// as <c>WallType</c> included, found among all added elements, not only the first
        /// <paramref name="maxSamples"/>, so a family load stays reviewable when regeneration
        /// adds many other elements. Families come first, then their types, then system types,
        /// so new system types can't push a loaded family past the cap.
        /// <para>
        /// <c>summary</c> is one line built from every change, not only the samples, for
        /// example <c>added 1 family (Door) with 3 types and 2 other elements (Legend
        /// Components), modified 1 element (Project Information), deleted 1 element</c>.
        /// </para>
        /// </remarks>
        public JObject Describe(Document doc, int maxSamples) {
            var description = Summarize();
            description["summary"] = DescribeInOneLine(doc);
            description["by_category"] = CountByCategory(doc);
            description["added"] = DescribeElements(doc, added, maxSamples);
            description["added_families"] = DescribeElements(doc, FamiliesAndTypes(doc), maxSamples);
            description["modified"] = DescribeElements(doc, modified, maxSamples);
            description["deleted"] = new JArray(deleted.Take(maxSamples).Select(AgentIds.ToValue));
            return description;
        }

        public JObject Summarize() {
            return new JObject {
                ["added_count"] = added.Count,
                ["modified_count"] = modified.Count,
                ["deleted_count"] = deleted.Count,
                ["summary"] = DescribeInOneLine(null),
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

        private IEnumerable<ElementId> FamiliesAndTypes(Document doc) {
            return added
                .Select(id => new { Id = id, Rank = FamilyRank(doc.GetElement(id)) })
                .Where(entry => entry.Rank >= 0)
                .OrderBy(entry => entry.Rank)
                .Select(entry => entry.Id);
        }

        private static int FamilyRank(Element element) {
            if (element is Family)
                return 0;
            if (element is FamilySymbol)
                return 1;
            return element is ElementType ? 2 : -1;
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

        private const int MaxSummaryNames = 3;

        private string DescribeInOneLine(Document doc) {
            var parts = new List<string>();
            if (added.Count > 0)
                parts.Add("added " + DescribeAdded(doc));
            if (modified.Count > 0)
                parts.Add("modified " + Count(modified.Count, "element") + (doc == null ? string.Empty : CategoryNames(modified.Select(id => doc.GetElement(id)))));
            if (deleted.Count > 0)
                parts.Add("deleted " + Count(deleted.Count, "element"));
            return parts.Count > 0 ? string.Join(", ", parts) : "no changes";
        }

        private string DescribeAdded(Document doc) {
            if (doc == null)
                return Count(added.Count, "element");
            var elements = added.Select(id => doc.GetElement(id)).ToList();
            var families = elements.Where(element => FamilyRank(element) == 0).ToList();
            var familyTypes = elements.Count(element => FamilyRank(element) == 1);
            var systemTypes = elements.Count(element => FamilyRank(element) == 2);
            var others = elements.Where(element => FamilyRank(element) < 0).ToList();

            var phrases = new List<string>();
            if (families.Count > 0) {
                var phrase = (families.Count == 1 ? "1 family" : families.Count + " families")
                    + " (" + ListNames(families.Select(family => SafeName(family) ?? "?")) + ")";
                if (familyTypes > 0)
                    phrase += " with " + Count(familyTypes, "type");
                phrases.Add(phrase);
            }
            else if (familyTypes > 0)
                phrases.Add(Count(familyTypes, "family type"));
            if (systemTypes > 0)
                phrases.Add(Count(systemTypes, "system type"));
            if (others.Count > 0)
                phrases.Add(Count(others.Count, phrases.Count > 0 ? "other element" : "element") + CategoryNames(others));
            return phrases.Count == 1
                ? phrases[0]
                : string.Join(", ", phrases.Take(phrases.Count - 1)) + " and " + phrases[phrases.Count - 1];
        }

        private static string CategoryNames(IEnumerable<Element> elements) {
            var names = elements
                .Select(element => element?.Category?.Name)
                .Where(name => !string.IsNullOrEmpty(name))
                .GroupBy(name => name)
                .OrderByDescending(group => group.Count())
                .ThenBy(group => group.Key, StringComparer.Ordinal)
                .Select(group => group.Key)
                .ToList();
            return names.Count > 0 ? " (" + ListNames(names) + ")" : string.Empty;
        }

        private static string ListNames(IEnumerable<string> names) {
            var all = names.ToList();
            var listed = string.Join(", ", all.Take(MaxSummaryNames));
            return all.Count > MaxSummaryNames ? listed + ", +" + (all.Count - MaxSummaryNames) + " more" : listed;
        }

        private static string Count(int count, string noun) {
            return count + " " + noun + (count == 1 ? string.Empty : "s");
        }
    }
}
