#nullable enable
using System;
using pyRevitLabs.NLog;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Logger adapter used by the C# session manager.
    /// </summary>
    public class LoggingHelper : ILogger
    {
        private static readonly Logger nlog = LogManager.GetCurrentClassLogger();

        public LoggingHelper()
        {
        }

        /// <summary>
        /// Logs an informational message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Info(string message)
        {
            try
            {
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
                nlog.Warn(message);
            }
            catch (Exception ex)
            {
                nlog.Error(ex, "Logging (Warning) failed");
            }
        }

    }
}
