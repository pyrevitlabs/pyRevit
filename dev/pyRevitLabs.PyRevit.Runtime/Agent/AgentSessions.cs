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
    /// In-process controls of the agent session: the user's consent for agents to work on one
    /// document, given in Revit.
    /// </summary>
    /// <remarks>
    /// Only code running inside Revit can start or resume a session. The pipe can only request,
    /// pause and end one, so an agent can't grant itself access by running the CLI. This guards
    /// against well-behaved agents acting unseen, not against a hostile script: any code inside
    /// Revit can call these methods too, except while an agent run executes.
    /// The bound document is held by reference and compared with <see cref="AgentDocuments.IsSame"/>,
    /// never by title or path. Closing it ends the session; after a move, closing the document the
    /// session left doesn't.
    /// </remarks>
    public static class AgentSessions {
        internal static readonly AgentSessionTracker Tracker = new AgentSessionTracker();

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly object sync = new object();
        private static bool eventsAttached;
        private static object closingDocument;
        private static int closingDocumentId;

        /// <summary>
        /// Whether model requests need an active session. Set from <c>[agent] require_session</c>
        /// each time pyRevit loads, so editing the config mid-session changes nothing until then.
        /// </summary>
        public static bool Required => Tracker.Required;

        /// <summary>
        /// Requires a session, or stops requiring one, until pyRevit loads again.
        /// </summary>
        /// <exception cref="AgentException">
        /// <c>session_locked</c> when making sessions optional while an agent run executes.
        /// </exception>
        public static void SetRequired(bool required) {
            Tracker.SetRequired(required);
        }

        /// <summary>
        /// Starts a session bound to the active document.
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
            if (!ScriptExecutor.IsOnMainThread)
                throw new InvalidOperationException("Agent sessions must be started on the Revit main thread.");
            var doc = app.ActiveUIDocument?.Document
                ?? throw new AgentException("no_active_document", "Open the document the agent should work on, then start the session.");
            WatchDocumentClosing(app.Application);
            AgentAwarenessWatch.Attach(app);
            var id = Tracker.Start(doc, doc.Title, DateTime.UtcNow);
            AgentAwarenessWatch.Restart(app);
            return id;
        }

        /// <summary>
        /// Moves the open session to the active document. The agent must read the context before
        /// anything else there, and its next summary of changes reports the move.
        /// </summary>
        /// <exception cref="InvalidOperationException">Called off the Revit main thread.</exception>
        /// <exception cref="AgentException">
        /// <c>no_active_document</c>; <c>already_bound</c> when the session is on the active
        /// document; <c>session_inactive</c> when there is no session; <c>session_locked</c> while
        /// an agent run executes.
        /// </exception>
        public static void Move(UIApplication app) {
            if (app == null)
                throw new ArgumentNullException(nameof(app));
            if (!ScriptExecutor.IsOnMainThread)
                throw new InvalidOperationException("Agent sessions must be moved on the Revit main thread.");
            var doc = app.ActiveUIDocument?.Document
                ?? throw new AgentException("no_active_document", "Open the document the agent should move to, then move the session.");
            if (Tracker.BoundDocument is Document bound && AgentDocuments.IsSame(bound, doc))
                throw new AgentException("already_bound", $"The agent session is already on '{doc.Title}'.");
            var left = Tracker.CurrentSession.Document;
            var lastRead = Tracker.Move(doc, doc.Title, DateTime.UtcNow);
            AgentAwarenessWatch.Restart(app);
            AgentAwarenessWatch.Awareness.RecordMove(lastRead, doc.Title);
            AgentHost.Activity.RecordMove(left, Tracker.CurrentSession, DateTime.UtcNow);
        }

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

        public static void End() {
            Tracker.End(AgentSessionEndReasons.EndedInRevit, DateTime.UtcNow);
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

        internal static void EndByClient() {
            Tracker.End(AgentSessionEndReasons.EndedByClient, DateTime.UtcNow);
        }

        /// <summary>
        /// Pauses the session when the agent panel is hidden, whether the user closed it or Revit
        /// hid it, for example on its Home screen. The user resumes it in the panel.
        /// </summary>
        internal static void PauseForPanelHidden() {
            Tracker.PauseByHost(AgentSessionPauseCauses.PanelHidden, "the agent panel in Revit was closed or hidden.");
        }

        /// <summary>
        /// Pauses the session after a run changed another open document, so the agent can't carry
        /// on until the user has seen what happened and resumed it.
        /// </summary>
        /// <param name="documents">Titles of the documents that were open before the run and that it changed.</param>
        internal static void PauseForOtherDocument(IEnumerable<string> documents) {
            var names = string.Join(", ", documents.Where(name => !string.IsNullOrEmpty(name)).Distinct().Select(name => "'" + name + "'"));
            Tracker.PauseByHost(
                AgentSessionPauseCauses.OtherDocument,
                $"the last run changed another open document ({names}), and agents may change only the session's document.");
        }

        internal static void EndForHostStop() {
            Tracker.End(AgentSessionEndReasons.HostStopped, DateTime.UtcNow);
        }

        /// <summary>
        /// Applies <c>[agent] require_session</c>. Called on every pyRevit load while the host is
        /// enabled.
        /// </summary>
        /// <remarks>
        /// A reload from inside an agent run can't make sessions optional. The refusal is logged
        /// and never thrown, so the rest of the host's configuration still runs.
        /// </remarks>
        internal static void Configure(Application app, bool required) {
            WatchDocumentClosing(app);
            try {
                Tracker.SetRequired(required);
            }
            catch (AgentException ex) when (ex.Code == "session_locked") {
                logger.Warn("Agent sessions stay required until pyRevit reloads outside an agent run: {0}", ex.Message);
            }
        }

        /// <param name="readsContext">Whether the request is <c>get_context</c>, which passes during a move's handshake.</param>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>session_moved</c> or <c>session_inactive</c>.
        /// </exception>
        internal static void CheckOnArrival(bool readsContext) {
            Tracker.CheckOnArrival(readsContext);
        }

        /// <remarks>Must run on the Revit main thread, because it compares documents.</remarks>
        /// <param name="readsContext">Whether the request is <c>get_context</c>, which passes during a move's handshake.</param>
        /// <exception cref="AgentException">
        /// <c>paused_by_user</c>, <c>paused_by_host</c>, <c>session_moved</c>, <c>session_inactive</c> or
        /// <c>wrong_document</c>.
        /// </exception>
        internal static void CheckOnDequeue(UIApplication app, bool readsContext) {
            if (Tracker.BoundDocument is Document bound && !bound.IsValidObject)
                Tracker.EndIfBoundTo(bound, AgentSessionEndReasons.DocumentClosed, DateTime.UtcNow);
            var active = app.ActiveUIDocument?.Document;
            Tracker.CheckOnDequeue(candidate => AgentDocuments.IsSame(candidate as Document, active), active?.Title, readsContext);
        }

        private static void WatchDocumentClosing(Application app) {
            lock (sync) {
                if (eventsAttached)
                    return;
                app.DocumentClosing += OnDocumentClosing;
                app.DocumentClosed += OnDocumentClosed;
                eventsAttached = true;
            }
        }

        private static void OnDocumentClosing(object sender, DocumentClosingEventArgs e) {
            var bound = Tracker.BoundDocument as Document;
            if (bound == null || !AgentDocuments.IsSame(bound, e.Document))
                return;
            lock (sync) {
                closingDocument = bound;
                closingDocumentId = e.DocumentId;
            }
        }

        private static void OnDocumentClosed(object sender, DocumentClosedEventArgs e) {
            object closed;
            lock (sync) {
                if (closingDocument == null || e.DocumentId != closingDocumentId)
                    return;
                closed = closingDocument;
                closingDocument = null;
            }
            if (e.Status == RevitAPIEventStatus.Succeeded)
                Tracker.EndIfBoundTo(closed, AgentSessionEndReasons.DocumentClosed, DateTime.UtcNow);
        }
    }
}
