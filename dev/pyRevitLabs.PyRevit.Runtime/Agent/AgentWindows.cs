using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

using static PyRevitLabs.PyRevit.Runtime.Agent.AgentUser32;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Lists the visible top-level windows of the Revit process other than its main window,
    /// to explain why Revit isn't idle.
    /// </summary>
    /// <remarks>
    /// Revit shows some modal dialogs while idle, outside any agent run, such as the
    /// "You have not saved your project recently" reminder. The run guard can't dismiss those,
    /// and they block every later request. Naming the window lets the agent ask the user to
    /// answer it instead of guessing, or closing windows it doesn't understand. Read-only:
    /// it never sends messages to the windows. Safe to call from any thread.
    /// Important: Revit's main window comes from <see cref="RememberMainWindow"/>, never from
    /// <c>Process.MainWindowHandle</c>. When a dialog has no owner window, Windows reports the
    /// dialog itself as the process's main window, so the process handle would point at an
    /// enabled window, hide the modal state, and leave the dialog out of the listing.
    /// Important: window titles are read with <c>InternalGetWindowText</c>, not
    /// <c>GetWindowText</c>. For a window owned by another thread of this process,
    /// <c>GetWindowText</c> sends WM_GETTEXT and waits for that thread to answer, so a busy
    /// UI thread would block the caller and the <c>revit_busy</c> answer would never be sent.
    /// </remarks>
    internal static class AgentWindows {
        private const int MaxWindows = 6;

        private static IntPtr revitMainWindow;

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int InternalGetWindowText(IntPtr window, StringBuilder text, int maxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr window, StringBuilder className, int maxCount);

        /// <summary>
        /// Records Revit's own main window, as reported by <c>UIApplication.MainWindowHandle</c>.
        /// </summary>
        /// <remarks>
        /// Call it on the Revit UI thread, for example from <c>AgentHost.Configure</c>. Until it
        /// has been called, the process's main window stands in.
        /// </remarks>
        public static void RememberMainWindow(IntPtr mainWindow) {
            revitMainWindow = mainWindow;
        }

        /// <summary>
        /// Whether a modal dialog is open: Revit's main window is disabled and another visible
        /// window of the process is showing.
        /// </summary>
        /// <remarks>
        /// Revit disables its main window while a modal dialog runs, which is what stops
        /// ExternalEvents from firing. Reads window state only and never sends a message.
        /// A visible window other than the main window always exists, such as the pyRevit one,
        /// so in practice only the disabled main window decides.
        /// </remarks>
        public static bool IsModalDialogOpen() {
            try {
                var mainWindow = MainWindow();
                return mainWindow != IntPtr.Zero && !IsWindowEnabled(mainWindow) && OpenDialogs().Count > 0;
            }
            catch (Exception) {
                return false;
            }
        }

        public static List<string> OpenDialogs() {
            var found = new List<string>();
            try {
                var process = Process.GetCurrentProcess();
                var processId = (uint)process.Id;
                var mainWindow = MainWindow();
                EnumWindows((window, _) => {
                    if (window == mainWindow || !IsWindowVisible(window))
                        return true;
                    GetWindowThreadProcessId(window, out var owner);
                    if (owner != processId)
                        return true;
                    var text = new StringBuilder(256);
                    InternalGetWindowText(window, text, text.Capacity);
                    var className = new StringBuilder(256);
                    GetClassName(window, className, className.Capacity);
                    if (text.Length == 0 && className.ToString().StartsWith("Tooltip", StringComparison.OrdinalIgnoreCase))
                        return true;
                    found.Add(string.Format("'{0}' ({1})", text, className));
                    return found.Count < MaxWindows;
                }, IntPtr.Zero);
            }
            catch (Exception) {
            }
            return found;
        }

        private static IntPtr MainWindow() {
            return revitMainWindow != IntPtr.Zero ? revitMainWindow : Process.GetCurrentProcess().MainWindowHandle;
        }
    }
}
