using System;
using System.Runtime.InteropServices;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The user32 window enumeration calls shared by <see cref="AgentWindows"/> and
    /// <see cref="AgentCapture"/>.
    /// </summary>
    internal static class AgentUser32 {
        internal delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

        [DllImport("user32.dll")]
        internal static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

        [DllImport("user32.dll")]
        internal static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

        [DllImport("user32.dll")]
        internal static extern bool IsWindowVisible(IntPtr window);
    }
}
