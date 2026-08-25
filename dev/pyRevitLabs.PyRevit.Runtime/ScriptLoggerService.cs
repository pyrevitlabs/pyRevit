using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Runtime.CompilerServices;
using System.Text;

using pyRevitLabs.Common;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime {
    public enum ScriptLogLevel {
        Debug = 10,
        Info = 20,
        Deprecate = 25,
        Warning = 30,
        Error = 40,
        Critical = 50,
        Success = 80,
    }

    /// <summary>
    /// Owns logging policy and destinations for Python and other script engines.
    /// Runtime-bound instances never keep their runtime alive.
    /// </summary>
    public sealed class ScriptLoggerService {
        private static readonly object StateLock = new object();
        private static readonly object FileLock = new object();
        private static readonly ConditionalWeakTable<ScriptRuntime, ScriptLoggerService> RuntimeServices =
            new ConditionalWeakTable<ScriptRuntime, ScriptLoggerService>();
        private static readonly ScriptLoggerService SessionService = new ScriptLoggerService();
        private static readonly Encoding Utf8Encoding = new UTF8Encoding(false);
        private static readonly int ProcessId = Process.GetCurrentProcess().Id;

        private static int _minimumLevel = ReadConfiguredMinimumLevel();
        private static bool _fileLoggingEnabled = ReadConfiguredFileLogging();

        private static readonly object DefaultLogPathLock = new object();
        private static string _cachedDefaultLogPath;

        private readonly WeakReference<ScriptRuntime> _runtime;
        private readonly bool _runtimeBound;
        private bool _hasErrors;

        private ScriptLoggerService() { }

        private ScriptLoggerService(ScriptRuntime runtime) {
            _runtime = new WeakReference<ScriptRuntime>(runtime);
            _runtimeBound = true;
        }

        public static ScriptLoggerService GetDefault() {
            return SessionService;
        }

        public static ScriptLoggerService GetForRuntime(ScriptRuntime runtime) {
            if (runtime == null || runtime.IsDisposed)
                return SessionService;

            return RuntimeServices.GetValue(runtime, item => new ScriptLoggerService(item));
        }

        public bool HasErrors {
            get {
                lock (StateLock)
                    return _hasErrors;
            }
        }

        public int GetMinimumLevel() {
            lock (StateLock)
                return _minimumLevel;
        }

        public void SetMinimumLevel(int level) {
            lock (StateLock)
                _minimumLevel = level;
        }

        public void SetFileLogging(bool enabled) {
            lock (StateLock)
                _fileLoggingEnabled = enabled;
        }

        public bool IsEnabled(int level) {
            var runtime = GetActiveRuntime();
            if (_runtimeBound && runtime == null)
                return false;

            return IsVisibleEnabled(level, runtime)
                || IsDefaultFileLoggingEnabled()
                || !string.IsNullOrWhiteSpace(runtime?.ScriptRuntimeConfigs?.LogFilePath);
        }

        public bool IsVisibleEnabled(int level) {
            var runtime = GetActiveRuntime();
            if (_runtimeBound && runtime == null)
                return false;

            return IsVisibleEnabled(level, runtime);
        }

        public void Log(string loggerName, int level, string message) {
            Log(loggerName, level, message, allowWindowCreation: true);
        }

        // Forwarded loader/NLog records pass allowWindowCreation: false so they still persist
        // to disk and reach an already-open console, but never spawn a session window the user
        // never opened. Direct script output keeps the default and creates windows as before.
        public void Log(string loggerName, int level, string message, bool allowWindowCreation) {
            try {
                var runtime = GetActiveRuntime();
                if (_runtimeBound && runtime == null)
                    return;

                var normalizedLevel = NormalizeLevel(level);
                var normalizedName = string.IsNullOrEmpty(loggerName) ? "root" : loggerName;
                var normalizedMessage = message ?? string.Empty;
                var visible = IsVisibleEnabled(level, runtime);
                var explicitLogPath = runtime?.ScriptRuntimeConfigs?.LogFilePath;
                var defaultLogPath = IsDefaultFileLoggingEnabled()
                    ? GetDefaultLogFilePath(runtime)
                    : null;

                if (!visible && string.IsNullOrWhiteSpace(explicitLogPath)
                        && string.IsNullOrWhiteSpace(defaultLogPath))
                    return;

                if (normalizedLevel == ScriptLogLevel.Error
                        || normalizedLevel == ScriptLogLevel.Critical) {
                    lock (StateLock)
                        _hasErrors = true;
                }

                if (visible && !(runtime?.ScriptRuntimeConfigs?.SuppressOutput ?? false))
                    WriteOutput(runtime, normalizedLevel, normalizedName, normalizedMessage,
                        allowWindowCreation);

                var hasFileSink = !string.IsNullOrWhiteSpace(explicitLogPath)
                    || !string.IsNullOrWhiteSpace(defaultLogPath);
                if (hasFileSink) {
                    var fileEntry = FormatFileEntry(
                        runtime,
                        normalizedLevel,
                        normalizedName,
                        normalizedMessage);
                    AppendFile(explicitLogPath, fileEntry);
                    if (!PathsEqual(explicitLogPath, defaultLogPath))
                        AppendFile(defaultLogPath, fileEntry);
                }
            }
            catch {
                // Logging failures must never interrupt command execution.
            }
        }

        private ScriptRuntime GetActiveRuntime() {
            if (!_runtimeBound || _runtime == null)
                return null;

            ScriptRuntime runtime;
            if (!_runtime.TryGetTarget(out runtime) || runtime == null || runtime.IsDisposed)
                return null;

            return runtime;
        }

        private static bool IsVisibleEnabled(int level, ScriptRuntime runtime) {
            var minimumLevel = runtime?.ScriptRuntimeConfigs?.DebugMode ?? false
                ? (int)ScriptLogLevel.Debug
                : GetSharedMinimumLevel();
            return level >= minimumLevel;
        }

        private static int GetSharedMinimumLevel() {
            lock (StateLock)
                return _minimumLevel;
        }

        private static bool IsDefaultFileLoggingEnabled() {
            lock (StateLock)
                return _fileLoggingEnabled;
        }

        private static ScriptLogLevel NormalizeLevel(int level) {
            if (level == (int)ScriptLogLevel.Success)
                return ScriptLogLevel.Success;
            if (level >= (int)ScriptLogLevel.Critical)
                return ScriptLogLevel.Critical;
            if (level >= (int)ScriptLogLevel.Error)
                return ScriptLogLevel.Error;
            if (level >= (int)ScriptLogLevel.Warning)
                return ScriptLogLevel.Warning;
            if (level >= (int)ScriptLogLevel.Deprecate)
                return ScriptLogLevel.Deprecate;
            if (level >= (int)ScriptLogLevel.Info)
                return ScriptLogLevel.Info;
            return ScriptLogLevel.Debug;
        }

        private static void WriteOutput(
            ScriptRuntime runtime,
            ScriptLogLevel level,
            string loggerName,
            string message,
            bool allowWindowCreation) {
            var output = ScriptOutput.GetForRuntime(runtime);
            // File persistence is handled by the caller; a forwarded record must not be the
            // reason an output window appears, so drop it when none is already open.
            if (!allowWindowCreation && !output.IsWindowReady)
                return;
            var rendered = FormatVisibleEntry(level, loggerName, message);
            output.write_log_record(
                rendered,
                level == ScriptLogLevel.Error || level == ScriptLogLevel.Critical);
        }

        private static string FormatVisibleEntry(
            ScriptLogLevel level,
            string loggerName,
            string message) {
            var levelName = GetLevelName(level);
            if (level == ScriptLogLevel.Debug || level == ScriptLogLevel.Info)
                return string.Format("{0} [{1}] {2}", levelName, loggerName, message);

            var style = GetVisibleStyle(level);
            var header = level == ScriptLogLevel.Success || level == ScriptLogLevel.Deprecate
                ? string.Format(
                    "&clt;strong&cgt;{0}&clt;/strong&cgt;{1}{2}",
                    levelName,
                    Environment.NewLine,
                    message)
                : string.Format(
                    "&clt;strong&cgt;{0}&clt;/strong&cgt; [{1}] {2}",
                    levelName,
                    loggerName,
                    message);
            return string.Format(
                "&clt;div class=\"logdefault {0}\"&cgt;{1}&clt;/div&cgt;",
                style,
                header);
        }

        private static string GetVisibleStyle(ScriptLogLevel level) {
            switch (level) {
                case ScriptLogLevel.Success:
                    return "logsuccess";
                case ScriptLogLevel.Error:
                    return "logerror";
                case ScriptLogLevel.Warning:
                    return "logwarning";
                case ScriptLogLevel.Critical:
                    return "logcritical";
                case ScriptLogLevel.Deprecate:
                    return "logdeprecate";
                default:
                    return "logdefault";
            }
        }

        private static string FormatFileEntry(
            ScriptRuntime runtime,
            ScriptLogLevel level,
            string loggerName,
            string message) {
            var commandName = runtime?.ScriptData?.CommandName;
            var loggerLabel = string.IsNullOrEmpty(commandName)
                ? loggerName
                : string.Format("<{0}> {1}", commandName, loggerName);
            return string.Format(
                CultureInfo.InvariantCulture,
                "{0} {1} [{2}] {3}{4}",
                DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss,fff", CultureInfo.InvariantCulture),
                GetLevelName(level),
                loggerLabel,
                message,
                Environment.NewLine);
        }

        private static string GetLevelName(ScriptLogLevel level) {
            return level.ToString().ToUpperInvariant();
        }

        private static void AppendFile(string path, string entry) {
            if (string.IsNullOrWhiteSpace(path))
                return;

            lock (FileLock) {
                try {
                    var directory = Path.GetDirectoryName(path);
                    if (!string.IsNullOrEmpty(directory))
                        Directory.CreateDirectory(directory);

                    using (var stream = new FileStream(
                            path,
                            FileMode.Append,
                            FileAccess.Write,
                            FileShare.ReadWrite))
                    using (var writer = new StreamWriter(stream, Utf8Encoding))
                        writer.Write(entry);
                }
                catch {
                    // File logging is best effort by design.
                }
            }
        }

        /// <summary>
        /// Path of the session's default runtime log file
        /// (<c>%APPDATA%\pyRevit\{majorVersion}\pyRevit_{majorVersion}_{pid}_runtime.log</c>),
        /// or null if it can't be resolved. Exposed so tools (e.g. the DevTools Logs viewer)
        /// can locate and pre-select the active session's log.
        /// </summary>
        public static string GetDefaultLogFilePath() {
            return GetDefaultLogFilePath(null);
        }

        private static string GetDefaultLogFilePath(ScriptRuntime runtime) {
            try {
                // Resolve once per process: the runtime log must stay a single file even if the
                // seeded Revit version string changes mid-session.
                lock (DefaultLogPathLock) {
                    if (_cachedDefaultLogPath != null)
                        return _cachedDefaultLogPath;

                    var revitVersion = runtime?.EnvDict?.RevitVersion;
                    if (string.IsNullOrEmpty(revitVersion))
                        revitVersion = new EnvDictionary().RevitVersion;
                    if (string.IsNullOrEmpty(revitVersion))
                        return null;

                    // Normalize to the major version ("2025.4.10" -> "2025") so the log lands in
                    // %APPDATA%\pyRevit\{major}\ — the canonical per-version appdata folder pyRevit
                    // and the DevTools Logs viewer use (and which pyRevit's 4-digit file matching
                    // expects), regardless of whether the seeded value is the subversion.
                    var majorVersion = revitVersion.Split('.')[0];

                    var appData = Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData);
                    var fileName = string.Format(
                        "{0}_{1}_{2}_runtime.log",
                        PyRevitLabsConsts.ProductName,
                        majorVersion,
                        ProcessId);
                    var path = Path.Combine(appData, PyRevitLabsConsts.AppdataDirName, majorVersion, fileName);

                    _cachedDefaultLogPath = path;
                    return path;
                }
            }
            catch {
                return null;
            }
        }

        private static bool PathsEqual(string first, string second) {
            if (string.IsNullOrWhiteSpace(first) || string.IsNullOrWhiteSpace(second))
                return false;

            try {
                return string.Equals(
                    Path.GetFullPath(first),
                    Path.GetFullPath(second),
                    StringComparison.OrdinalIgnoreCase);
            }
            catch {
                return string.Equals(first, second, StringComparison.OrdinalIgnoreCase);
            }
        }

        private static int ReadConfiguredMinimumLevel() {
            try {
                var configuredLevel = PyRevitConfigs.GetLoggingLevel();
                if (configuredLevel == PyRevitLogLevels.Debug)
                    return (int)ScriptLogLevel.Debug;
                if (configuredLevel == PyRevitLogLevels.Verbose)
                    return (int)ScriptLogLevel.Info;
            }
            catch { }

            return (int)ScriptLogLevel.Warning;
        }

        private static bool ReadConfiguredFileLogging() {
            try {
                return PyRevitConfigs.GetFileLogging();
            }
            catch {
                return false;
            }
        }
    }
}
