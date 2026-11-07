using System;
using System.Collections.Generic;
using System.Linq;

using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Events;
using Autodesk.Revit.UI;
using Autodesk.Revit.UI.Events;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The pyRevit Agent dockable pane, where the user starts, pauses and ends agent sessions and
    /// sees what agents are doing.
    /// </summary>
    /// <remarks>
    /// Registered by <see cref="AgentHost.Configure"/> on the first pyRevit load, whether or not
    /// the host is enabled, because Revit accepts a dockable pane only during startup and never
    /// removes one. While the host is disabled the pane is hidden at startup and says so.
    /// Invariant: the panel never calls the Revit API from its own UI events. Starting, adding,
    /// ending and closing go through the agent dispatcher's ExternalEvent; the open documents and
    /// the active one are read in Revit's events and kept for the panel. Everything else the panel
    /// does only changes host state.
    /// Hiding the pane pauses the session, whether the user closed it or Revit hid it, for
    /// example on its Home screen; only the user resumes it.
    /// From Revit 2024 the pane follows Revit's light or dark theme, including a change made
    /// while it is open; see <see cref="AgentPanelTheme.RevitIsDark"/>.
    /// </remarks>
    public static class AgentPanel {
        public const string Title = "pyRevit Agent";

        /// <summary>
        /// The pane's id. Callers that need the pane use <see cref="Show"/> instead of this id.
        /// </summary>
        public static readonly Guid PaneGuid = new Guid("5b0c7e2a-8f4d-4a61-9c3e-2d7f1a6b9e40");

        private static readonly Logger logger = LogManager.GetCurrentClassLogger();
        private static readonly TimeSpan RevealInterval = TimeSpan.FromMinutes(1);
        private static readonly object sync = new object();
        private static bool registrationAttempted;
        private static DateTime lastRevealUtc = DateTime.MinValue;
        private static List<AgentPanelOpenDocument> openDocuments = new List<AgentPanelOpenDocument>();
        private static UIApplication uiApplication;
        private static AgentPanelProvider provider;

        /// <summary>
        /// Raised when a document opens, closes or is renamed, or another one becomes active, on
        /// Revit's main thread.
        /// </summary>
        internal static event Action DocumentsChanged;

        internal static DockablePaneId PaneId => new DockablePaneId(PaneGuid);

        /// <summary>
        /// The open documents, links left out, as Revit last reported them.
        /// </summary>
        internal static IList<AgentPanelOpenDocument> OpenDocuments {
            get {
                lock (sync)
                    return openDocuments.ToList();
            }
        }

        /// <summary>
        /// Shows the agent panel. Must run in a Revit API context, such as a pyRevit command.
        /// </summary>
        public static void Show(UIApplication uiApp) {
            if (uiApp == null)
                throw new ArgumentNullException(nameof(uiApp));
            if (!DockablePane.PaneIsRegistered(PaneId)) {
                TaskDialog.Show(Title, "The agent panel becomes available after Revit restarts.");
                return;
            }
            NoteDocuments(uiApp);
            uiApp.GetDockablePane(PaneId).Show();
        }

        /// <summary>
        /// Registers the pane once per Revit process. Failures are logged, never thrown, so they
        /// can't stop the agent host from configuring.
        /// </summary>
        internal static void Register(UIApplication uiApp) {
            lock (sync) {
                if (registrationAttempted)
                    return;
                registrationAttempted = true;
            }
            try {
                if (DockablePane.PaneIsRegistered(PaneId))
                    return;
                provider = new AgentPanelProvider();
                uiApp.RegisterDockablePane(PaneId, Title, provider);
                uiApplication = uiApp;
                uiApp.DockableFrameVisibilityChanged += OnVisibilityChanged;
                uiApp.ViewActivated += OnViewActivated;
                uiApp.Application.DocumentOpened += OnDocumentOpened;
                uiApp.Application.DocumentCreated += OnDocumentCreated;
                uiApp.Application.DocumentClosed += OnDocumentClosed;
                uiApp.Application.DocumentSavedAs += OnDocumentSavedAs;
                uiApp.Idling += HideOnFirstIdlingWhileHostIsOff;
#if !(REVIT2021 || REVIT2022 || REVIT2023)
                uiApp.ThemeChanged += OnThemeChanged;
#endif
            }
            catch (Exception ex) {
                logger.Warn("Could not register the agent panel; it becomes available after Revit restarts: {0}", ex.Message);
            }
        }

        /// <summary>
        /// Shows the pane for an agent's request for a session, at most once a minute so a
        /// looping agent can't keep reopening it. The pane is shown through the dispatcher,
        /// because the request arrives on the pipe thread.
        /// </summary>
        internal static void RevealForRequest() {
            var now = DateTime.UtcNow;
            lock (sync) {
                if (now - lastRevealUtc < RevealInterval)
                    return;
                lastRevealUtc = now;
            }
            AgentHost.Dispatcher?.Post(app => {
                try {
                    if (!DockablePane.PaneIsRegistered(PaneId))
                        return;
                    NoteDocuments(app);
                    var pane = app.GetDockablePane(PaneId);
                    if (!pane.IsShown())
                        pane.Show();
                }
                catch (Exception ex) {
                    logger.Debug("Could not show the agent panel: {0}", ex.Message);
                }
            });
        }

        /// <remarks>Must run in a Revit API context, because it reads the documents' views.</remarks>
        private static void NoteDocuments(UIApplication app) {
            List<AgentPanelOpenDocument> snapshot;
            try {
                var active = app?.ActiveUIDocument?.Document;
                snapshot = app == null
                    ? new List<AgentPanelOpenDocument>()
                    : app.Application.Documents.Cast<Document>()
                        .Where(doc => !doc.IsLinked)
                        .Select(doc => new AgentPanelOpenDocument(
                            AgentDocuments.Keys.KeyOf(doc), doc.Title, AgentDocuments.IsSame(active, doc), AgentDocuments.IsBackground(doc)))
                        .ToList();
            }
            catch (Exception ex) {
                logger.Debug("Could not read the open documents for the agent panel: {0}", ex.Message);
                return;
            }
            lock (sync) {
                if (snapshot.SequenceEqual(openDocuments))
                    return;
                openDocuments = snapshot;
            }
            DocumentsChanged?.Invoke();
        }

        private static void OnVisibilityChanged(object sender, DockableFrameVisibilityChangedEventArgs e) {
            if (e.PaneId.Guid != PaneGuid || e.DockableFrameShown)
                return;
            AgentSessions.PauseForPanelHidden();
        }

        private static void OnViewActivated(object sender, ViewActivatedEventArgs e) {
            NoteDocuments(sender as UIApplication ?? uiApplication);
        }

        private static void OnDocumentOpened(object sender, DocumentOpenedEventArgs e) {
            NoteDocuments(uiApplication);
        }

        private static void OnDocumentCreated(object sender, DocumentCreatedEventArgs e) {
            NoteDocuments(uiApplication);
        }

        private static void OnDocumentClosed(object sender, DocumentClosedEventArgs e) {
            NoteDocuments(uiApplication);
        }

        private static void OnDocumentSavedAs(object sender, DocumentSavedAsEventArgs e) {
            NoteDocuments(uiApplication);
        }

        private static void HideOnFirstIdlingWhileHostIsOff(object sender, IdlingEventArgs e) {
            var app = sender as UIApplication;
            if (app == null)
                return;
            app.Idling -= HideOnFirstIdlingWhileHostIsOff;
            if (AgentHost.IsRunning)
                return;
            try {
                app.GetDockablePane(PaneId).Hide();
            }
            catch (Exception ex) {
                logger.Debug("Could not hide the agent panel: {0}", ex.Message);
            }
        }

#if !(REVIT2021 || REVIT2022 || REVIT2023)
        /// <remarks>
        /// Revit also raises this when only the canvas theme changes; the page ignores a palette
        /// it already shows.
        /// </remarks>
        private static void OnThemeChanged(object sender, ThemeChangedEventArgs e) {
            try {
                provider?.Page?.ApplyTheme(AgentPanelTheme.RevitIsDark());
            }
            catch (Exception ex) {
                logger.Debug("Could not switch the agent panel's theme: {0}", ex.Message);
            }
        }
#endif
    }

    internal sealed class AgentPanelProvider : IDockablePaneProvider {
        /// <summary>The page Revit hosts in the pane, once Revit has asked for it; null before.</summary>
        public AgentPanelPage Page { get; private set; }

        public void SetupDockablePane(DockablePaneProviderData data) {
            Page = new AgentPanelPage(AgentPanelTheme.RevitIsDark());
            data.FrameworkElement = Page;
            data.VisibleByDefault = false;
            data.InitialState = new DockablePaneState { DockPosition = DockPosition.Right };
        }
    }
}
