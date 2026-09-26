using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

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
    /// </remarks>
    internal static class AgentWindows {
        private const int MaxWindows = 6;

        private delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

        [DllImport("user32.dll")]
        private static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

        [DllImport("user32.dll")]
        private static extern bool IsWindowVisible(IntPtr window);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetWindowText(IntPtr window, StringBuilder text, int maxCount);

        [DllImport("user32.dll", CharSet = CharSet.Unicode)]
        private static extern int GetClassName(IntPtr window, StringBuilder className, int maxCount);

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
                    GetWindowText(window, text, text.Capacity);
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
