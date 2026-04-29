#nullable enable
using System;
using pyRevitLabs.NLog;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Helper class for logging using Python's logger.
    /// </summary>
    public class LoggingHelper : ILogger
    {
        private static readonly Logger nlog = LogManager.GetCurrentClassLogger();
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
                if (_pythonLogger != null)
                    _pythonLogger.info(message);
                else
                    nlog.Info(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Info) failed");
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
                if (_pythonLogger != null)
                    _pythonLogger.debug(message);
                else
                    nlog.Debug(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Debug) failed");
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
                if (_pythonLogger != null)
                    _pythonLogger.error(message);
                else
                    nlog.Error(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Error) failed");
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
                if (_pythonLogger != null)
                    _pythonLogger.warning(message);
                else
                    nlog.Warn(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Warning) failed");
            }
        }
    }
}
