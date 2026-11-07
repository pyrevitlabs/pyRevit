using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;

using pyRevitLabs.Json.Linq;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// In-process controls of the agent session: the user's consent for agents to work in a set of
    /// documents, given in Revit, or given once for every document with
    /// <c>[agent] session_start = auto</c>.
    /// </summary>
    /// <remarks>
    /// Only code running inside Revit can start or resume a session, or add a document to it. The
    /// pipe can only request and pause one, and end one the user started, so an agent can't grant
    /// itself access by running the CLI. This guards against well-behaved agents acting unseen, not
    /// against a hostile script: any code inside Revit can call these methods too, except while an
    /// agent run executes.
    /// Session documents are held by reference and compared with <see cref="AgentDocuments.IsSame"/>,
    /// never by title or path. Closing one removes it, and closing the last ends the session.
    /// Saving one under another name changes its title. A session that started automatically
    /// takes in every document opened while it is open.
    /// </remarks>
    public static class AgentSessions {
        public const string StartUser = "user";
        public const string StartAuto = "auto";

        internal static readonly AgentSessionTracker Tracker = new AgentSessionTracker();

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object sync = new object();
        private static bool eventsAttached;
        private static Document closingDocument;
        private static int closingDocumentId;

        static AgentSessions() {
            Tracker.EndedWithOpenedDocuments += CloseOpenedDocuments;
        }

        /// <summary>
        /// Whether the first model request starts a session on every open document. Set from
        /// <c>[agent] session_start</c> each time pyRevit loads, so editing the config mid-session
        /// changes nothing until then.
        /// </summary>
        public static bool StartsAutomatically => Tracker.StartMode == AgentSessionStart.Auto;

        /// <summary>
        /// Sets how sessions start, <see cref="StartUser"/> or <see cref="StartAuto"/>, until
        /// pyRevit loads again.
        /// </summary>
        /// <exception cref="ArgumentException">Any other value.</exception>
        /// <exception cref="AgentException">
        /// <c>session_locked</c> when making sessions start automatically while an agent run executes.
        /// </exception>
        public static void SetSessionStart(string mode) {
            Tracker.SetStartMode(ParseStart(mode));
        }

        /// <summary>
        /// Starts a session on the active document.
        /// </summary>
        /// <returns>The new session's id.</returns>
        /// <exception cref="InvalidOperationException">Called off the Revit main thread.</exception>
        /// <exception cref="AgentException">
        /// <c>no_active_document</c>; <c>session_active</c> when a session is already active or
        /// paused; <c>session_locked</c> while an agent run executes.
        /// </exception>
        public static string Start(UIApplication app) {
            if (app == null)
                throw new ArgumentNullException(nameof(app));
            var doc = app.ActiveUIDocument?.Document
                ?? throw new AgentException("no_active_document", "Open the document the agent should work on, then start the session.");
            return Start(app, new[] { doc });
        }

        /// <summary>
        /// Starts a session on the documents the user chose in the panel, by their keys.
        /// </summary>
        /// <returns>The new session's id.</returns>
        /// <exception cref="InvalidOperationException">Called off the Revit main thread.</exception>
        /// <exception cref="AgentException">
        /// <c>no_active_document</c> when no key is given; <c>unknown_document</c> when one names
        /// no open document; <c>session_active</c> or <c>session_locked</c> as for
        /// <see cref="Start(UIApplication)"/>.
        /// </exception>
        internal static string Start(UIApplication app, IEnumerable<string> keys) {
            if (app == null)
                throw new ArgumentNullException(nameof(app));
            var chosen = (keys ?? Enumerable.Empty<string>()).Select(FindOpen).ToList();
            if (chosen.Count == 0)
                throw new AgentException("no_active_document", "Choose at least one document for the session.");
            return Start(app, chosen);
        }

        private static string Start(UIApplication app, IList<Document> chosen) {
            if (!ScriptExecutor.IsOnMainThread)
                throw new InvalidOperationException("Agent sessions must be started on the Revit main thread.");
            WatchDocuments(app.Application);
            AgentAwarenessWatch.Attach(app);
            var id = Tracker.Start(chosen.Select(SessionDocument), DateTime.UtcNow);
            AgentAwarenessWatch.Restart(app);
            return id;
        }

        /// <summary>
        /// Adds the active document to the open session, and the agent's next summary of changes
        /// reports it.
        /// </summary>
        /// <exception cref="InvalidOperationException">Called off the Revit main thread.</exception>
        /// <exception cref="AgentException">
        /// <c>no_active_document</c>; <c>already_in_session</c> when the session has the active
        /// document; <c>session_inactive</c> when there is no session; <c>session_locked</c> while an
        /// agent run executes.
        /// </exception>
        public static void Add(UIApplication app) {
            if (app == null)
                throw new ArgumentNullException(nameof(app));
            Add(app.ActiveUIDocument?.Document
                ?? throw new AgentException("no_active_document", "Open the document to add, then add it to the session."));
        }

        /// <summary>
        /// Adds the open document with <paramref name="key"/> to the open session, as
        /// <see cref="Add(UIApplication)"/> does for the active one.
        /// </summary>
        /// <exception cref="AgentException">
        /// <c>unknown_document</c> when the key names no open document, and the refusals of
        /// <see cref="Add(UIApplication)"/>.
        /// </exception>
        internal static void Add(string key) {
            Add(FindOpen(key));
        }

        private static void Add(Document doc) {
            if (!ScriptExecutor.IsOnMainThread)
                throw new InvalidOperationException("Documents must be added to agent sessions on the Revit main thread.");
            var added = SessionDocument(doc);
            if (Tracker.StartedAutomatically || !Tracker.AddDocument(added, byUser: true))
                throw new AgentException("already_in_session", $"'{doc.Title}' is already part of the agent session.");
            AgentAwarenessWatch.Awareness.RecordJoined(added.Key, added.Title);
            AgentHost.Activity.RecordAdded(added.Title, Tracker.CurrentSession, DateTime.UtcNow);
        }

        /// <summary>
        /// Takes a document the user chose out of the open session, and the agent's next summary of
        /// changes reports that it left.
        /// </summary>
        /// <exception cref="AgentException">The refusals of <see cref="AgentSessionTracker.RemoveDocumentByUser"/>.</exception>
        public static void Remove(string key) {
            var removed = Tracker.RemoveDocumentByUser(key);
            if (removed == null)
                return;
            AgentAwarenessWatch.Awareness.RecordLeft(removed.Key, removed.Title);
            AgentHost.Activity.RecordRemoved(removed.Title, Tracker.CurrentSession, DateTime.UtcNow);
        }

        /// <summary>
        /// Closes, without saving, a document an agent opened in the session. It leaves the session
        /// as any closed document does.
        /// </summary>
        /// <remarks>Must run in a Revit API context, as the panel's posted actions do.</remarks>
        /// <exception cref="AgentException">
        /// <c>unknown_document</c> when the session has no document an agent opened with that key;
        /// <c>wrong_document</c> while it is the active document, which Revit can't close.
        /// </exception>
        internal static void CloseOpenedDocument(UIApplication app, string key) {
            var entry = Tracker.Documents.FirstOrDefault(candidate => candidate.Key == key && candidate.OpenedByAgent);
            var doc = entry?.Document as Document;
            if (!IsOpen(doc))
                throw new AgentException("unknown_document", "That document is no longer open.");
            if (AgentDocuments.IsSame(app.ActiveUIDocument?.Document, doc))
                throw new AgentException("wrong_document",
                    $"'{entry.Title}' is the active document, which Revit can't close. Switch to another document first.");
            if (!doc.Close(false))
                throw new AgentException("not_run", $"Revit kept '{entry.Title}' open.");
        }

        /// <summary>
        /// Pauses the session. Called from an agent run's code, the pause counts as the agent's.
        /// </summary>
        /// <exception cref="AgentException"><c>session_inactive</c> when there is no session.</exception>
        public static void Pause() {
            Tracker.Pause();
        }

        /// <exception cref="AgentException">
        /// <c>session_inactive</c> when there is no session, or <c>session_locked</c> while an
        /// agent run executes.
        /// </exception>
        public static void Resume() {
            Tracker.Resume();
        }

        /// <exception cref="AgentException">
        /// <c>session_locked</c> while sessions start automatically: Pause is the way to stop agents then.
        /// </exception>
        public static void End() {
            Tracker.EndInRevit(DateTime.UtcNow);
        }

        /// <summary>
        /// Declines an agent's pending request for a session. Its next refusal tells it the user
        /// said no.
        /// </summary>
        public static void Decline() {
            Tracker.Decline(DateTime.UtcNow);
        }

        internal static JObject Describe() {
            return Tracker.Describe();
        }

        /// <exception cref="AgentException"><c>session_inactive</c> when there is no session.</exception>
        internal static void PauseByClient() {
            Tracker.PauseForAgent();
        }

        /// <exception cref="AgentException"><c>session_locked</c> while sessions start automatically.</exception>
        internal static void EndByClient() {
            Tracker.EndForAgent(DateTime.UtcNow);
        }

        /// <summary>
        /// Pauses a session the user started when the agent panel is hidden, whether the user closed
        /// it or Revit hid it, for example on its Home screen. The user resumes it in the panel. A
        /// session that started automatically carries on, so the panel can be opened to watch and
        /// closed again.
        /// </summary>
        internal static void PauseForPanelHidden() {
            if (Tracker.StartedAutomatically)
                return;
            Tracker.PauseByHost(AgentSessionPauseCauses.PanelHidden, "the agent panel in Revit was closed or hidden.");
        }

        /// <summary>
        /// Pauses the session after a run changed an open document outside it, so the agent can't carry
        /// on until the user has seen what happened and resumed it.
        /// </summary>
        /// <param name="documents">Titles of the documents that were open before the run and that it changed.</param>
        /// <returns>Whether the session is paused now: false when there is no session to pause.</returns>
        internal static bool PauseForOtherDocument(IEnumerable<string> documents) {
            var names = string.Join(", ", documents.Where(name => !string.IsNullOrEmpty(name)).Distinct().Select(name => "'" + name + "'"));
            Tracker.PauseByHost(
                AgentSessionPauseCauses.OtherDocument,
                $"the last run changed an open document outside the session ({names}), and a run may change only the session's documents.");
            return Tracker.State == AgentSessionState.Paused;
        }

        /// <summary>
        /// Whether the open session holds <paramref name="doc"/>, so a run may change it. A session
        /// that started automatically holds every open document.
        /// </summary>
        /// <remarks>Must run on the Revit main thread, because it compares documents.</remarks>
        internal static bool IsInSession(Document doc) {
            return Tracker.Contains(candidate => AgentDocuments.IsSame(candidate as Document, doc));
        }

        /// <summary>
        /// Keeps the documents a modify run opened or created in the open session, as the agent's.
        /// </summary>
        /// <returns>
        /// The kept documents' keys and titles, or null when there is no session to keep them in.
        /// </returns>
        /// <remarks>Must run on the Revit main thread, because it describes documents.</remarks>
        internal static JArray AdoptOpenedDocuments(IEnumerable<Document> opened) {
            var adopted = new JArray();
            foreach (var doc in opened) {
                var entry = SessionDocument(doc);
                if (!Tracker.AdoptOpenedDocument(entry))
                    return null;
                adopted.Add(new JObject { ["key"] = entry.Key, ["title"] = entry.Title });
            }
            return adopted;
        }

        internal static void EndForHostStop() {
            Tracker.End(AgentSessionEndReasons.HostStopped, DateTime.UtcNow);
        }

        /// <summary>
        /// Applies <c>[agent] session_start</c>. Called on every pyRevit load while the host is
        /// enabled.
        /// </summary>
        /// <remarks>
        /// A reload from inside an agent run can't make sessions start automatically. The refusal
        /// is logged and never thrown, so the rest of the host's configuration still runs.
        /// </remarks>
        internal static void Configure(Application app, string start) {
            WatchDocuments(app);
            try {
                Tracker.SetStartMode(ParseStart(start));
            }
            catch (AgentException ex) when (ex.Code == "session_locked") {
                logger.Warn("Agent sessions keep starting in the agent panel until pyRevit reloads outside an agent run: {0}", ex.Message);
            }
        }

        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>paused_by_agent</c> or <c>session_inactive</c>.
        /// </exception>
        internal static void CheckOnArrival() {
            Tracker.CheckOnArrival();
        }

        /// <summary>
        /// The gate when Revit picks a request up. Starts a session on every open document first
        /// when sessions start automatically and none is open, and forgets session documents that
        /// closed without Revit saying so.
        /// </summary>
        /// <remarks>Must run on the Revit main thread, because it compares documents.</remarks>
        /// <param name="target">The document the request names, or null when it names none.</param>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>paused_by_agent</c>, <c>session_inactive</c> or
        /// <c>document_not_in_session</c>.
        /// </exception>
        internal static void CheckOnDequeue(UIApplication app, Document target) {
            if (Tracker.StartMode == AgentSessionStart.Auto && Tracker.State == AgentSessionState.Inactive) {
                WatchDocuments(app.Application);
                AgentAwarenessWatch.Attach(app);
                if (Tracker.StartAutomatically(OpenDocuments(app.Application), DateTime.UtcNow))
                    AgentAwarenessWatch.Restart(app);
            }
            foreach (var closed in Tracker.Documents.Where(entry => !IsOpen(entry.Document as Document)))
                Leave(closed.Document as Document, closed);
            Tracker.CheckOnDequeue(candidate => AgentDocuments.IsSame(candidate as Document, target), target?.Title);
        }

        private static AgentSessionStart ParseStart(string mode) {
            switch ((mode ?? string.Empty).Trim().ToLowerInvariant()) {
                case StartUser:
                    return AgentSessionStart.User;
                case StartAuto:
                    return AgentSessionStart.Auto;
                default:
                    throw new ArgumentException($"Agent sessions start '{StartUser}' or '{StartAuto}', not '{mode}'.", nameof(mode));
            }
        }

        private static Document FindOpen(string key) {
            var doc = AgentDocuments.Keys.Find(key);
            if (doc == null || doc.IsLinked)
                throw new AgentException("unknown_document", "That document is no longer open. Choose again.");
            return doc;
        }

        private static AgentSessionDocument SessionDocument(Document doc) {
            return new AgentSessionDocument(doc, AgentDocuments.Keys.KeyOf(doc), doc.Title);
        }

        private static IEnumerable<AgentSessionDocument> OpenDocuments(Application app) {
            return app.Documents.Cast<Document>().Where(doc => !doc.IsLinked).Select(SessionDocument).ToList();
        }

        private static bool IsOpen(Document doc) {
            try {
                return doc != null && doc.IsValidObject;
            }
            catch (Exception) {
                return false;
            }
        }

        /// <remarks>
        /// Closing needs a Revit API context. On the main thread the caller is in one: the panel,
        /// a pyRevit command, or a request Revit picked up. A session ended from the pipe thread
        /// closes them through the dispatcher.
        /// </remarks>
        private static void CloseOpenedDocuments(IReadOnlyList<AgentSessionDocument> released) {
            if (ScriptExecutor.IsOnMainThread) {
                Close(released);
                return;
            }
            var dispatcher = AgentHost.Dispatcher;
            if (dispatcher == null) {
                logger.Warn("Could not close the documents agents opened, because the agent host is stopped: {0}",
                    string.Join(", ", released.Select(entry => entry.Title)));
                return;
            }
            if (!dispatcher.Post(_ => Close(released)))
                logger.Warn("Could not close the documents agents opened, because Revit refused the request: {0}",
                    string.Join(", ", released.Select(entry => entry.Title)));
        }

        private static void Close(IEnumerable<AgentSessionDocument> released) {
            foreach (var entry in released) {
                var doc = entry.Document as Document;
                if (!IsOpen(doc) || doc.IsLinked)
                    continue;
                try {
                    if (!doc.Close(false))
                        logger.Warn("Revit kept '{0}', which an agent opened, open after its session ended.", entry.Title);
                }
                catch (Exception ex) {
                    logger.Warn("Could not close '{0}', which an agent opened, after its session ended: {1}", entry.Title, ex.Message);
                }
            }
        }

        private static void Leave(Document closed, AgentSessionDocument entry) {
            var removed = Tracker.RemoveDocument(
                candidate => ReferenceEquals(candidate, closed), AgentSessionEndReasons.DocumentClosed, DateTime.UtcNow);
            if (removed != null)
                AgentAwarenessWatch.Awareness.RecordLeft(entry.Key, entry.Title);
        }

        private static void WatchDocuments(Application app) {
            lock (sync) {
                if (eventsAttached)
                    return;
                app.DocumentOpened += OnDocumentOpened;
                app.DocumentCreated += OnDocumentCreated;
                app.DocumentClosing += OnDocumentClosing;
                app.DocumentClosed += OnDocumentClosed;
                app.DocumentSavedAs += OnDocumentSavedAs;
                eventsAttached = true;
            }
        }

        private static void OnDocumentOpened(object sender, DocumentOpenedEventArgs e) {
            if (e.Status == RevitAPIEventStatus.Succeeded)
                JoinAutomaticSession(e.Document);
        }

        private static void OnDocumentCreated(object sender, DocumentCreatedEventArgs e) {
            if (e.Status == RevitAPIEventStatus.Succeeded)
                JoinAutomaticSession(e.Document);
        }

        private static void JoinAutomaticSession(Document doc) {
            if (doc == null || doc.IsLinked || !Tracker.StartedAutomatically)
                return;
            var joined = SessionDocument(doc);
            if (Tracker.AddDocument(joined, byUser: false))
                AgentAwarenessWatch.Awareness.RecordJoined(joined.Key, joined.Title);
        }

        private static void OnDocumentSavedAs(object sender, DocumentSavedAsEventArgs e) {
            if (e.Status != RevitAPIEventStatus.Succeeded)
                return;
            Tracker.Retitle(candidate => AgentDocuments.IsSame(candidate as Document, e.Document), e.Document.Title);
        }

        private static void OnDocumentClosing(object sender, DocumentClosingEventArgs e) {
            var entry = Tracker.Documents.FirstOrDefault(candidate => AgentDocuments.IsSame(candidate.Document as Document, e.Document));
            if (entry == null)
                return;
            lock (sync) {
                closingDocument = entry.Document as Document;
                closingDocumentId = e.DocumentId;
            }
        }

        private static void OnDocumentClosed(object sender, DocumentClosedEventArgs e) {
            Document closed;
            lock (sync) {
                if (closingDocument == null || e.DocumentId != closingDocumentId)
                    return;
                closed = closingDocument;
                closingDocument = null;
            }
            if (e.Status != RevitAPIEventStatus.Succeeded)
                return;
            var entry = Tracker.Documents.FirstOrDefault(candidate => ReferenceEquals(candidate.Document, closed));
            if (entry != null)
                Leave(closed, entry);
        }
    }
}
