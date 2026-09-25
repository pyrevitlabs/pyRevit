#nullable enable
using System;
using System.Collections.Generic;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Severity of a captured log record, mirroring the <see cref="ILogger"/> methods.
    /// </summary>
    internal enum CapturedLogLevel
    {
        Debug,
        Info,
        Warning,
        Error
    }

    /// <summary>
    /// Buffers the log records a worker thread emits so the thread that owns the parallel work can
    /// replay them afterwards, in a deterministic order.
    /// </summary>
    /// <remarks>
    /// A record written from a background thread does not reach the pyRevit output window in
    /// place: <c>ScriptOutput.write_log_record</c> marshals it onto the WPF dispatcher, which does
    /// not pump while the main thread is running a session load, so it renders only once the load
    /// has finished. The runtime log file gets it immediately, but in whatever order the workers
    /// happened to interleave, which differs between runs of the same load. Capturing on the
    /// worker and replaying on the owning thread fixes both: the window shows the records in
    /// place, and the file order stops depending on scheduling.
    /// <para>
    /// Invariant: capture is thread-local and covers exactly the thread that opened it. Work a
    /// capturing thread hands to further threads is not captured, and nesting is not supported.
    /// </para>
    /// </remarks>
    internal static class ParallelLogCapture
    {
        [ThreadStatic]
        private static List<(CapturedLogLevel Level, string Message)>? _buffer;

        /// <summary>
        /// Redirects this thread's log records into <paramref name="buffer"/> until the returned
        /// token is disposed.
        /// </summary>
        /// <param name="buffer">Receives the records in the order they are emitted.</param>
        internal static IDisposable Begin(List<(CapturedLogLevel Level, string Message)> buffer)
        {
            if (buffer == null)
                throw new ArgumentNullException(nameof(buffer));

            _buffer = buffer;
            return new CaptureToken();
        }

        /// <summary>
        /// Adds a record to this thread's capture buffer, if it has one.
        /// </summary>
        /// <returns>
        /// False when this thread is not capturing, meaning the caller should log the record
        /// itself. <see cref="ILogger"/> implementations must honour this.
        /// </returns>
        internal static bool TryCapture(CapturedLogLevel level, string message)
        {
            var buffer = _buffer;
            if (buffer == null)
                return false;

            buffer.Add((level, message));
            return true;
        }

        /// <summary>
        /// Writes captured records to <paramref name="logger"/> in capture order. Call from the
        /// thread that owns the parallel work, once that work has finished.
        /// </summary>
        internal static void Replay(
            ILogger logger,
            IEnumerable<(CapturedLogLevel Level, string Message)>? records)
        {
            if (logger == null || records == null)
                return;

            foreach (var (level, message) in records)
            {
                switch (level)
                {
                    case CapturedLogLevel.Info:
                        logger.Info(message);
                        break;
                    case CapturedLogLevel.Warning:
                        logger.Warning(message);
                        break;
                    case CapturedLogLevel.Error:
                        logger.Error(message);
                        break;
                    default:
                        logger.Debug(message);
                        break;
                }
            }
        }

        private sealed class CaptureToken : IDisposable
        {
            public void Dispose()
            {
                _buffer = null;
            }
        }
    }
}
