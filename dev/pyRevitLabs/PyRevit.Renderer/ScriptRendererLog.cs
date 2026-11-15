using System;
using System.Globalization;
using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Renderer {
    /// <summary>
    /// Renderer lifecycle tracing. Records go through NLog like every other
    /// pyRevit runtime record, so they persist to the pyRevit runtime log and
    /// surface in the console only when the user has debug logging on.
    ///
    /// Invariant: emission is re-entrancy guarded. A visible record appends to
    /// an output window, which schedules another flush, which logs again;
    /// without the guard renderer logging feeds itself on the same thread.
    /// </summary>
    public static class ScriptRendererLog {
        private static readonly Logger Logger = LogManager.GetLogger("pyrevit.runtime.webview");

        [ThreadStatic]
        private static bool _emitting;

        /// <summary>Records a debug trace for the renderer.</summary>
        public static void Debug(string format, params object[] args) {
            Emit(false, format, args);
        }

        /// <summary>Records an error for the renderer.</summary>
        public static void Error(string format, params object[] args) {
            Emit(true, format, args);
        }

        private static void Emit(bool isError, string format, object[] args) {
            if (_emitting)
                return;

            _emitting = true;
            try {
                var message = args == null || args.Length == 0
                    ? format
                    : string.Format(CultureInfo.InvariantCulture, format, args);
                if (isError)
                    Logger.Error(message);
                else
                    Logger.Debug(message);
            }
            catch {
            }
            finally {
                _emitting = false;
            }
        }
    }
}
