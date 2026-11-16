using System;
using System.Text;

namespace pyRevitCLI {
    /// <summary>
    /// Keeps CLI output lossless when it is consumed by another process.
    /// </summary>
    internal static class PyRevitCLIConsoleEncoding {
        /// <summary>
        /// Switches the console output encoding to BOM-less UTF-8 when stdout is redirected.
        /// </summary>
        /// <param name="isOutputRedirected">Whether stdout is a pipe or file rather than a console.</param>
        /// <param name="setOutputEncoding">Applies the encoding to the console.</param>
        /// <remarks>
        /// Without this, a redirected stdout uses the console code page and non-ASCII text such as
        /// agent run output reaches the reader as U+FFFD. An interactive console is left untouched.
        /// </remarks>
        internal static void ApplyForRedirectedOutput(bool isOutputRedirected, Action<Encoding> setOutputEncoding) {
            if (isOutputRedirected)
                setOutputEncoding(new UTF8Encoding(false));
        }

        internal static void Apply() {
            ApplyForRedirectedOutput(Console.IsOutputRedirected, encoding => Console.OutputEncoding = encoding);
        }
    }
}
