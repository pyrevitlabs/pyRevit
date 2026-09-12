using System;
using System.Reflection;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.UI;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Normalizes any Revit application handle into a <see cref="UIApplication"/>.
    /// </summary>
    /// <remarks>
    /// Revit hands event subscribers four unrelated application types depending on which
    /// event fired: <see cref="UIApplication"/>, <see cref="Application"/>,
    /// <see cref="UIControlledApplication"/> and <see cref="ControlledApplication"/>.
    /// Leaking that distinction into scripts is what made the <c>__revit__</c> builtin
    /// polymorphic and broke every hook that expected a UI handle, so every handle is
    /// funnelled through here before it reaches a script.
    ///
    /// <para>Invariant: resolution never throws. An unresolvable handle yields
    /// <c>null</c>, which reaches scripts as <c>__revit__ is None</c>.</para>
    /// </remarks>
    public static class RevitAppResolver {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private const string UIControlledAppUIAppField = "m_uiapplication";

        private static UIApplication _sessionUIApp = null;

        /// <summary>
        /// Records the session-wide <see cref="UIApplication"/> used as the last-resort
        /// fallback for handles that carry no public route back to the UI application.
        /// </summary>
        /// <remarks>
        /// Safe to call repeatedly; a null handle is ignored so an existing fallback is
        /// never dropped. The stored handle is valid for the whole Revit process, not just
        /// one pyRevit session, and is therefore kept across reloads.
        /// </remarks>
        public static void SetSessionUIApplication(UIApplication uiApp) {
            if (uiApp != null)
                _sessionUIApp = uiApp;
        }

        /// <summary>
        /// Resolves <paramref name="appHandle"/> to a <see cref="UIApplication"/>,
        /// or null when no UI application can be reached.
        /// </summary>
        /// <param name="appHandle">
        /// Any Revit application handle, typically an event sender. Unknown types and null
        /// fall back to the session handle recorded by
        /// <see cref="SetSessionUIApplication(UIApplication)"/>.
        /// </param>
        /// <remarks>
        /// Warning: a <see cref="UIApplication"/> built from a DB-only handle is live but may
        /// expose no <c>ActiveUIDocument</c> while the originating event is still running.
        /// Scripts that need the untouched sender should read <c>__eventsender__</c>.
        /// </remarks>
        public static UIApplication GetUIApplication(object appHandle) {
            switch (appHandle) {
                case UIApplication uiApp:
                    SetSessionUIApplication(uiApp);
                    return uiApp;
                case Application app:
                    return FromApplication(app);
                case UIControlledApplication uiControlledApp:
                    return FromUIControlledApplication(uiControlledApp) ?? _sessionUIApp;
                default:
                    return _sessionUIApp;
            }
        }

        private static UIApplication FromApplication(Application app) {
            try {
                return new UIApplication(app);
            }
            catch (Exception ex) {
                logger.Debug("Failed wrapping Application in UIApplication | {0}", ex.Message);
                return _sessionUIApp;
            }
        }

        private static UIApplication FromUIControlledApplication(UIControlledApplication uiControlledApp) {
            try {
                var field = uiControlledApp.GetType().GetField(
                    UIControlledAppUIAppField, BindingFlags.NonPublic | BindingFlags.Instance);
                return field?.GetValue(uiControlledApp) as UIApplication;
            }
            catch (Exception ex) {
                logger.Debug("Failed unwrapping UIControlledApplication | {0}", ex.Message);
                return null;
            }
        }
    }
}
