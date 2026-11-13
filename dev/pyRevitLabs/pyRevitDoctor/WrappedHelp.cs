using System;
using System.Linq;

namespace pyRevitDoctor {
    /// <summary>
    /// Turns the standalone <c>pyrevit-doctor</c> help text into the text <c>pyrevit doctor --help</c> prints.
    /// </summary>
    public static class WrappedHelp {
        const string VersionUsage = "pyrevit-doctor (-V | --version)";

        /// <summary>
        /// Drops the version usage line, which <c>pyrevit</c> already offers, and renames the command.
        /// </summary>
        /// <remarks>
        /// Invariant: the result does not depend on the line endings of <paramref name="helpMessage"/>, which takes
        /// the source file's endings (CRLF in a Windows checkout).
        /// </remarks>
        public static string From(string helpMessage) {
            var lines = helpMessage
                .Replace("\r\n", "\n")
                .Split('\n')
                .Where(line => line.Trim() != VersionUsage);
            return string.Join(Environment.NewLine, lines).Replace("pyrevit-doctor", "pyrevit doctor");
        }
    }
}
