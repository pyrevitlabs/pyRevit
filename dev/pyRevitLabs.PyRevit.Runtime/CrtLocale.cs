using System;
using System.Runtime.InteropServices;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Pins one category of the Universal CRT locale, which is process-wide state shared with Revit.
    /// </summary>
    /// <remarks>
    /// <para>
    /// Revit runs with <c>LC_CTYPE</c> at <c>C</c> and its native code depends on it: a
    /// non-<c>C</c> value changes case-insensitive comparisons of non-ASCII names, which makes Revit
    /// reject a workshared central model as corrupt on Synchronize with Central (pyRevit#4074).
    /// CPython calls <c>setlocale(LC_CTYPE, "")</c> while initializing, so anything that brings an
    /// interpreter up inside the Revit process has to run under a scope from this class.
    /// </para>
    /// <para>
    /// The CRT is the shared <c>ucrtbase.dll</c>, so the call here and the one inside
    /// <c>python3*.dll</c> act on the same locale.
    /// </para>
    /// </remarks>
    internal sealed class CrtLocale : IDisposable {
        internal const int LcCtype = 2;

        private readonly int _category;
        private readonly string _saved;

        private CrtLocale(int category, string saved) {
            _category = category;
            _saved = saved;
        }

        /// <summary>
        /// Captures the current locale of <paramref name="category"/> and restores it when the
        /// returned scope is disposed.
        /// </summary>
        /// <param name="category">A CRT locale category such as <see cref="LcCtype"/>.</param>
        /// <returns>The scope to dispose once the locale-changing work is done.</returns>
        internal static CrtLocale Preserve(int category) {
            return new CrtLocale(category, Query(category));
        }

        /// <summary>
        /// Returns the current locale name of <paramref name="category"/>, or null when the CRT
        /// reports none.
        /// </summary>
        internal static string Query(int category) {
            return Marshal.PtrToStringAnsi(setlocale(category, IntPtr.Zero));
        }

        public void Dispose() {
            if (_saved == null)
                return;
            var restored = Marshal.StringToHGlobalAnsi(_saved);
            try {
                setlocale(_category, restored);
            }
            finally {
                Marshal.FreeHGlobal(restored);
            }
        }

        [DllImport("ucrtbase.dll", CallingConvention = CallingConvention.Cdecl)]
        private static extern IntPtr setlocale(int category, IntPtr locale);
    }
}
