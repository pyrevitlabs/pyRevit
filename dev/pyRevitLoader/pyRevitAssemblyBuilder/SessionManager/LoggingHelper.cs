#nullable enable
using System;
using System.Diagnostics;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Helper class for logging using Python's logger.
    /// </summary>
    public class LoggingHelper : ILogger
    {
        private const string LogPrefix = "[pyRevit]";
        private readonly dynamic? _pythonLogger;

        /// <summary>
        /// Initializes a new instance of the <see cref="LoggingHelper"/> class.
        /// </summary>
        /// <param name="pythonLogger">The Python logger instance passed from Python code.</param>
        public LoggingHelper(object? pythonLogger)
        {
            _pythonLogger = pythonLogger;
        }

        /// <summary>
        /// Logs an informational message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Info(string message)
        {
            try
            {
                _pythonLogger?.info(message);
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"{LogPrefix} Logging (Info) failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Logs a debug message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Debug(string message)
        {
            try
            {
                _pythonLogger?.debug(message);
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"{LogPrefix} Logging (Debug) failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Logs an error message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Error(string message)
        {
            try
            {
                _pythonLogger?.error(message);
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"{LogPrefix} Logging (Error) failed: {ex.Message}");
            }
        }

        /// <summary>
        /// Logs a warning message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Warning(string message)
        {
            try
            {
                _pythonLogger?.warning(message);
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"{LogPrefix} Logging (Warning) failed: {ex.Message}");
            }
        }
    }
}
