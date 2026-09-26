using System;
using System.Reflection;

using Autodesk.Revit.ApplicationServices;
using Autodesk.Revit.UI;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// The route a Revit application handle takes to become a
    /// <see cref="UIApplication"/>, as reported by
    /// <see cref="RevitAppResolver.Classify"/>.
    /// </summary>
    public enum RevitAppHandleKind {
        /// <summary>
        /// The handle already is a <see cref="UIApplication"/> and is used as-is.
        /// </summary>
        UiApplication,

        /// <summary>
        /// The handle is a DB-only <see cref="Application"/>. It is wrapped in a
        /// <see cref="UIApplication"/>, which is live but may expose no
        /// <c>ActiveUIDocument</c> for as long as the originating event runs.
        /// </summary>
        Application,

        /// <summary>
        /// The handle is a <see cref="UIControlledApplication"/>, which keeps the
        /// UI application it was created from in a private field.
        /// </summary>
        UIControlledApplication,

        /// <summary>
        /// The handle is a <see cref="ControlledApplication"/>, a null, or a type
        /// carrying no route back to a UI application. The session handle is used.
        /// </summary>
        Unresolvable,
    }

    /// <summary>
    /// Normalizes any Revit application handle into a <see cref="UIApplication"/>,
    /// which is the single shape the <c>__revit__</c> builtin is allowed to have.
    /// </summary>
    /// <remarks>
    /// Revit hands subscribers four unrelated application types depending on the
    /// event that fired: <see cref="UIApplication"/>, <see cref="Application"/>,
    /// <see cref="UIControlledApplication"/> and <see cref="ControlledApplication"/>.
    /// Every <c>Application_*</c> event hook is registered on
    /// <c>uiApp.Application</c>, so leaking that distinction into scripts made
    /// <c>__revit__</c> polymorphic: bundled scripts call
    /// <c>__revit__.ActiveUIDocument</c> and the pyrevit library reads the host
    /// application from it, so a DB-only handle silently turned
    /// <c>HOST_APP.uiapp</c>, <c>HOST_APP.uidoc</c> and <c>HOST_APP.doc</c> into
    /// <c>None</c> instead of failing. Funnelling every handle through here is
    /// what makes the builtin consistently a UI handle.
    ///
    /// <para><b>Invariant:</b> resolution never throws. A handle that cannot be
    /// resolved yields <c>null</c>, which reaches scripts as
    /// <c>__revit__ is None</c>; callers must treat that as "no Revit UI context"
    /// rather than assuming a handle exists.</para>
    ///
    /// <para><b>Compatibility:</b> scripts that need the handle exactly as Revit
    /// delivered it read <c>__eventsender__</c>, which still receives the raw
    /// sender. <c>__revit__</c> itself keeps working for the code that already
    /// treats it as a UI application; code that type-switches on it must read
    /// <c>__eventsender__</c> instead.</para>
    /// </remarks>
    public static class RevitAppResolver {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private const string UIControlledAppUIAppField = "m_uiapplication";

        private static UIApplication _sessionUIApp;

        /// <summary>
        /// The session-wide <see cref="UIApplication"/> recorded by
        /// <see cref="SeedSessionUIApplication(UIApplication)"/>, or <c>null</c>
        /// when no session handle has been offered yet.
        /// </summary>
        public static UIApplication SessionUIApplication {
            get { return _sessionUIApp; }
        }

        /// <summary>
        /// Offers <paramref name="uiApp"/> as the session-wide fallback handle.
        /// </summary>
        /// <param name="uiApp">
        /// A <see cref="UIApplication"/> that is valid for the whole Revit
        /// process. Null handles are ignored.
        /// </param>
        /// <remarks>
        /// <b>Invariant:</b> the first non-null handle wins and is never replaced.
        /// The session loader offers the startup handle before any command or hook
        /// runs, and that one stays valid for the lifetime of the process. Later
        /// callers only ever offer handles from
        /// <c>ExternalCommandData.Application</c> or hook activation - never the
        /// event-scoped sender - because Revit may invalidate an event-scoped
        /// handle once its event returns, and a stable handle is worth more here
        /// than a fresher one. Safe to call repeatedly.
        /// </remarks>
        public static void SeedSessionUIApplication(UIApplication uiApp) {
            if (_sessionUIApp == null && uiApp != null)
                _sessionUIApp = uiApp;
        }

        /// <summary>
        /// Reports which route <paramref name="appHandle"/> would take in
        /// <see cref="GetUIApplication"/>, for diagnostics and for tests that need
        /// to name the branch a handle belongs to.
        /// </summary>
        /// <param name="appHandle">Any Revit application handle, or <c>null</c>.</param>
        public static RevitAppHandleKind Classify(object appHandle) {
            switch (appHandle) {
                case UIApplication _: return RevitAppHandleKind.UiApplication;
                case Application _: return RevitAppHandleKind.Application;
                case UIControlledApplication _: return RevitAppHandleKind.UIControlledApplication;
                default: return RevitAppHandleKind.Unresolvable;
            }
        }

        /// <summary>
        /// Resolves <paramref name="appHandle"/> to a <see cref="UIApplication"/>,
        /// or <c>null</c> when no UI application can be reached.
        /// </summary>
        /// <param name="appHandle">
        /// Any Revit application handle, typically an event sender. Unknown types
        /// and null fall back to the session handle recorded by
        /// <see cref="SeedSessionUIApplication(UIApplication)"/>.
        /// </param>
        /// <remarks>
        /// <b>Warning:</b> a <see cref="UIApplication"/> resolved from a DB-only
        /// <see cref="RevitAppHandleKind.Application"/> handle is real, but Revit
        /// does not guarantee an <c>ActiveUIDocument</c> while the originating
        /// event is still running. Consumers must degrade to <c>None</c> rather
        /// than assume a document, and scripts that need the document the event
        /// carries should read it from the event arguments.
        ///
        /// <para>Never throws; see the type-level invariant.</para>
        /// </remarks>
        public static UIApplication GetUIApplication(object appHandle) {
            var kind = Classify(appHandle);
            if (kind != RevitAppHandleKind.UiApplication)
                logger.Debug("Resolving __revit__ from {0} sender", kind);

            switch (kind) {
                case RevitAppHandleKind.UiApplication:
                    var uiApp = (UIApplication)appHandle;
                    SeedSessionUIApplication(uiApp);
                    return uiApp;
                case RevitAppHandleKind.Application:
                    return FromApplication((Application)appHandle);
                case RevitAppHandleKind.UIControlledApplication:
                    return FromUIControlledApplication((UIControlledApplication)appHandle) ?? _sessionUIApp;
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
