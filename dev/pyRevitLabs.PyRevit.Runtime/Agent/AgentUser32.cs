using System;
using System.Runtime.InteropServices;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The user32 calls shared by <see cref="AgentWindows"/>, <see cref="AgentCapture"/> and
    /// <see cref="AgentApproval"/>: window enumeration and the taskbar flash.
    /// </summary>
    internal static class AgentUser32 {
        private const uint FlashStop = 0;
        private const uint FlashAll = 3;
        private const uint FlashUntilForeground = 12;

        internal delegate bool EnumWindowsProc(IntPtr window, IntPtr parameter);

        [StructLayout(LayoutKind.Sequential)]
        internal struct FlashInfo {
            internal uint Size;
            internal IntPtr Window;
            internal uint Flags;
            internal uint Count;
            internal uint TimeoutMilliseconds;
        }

        /// <summary>
        /// Builds the <c>FLASHWINFO</c> that starts or stops the taskbar flash of
        /// <paramref name="window"/>. Starting flashes until the window is foregrounded.
        /// </summary>
        internal static FlashInfo BuildFlashInfo(IntPtr window, bool stop) {
            return new FlashInfo {
                Size = (uint)Marshal.SizeOf(typeof(FlashInfo)),
                Window = window,
                Flags = stop ? FlashStop : FlashAll | FlashUntilForeground,
                Count = stop ? 0 : uint.MaxValue,
                TimeoutMilliseconds = 0,
            };
        }

        /// <summary>
        /// Starts or stops the taskbar flash of <paramref name="window"/>. Does nothing for a
        /// null handle.
        /// </summary>
        internal static void Flash(IntPtr window, bool stop) {
            if (window == IntPtr.Zero)
                return;
            var info = BuildFlashInfo(window, stop);
            FlashWindowEx(ref info);
        }

        [DllImport("user32.dll")]
        private static extern bool FlashWindowEx(ref FlashInfo info);

        [DllImport("user32.dll")]
        internal static extern bool EnumWindows(EnumWindowsProc callback, IntPtr parameter);

        [DllImport("user32.dll")]
        internal static extern uint GetWindowThreadProcessId(IntPtr window, out uint processId);

        [DllImport("user32.dll")]
        internal static extern bool IsWindowVisible(IntPtr window);

        [DllImport("user32.dll")]
        internal static extern bool IsWindowEnabled(IntPtr window);
    }
}
