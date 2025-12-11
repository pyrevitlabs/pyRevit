using System;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Helper class for logging using Python's logger.
    /// </summary>
    public class LoggingHelper
    {
        private readonly dynamic _pythonLogger;

        /// <summary>
        /// Initializes a new instance of the <see cref="LoggingHelper"/> class.
        /// </summary>
        /// <param name="pythonLogger">The Python logger instance passed from Python code.</param>
        public LoggingHelper(object pythonLogger)
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
                (_pythonLogger ?? throw new InvalidOperationException("Python logger is not initialized")).info(message);
            }
            catch { }
        }

        /// <summary>
        /// Logs a debug message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Debug(string message)
        {
            try
            {
                (_pythonLogger ?? throw new InvalidOperationException("Python logger is not initialized")).debug(message);
            }
            catch { }
        }

        /// <summary>
        /// Logs an error message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Error(string message)
        {
            try
            {
                (_pythonLogger ?? throw new InvalidOperationException("Python logger is not initialized")).error(message);
            }
            catch { }
        }

        /// <summary>
        /// Logs a warning message.
        /// </summary>
        /// <param name="message">The message to log.</param>
        public void Warning(string message)
        {
            try
            {
                (_pythonLogger ?? throw new InvalidOperationException("Python logger is not initialized")).warning(message);
            }
            catch { }
        }
    }
}
