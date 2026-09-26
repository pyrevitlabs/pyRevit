using System;
using System.Globalization;
using System.Threading;

using pyRevitLabs.NLog;

namespace PyRevitLabs.PyRevit.Runtime {
    /// <summary>
    /// Diagnostics for the output path, kept on NLog so they reach the runtime log and an already
    /// open console without ever needing one to be created.
    /// </summary>
    /// <remarks>
    /// Invariant: emission is re-entrancy guarded, and never at error level. These records are
    /// about the output path failing, so they must not themselves ask for a window, and must not
    /// mark the session as having errors - that drives the startup window's self-destruct.
    /// </remarks>
    internal static class ScriptOutputUiLog {
        private static readonly Logger Logger = LogManager.GetLogger("pyrevit.runtime.output");

        [ThreadStatic]
        private static bool _emitting;

        public static void Debug(string format, params object[] args) {
            Emit(false, format, args);
        }

        public static void Warn(string format, params object[] args) {
            Emit(true, format, args);
        }

        private static void Emit(bool isWarning, string format, object[] args) {
            if (_emitting)
                return;

            _emitting = true;
            try {
                var message = args == null || args.Length == 0
                    ? format
                    : string.Format(CultureInfo.InvariantCulture, format, args);
                if (isWarning)
                    Logger.Warn(message);
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
