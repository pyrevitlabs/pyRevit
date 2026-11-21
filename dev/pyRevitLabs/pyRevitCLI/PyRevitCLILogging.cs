using pyRevitLabs.NLog;
using pyRevitLabs.NLog.Config;
using pyRevitLabs.NLog.Targets;

namespace pyRevitCLI {
    /// <summary>
    /// Builds the CLI's console logging so that command output stays separable from diagnostics.
    /// </summary>
    internal static class PyRevitCLILogging {
        private const string Layout = @"${level}: ${message} ${exception}";

        /// <summary>
        /// Creates the console logging configuration for one CLI invocation.
        /// </summary>
        /// <param name="verbose">Also log Info messages.</param>
        /// <param name="debug">Also log Debug messages.</param>
        /// <remarks>
        /// Important: Error and Fatal lines go to stderr and nothing else does. Callers redirect
        /// stdout to capture command output (for example <c>agent run &gt; out.json</c>), and an
        /// error line there is indistinguishable from data. Info and Debug lines stay on stdout.
        /// </remarks>
        internal static LoggingConfiguration CreateConsoleConfiguration(bool verbose, bool debug) {
            var config = new LoggingConfiguration();

            var errorConsole = new ConsoleTarget("logerrorconsole") { Layout = Layout, StdErr = true };
            config.AddTarget(errorConsole);
            config.AddRule(LogLevel.Error, LogLevel.Fatal, errorConsole);

            var logconsole = new ConsoleTarget("logconsole") { Layout = Layout };
            config.AddTarget(logconsole);

            if (verbose)
                config.AddRule(LogLevel.Info, LogLevel.Info, logconsole);

            if (debug)
                config.AddRule(LogLevel.Debug, LogLevel.Debug, logconsole);

            return config;
        }
    }
}
