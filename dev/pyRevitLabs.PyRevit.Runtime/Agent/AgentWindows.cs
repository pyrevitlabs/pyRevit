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
    /// Important: window titles are read with <c>InternalGetWindowText</c>, not
    /// <c>GetWindowText</c>. For a window owned by another thread of this process,
    /// <c>GetWindowText</c> sends WM_GETTEXT and waits for that thread to answer, so a busy
    /// UI thread would block the caller and the <c>revit_busy</c> answer would never be sent.
    /// </remarks>
    internal static class AgentWindows {
        private const int MaxWindows = 6;

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int InternalGetWindowText(IntPtr window, StringBuilder text, int maxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr window, StringBuilder className, int maxCount);

        /// <summary>
        /// Whether a modal dialog is open: Revit's main window is disabled and another visible
        /// window of the process is showing.
        /// </summary>
        /// <remarks>
        /// Revit disables its main window while a modal dialog runs, which is what stops
        /// ExternalEvents from firing. Reads window state only and never sends a message.
        /// </remarks>
        public static bool IsModalDialogOpen() {
            try {
                var mainWindow = Process.GetCurrentProcess().MainWindowHandle;
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
                var mainWindow = process.MainWindowHandle;
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
    }
}
