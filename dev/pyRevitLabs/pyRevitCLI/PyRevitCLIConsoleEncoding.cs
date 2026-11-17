using System;
using System.IO;
using System.Text;

namespace pyRevitCLI {
    /// <summary>
    /// Keeps CLI output lossless when it is consumed by another process.
    /// </summary>
    internal static class PyRevitCLIConsoleEncoding {
        /// <summary>
        /// Replaces a redirected standard stream writer with an auto-flushing BOM-less UTF-8 writer.
        /// </summary>
        /// <param name="isRedirected">Whether the stream is a pipe or file rather than a console.</param>
        /// <param name="openStream">Opens the raw standard stream.</param>
        /// <param name="setWriter">Installs the replacement writer (for example <c>Console.SetOut</c>).</param>
        /// <remarks>
        /// Without this, a redirected stdout uses the console code page and non-ASCII text such as
        /// agent run output reaches the reader as U+FFFD. The shared console's code page
        /// (<c>Console.OutputEncoding</c>) is deliberately left alone, because changing it would
        /// persist in the parent terminal after the process exits. A stream that is not redirected
        /// is left untouched.
        /// <para>
        /// Invariant: nothing may reset the <c>Console</c> writers after this runs. In particular
        /// <c>pyRevitLabs.CommonCLI.ConsoleProvider.InvalidateOutAndError</c> (reached through
        /// <c>ConsoleProvider.Show</c> and <c>Toggle</c>) clears them by reflection, which would bring
        /// back U+FFFD. No code reachable from this CLI calls it today.
        /// </para>
        /// </remarks>
        internal static void ApplyForRedirectedStream(bool isRedirected, Func<Stream> openStream, Action<TextWriter> setWriter) {
            if (!isRedirected)
                return;
            setWriter(new StreamWriter(openStream(), new UTF8Encoding(false)) { AutoFlush = true });
        }

        internal static void Apply() {
            ApplyForRedirectedStream(Console.IsOutputRedirected, Console.OpenStandardOutput, Console.SetOut);
            ApplyForRedirectedStream(Console.IsErrorRedirected, Console.OpenStandardError, Console.SetError);
        }
    }
}
