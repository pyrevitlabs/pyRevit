using System;

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
    /// Invariant: the panel never calls the Revit API from its own UI events. Starting a session
    /// goes through the agent dispatcher's ExternalEvent; Revit tells the panel which document is
    /// active through its events. Everything else the panel does only changes host state.
    /// Closing the pane ends the session.
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
        private static string activeDocumentTitle;
        private static UIApplication uiApplication;

        /// <summary>
        /// Raised when the active document changes, on Revit's main thread.
        /// </summary>
        internal static event Action ActiveDocumentChanged;

        internal static DockablePaneId PaneId => new DockablePaneId(PaneGuid);

        internal static string ActiveDocumentTitle {
            get {
                lock (sync)
                    return activeDocumentTitle;
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
            NoteActiveDocument(uiApp.ActiveUIDocument?.Document?.Title);
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
                uiApp.RegisterDockablePane(PaneId, Title, new AgentPanelProvider(IsDarkTheme()));
                uiApplication = uiApp;
                uiApp.DockableFrameVisibilityChanged += OnVisibilityChanged;
                uiApp.ViewActivated += OnViewActivated;
                uiApp.Application.DocumentClosed += OnDocumentClosed;
                uiApp.Idling += HideOnFirstIdlingWhileHostIsOff;
            }
            catch (Exception ex) {
                logger.Warn("Could not register the agent panel: {0}", ex.Message);
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
                    NoteActiveDocument(app.ActiveUIDocument?.Document?.Title);
                    var pane = app.GetDockablePane(PaneId);
                    if (!pane.IsShown())
                        pane.Show();
                }
                catch (Exception ex) {
                    logger.Debug("Could not show the agent panel: {0}", ex.Message);
                }
            });
        }

        private static void NoteActiveDocument(string title) {
            lock (sync) {
                if (title == activeDocumentTitle)
                    return;
                activeDocumentTitle = title;
            }
            ActiveDocumentChanged?.Invoke();
        }

        private static void OnVisibilityChanged(object sender, DockableFrameVisibilityChangedEventArgs e) {
            if (e.PaneId.Guid != PaneGuid || e.DockableFrameShown)
                return;
            AgentSessions.EndForPanelClosed();
        }

        private static void OnViewActivated(object sender, ViewActivatedEventArgs e) {
            NoteActiveDocument(e.Document?.Title);
        }

        private static void OnDocumentClosed(object sender, DocumentClosedEventArgs e) {
            try {
                NoteActiveDocument(uiApplication?.ActiveUIDocument?.Document?.Title);
            }
            catch (Exception) {
                NoteActiveDocument(null);
            }
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

        /// <summary>
        /// Whether Revit uses its dark theme. Read through reflection because Revit versions before
        /// 2024 have no theme API; any failure reads as light.
        /// </summary>
        private static bool IsDarkTheme() {
            try {
                var themeManager = Type.GetType("Autodesk.Revit.UI.UIThemeManager, RevitAPIUI");
                var theme = themeManager?.GetProperty("CurrentTheme")?.GetValue(null, null);
                return string.Equals(theme?.ToString(), "Dark", StringComparison.OrdinalIgnoreCase);
            }
            catch (Exception) {
                return false;
            }
        }
    }

    internal sealed class AgentPanelProvider : IDockablePaneProvider {
        private readonly bool dark;

        public AgentPanelProvider(bool dark) {
            this.dark = dark;
        }

        public void SetupDockablePane(DockablePaneProviderData data) {
            data.FrameworkElement = new AgentPanelPage(dark);
            data.VisibleByDefault = false;
            data.InitialState = new DockablePaneState { DockPosition = DockPosition.Right };
        }
    }
}
