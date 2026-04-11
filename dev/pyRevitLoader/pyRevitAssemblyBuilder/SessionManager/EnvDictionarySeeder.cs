#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Diagnostics;
using System.Reflection;
using Autodesk.Revit.UI;
using pyRevitExtensionParser;

namespace pyRevitAssemblyBuilder.SessionManager
{
    /// <summary>
    /// Seeds the AppDomain environment dictionary consumed by the pyRevit Runtime.
    /// <para>
    /// The Runtime's <c>EnvDictionary</c> class reads session state (UUID, versions, telemetry
    /// settings, etc.) from an <c>IronPython.Runtime.PythonDictionary</c> stored in the AppDomain
    /// under the key <c>"PYREVITEnvVarsDict"</c>.  Because this loader project has no compile-time
    /// reference to IronPython (<c>UseIronPython=false</c>), we delegate the actual
    /// <c>PythonDictionary</c> creation to the Runtime via <c>EnvDictionary.Seed()</c>, which is
    /// invoked here through reflection — the same pattern already used for
    /// <c>ScriptExecutor.Initialize()</c> and <c>ScriptExecutor.ExecuteScript()</c>.
    /// </para>
    /// </summary>
    internal static class EnvDictionarySeeder
    {
        // Env-dict key string values.  These must match EnvDictionaryKeys in the Runtime
        // (dev/pyRevitLabs.PyRevit.Runtime/EnvVariables.cs).  The prefix is "PYREVIT" because
        // PyRevitLabsConsts.ProductName = "PYREVIT".
        private const string KeySessionUUID          = "PYREVIT_UUID";
        private const string KeyRevitVersion         = "PYREVIT_APPVERSION";
        private const string KeyVersion              = "PYREVIT_VERSION";
        private const string KeyClone                = "PYREVIT_CLONE";
        private const string KeyIPYVersion           = "PYREVIT_IPYVERSION";
        private const string KeyCPYVersion           = "PYREVIT_CPYVERSION";
        private const string KeyLoggingLevel         = "PYREVIT_LOGGINGLEVEL";
        private const string KeyFileLogging          = "PYREVIT_FILELOGGING";
        private const string KeyTelemetryState       = "PYREVIT_TELEMETRYSTATE";
        private const string KeyTelemetryUTC         = "PYREVIT_TELEMETRYUTCTIMESTAMPS";
        private const string KeyTelemetryFileDir     = "PYREVIT_TELEMETRYDIR";
        private const string KeyTelemetryFile        = "PYREVIT_TELEMETRYFILE";
        private const string KeyTelemetryServer      = "PYREVIT_TELEMETRYSERVER";
        private const string KeyTelemetryHooks       = "PYREVIT_TELEMETRYINCLUDEHOOKS";
        private const string KeyAppTelemetryState    = "PYREVIT_APPTELEMETRYSTATE";
        private const string KeyAppTelemetryServer   = "PYREVIT_APPTELEMETRYSERVER";
        private const string KeyAppTelemetryFlags    = "PYREVIT_APPTELEMETRYEVENTFLAGS";
        private const string KeyAutoUpdating         = "PYREVIT_AUTOUPDATE";
        private const string KeyOutputStyleSheet     = "PYREVIT_STYLESHEET";

        /// <summary>
        /// Builds the session environment dictionary and stores it in the AppDomain via a reflection
        /// call to <c>EnvDictionary.Seed()</c> in the Runtime assembly.
        /// </summary>
        /// <param name="uiApp">The active Revit UIApplication (provides version number).</param>
        /// <param name="runtimeAssembly">
        /// The already-loaded <c>pyRevitLabs.PyRevit.Runtime</c> assembly.
        /// </param>
        /// <param name="pyRevitRoot">
        /// Root directory of the pyRevit repository (used to read the version file and locate engine
        /// binaries).  May be empty — the seeder degrades gracefully to "Unknown" where needed.
        /// </param>
        public static void Seed(UIApplication uiApp, Assembly runtimeAssembly, string pyRevitRoot)
        {
            var config = PyRevitConfig.Load();

            var values = new Dictionary<string, object>
            {
                [KeySessionUUID]        = Guid.NewGuid().ToString(),
                [KeyRevitVersion]       = uiApp?.Application?.VersionNumber ?? string.Empty,
                [KeyVersion]            = ReadPyRevitVersion(pyRevitRoot),
                [KeyClone]              = "Unknown",
                [KeyIPYVersion]         = ReadIPYVersion(pyRevitRoot),
                [KeyCPYVersion]         = ReadCPYVersion(pyRevitRoot),

                // Fix for #3203: PyRevitConfig.LoggingLevel returns a pyRevit enum
                // (0=Quiet, 1=Verbose, 2=Debug) but the Python logger reads this
                // env var as a Python logging module level (10=DEBUG, 20=INFO, 30=WARNING).
                // Translate to avoid corrupting the Python logging threshold.
                [KeyLoggingLevel]       = ToPythonLoggingLevel(config.LoggingLevel),
                [KeyFileLogging]        = config.FileLogging,

                [KeyTelemetryState]     = config.TelemetryState,
                [KeyTelemetryUTC]       = config.TelemetryUTCTimeStamps,
                [KeyTelemetryFileDir]   = config.TelemetryFilePath,
                [KeyTelemetryFile]      = string.Empty,
                [KeyTelemetryServer]    = config.TelemetryServerUrl,
                [KeyTelemetryHooks]     = config.TelemetryIncludeHooks,

                [KeyAppTelemetryState]  = config.AppTelemetryState,
                [KeyAppTelemetryServer] = config.AppTelemetryServerUrl,
                [KeyAppTelemetryFlags]  = config.AppTelemetryEventFlags,

                [KeyAutoUpdating]       = config.AutoUpdate,
                [KeyOutputStyleSheet]   = config.OutputStyleSheet,
            };

            // Delegate to EnvDictionary.Seed() in the Runtime, which owns PythonDictionary creation.
            var envDictType = runtimeAssembly.GetType("PyRevitLabs.PyRevit.Runtime.EnvDictionary")
                ?? throw new InvalidOperationException("Cannot find type PyRevitLabs.PyRevit.Runtime.EnvDictionary in runtime assembly.");

            var seedMethod = envDictType.GetMethod(
                "Seed",
                BindingFlags.Public | BindingFlags.Static,
                null,
                new[] { typeof(Dictionary<string, object>) },
                null)
                ?? throw new InvalidOperationException("Cannot find EnvDictionary.Seed(Dictionary<string, object>) method.");

            seedMethod.Invoke(null, new object[] { values });
        }

        /// <summary>
        /// Converts PyRevitConfig's logging level enum (0=Quiet, 1=Verbose, 2=Debug)
        /// to Python's logging module level (30=WARNING, 20=INFO, 10=DEBUG).
        /// <para>
        /// Python's logger (pyrevitlib/pyrevit/coreutils/logger.py) reads PYREVIT_LOGGINGLEVEL
        /// and compares it directly: <c>record.levelno >= _curlevel</c>.  The Python logging
        /// constants are DEBUG=10, INFO=20, WARNING=30.  If we store 0 (pyRevit Quiet) the
        /// comparison <c>10 >= 0</c> is always true — every message passes, which forces the
        /// console window open.
        /// </para>
        /// </summary>
        internal static int ToPythonLoggingLevel(int pyrevitLevel)
        {
            switch (pyrevitLevel)
            {
                case 2:  return 10;   // Debug   → logging.DEBUG
                case 1:  return 20;   // Verbose → logging.INFO
                default: return 30;   // Quiet   → logging.WARNING (Python default)
            }
        }

        internal static string ReadPyRevitVersion(string pyRevitRoot)
        {
            if (string.IsNullOrEmpty(pyRevitRoot))
                return "Unknown";

            // pyRevit version is stored as a bare version string in pyrevitlib/pyrevit/version
            var versionFile = Path.Combine(pyRevitRoot, "pyrevitlib", "pyrevit", "version");
            if (File.Exists(versionFile))
            {
                try { return File.ReadAllText(versionFile).Trim(); }
                catch { /* fall through to Unknown */ }
            }

            return "Unknown";
        }

        internal static string ReadIPYVersion(string pyRevitRoot)
        {
            // IronPython engines live under bin/{netcore|netfx}/engines/{IPY342|IPY2712PR}/.
            // IPY342 ships as "IronPython.dll"; IPY2712PR ships as "pyRevitLabs.IronPython.dll".
            // Check the executing assembly's directory FIRST — it sits in the active engine
            // folder, so its sibling IronPython DLL is the one actually in use.  Fall back to
            // the repo engine directories if the executing assembly path is unavailable.
            var candidateDirs = new List<string>();

            // Priority 1: active engine directory (same folder as this DLL)
            var selfDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            if (!string.IsNullOrEmpty(selfDir))
                candidateDirs.Add(selfDir);

            // Priority 2: all known engine directories under the repo root
            if (!string.IsNullOrEmpty(pyRevitRoot))
            {
                foreach (var net in new[] { "netcore", "netfx" })
                {
                    candidateDirs.Add(Path.Combine(pyRevitRoot, "bin", net, "engines", "IPY342"));
                    candidateDirs.Add(Path.Combine(pyRevitRoot, "bin", net, "engines", "IPY2712PR"));
                }
            }

            // Check both DLL name variants in each candidate directory
            var dllNames = new[] { "IronPython.dll", "pyRevitLabs.IronPython.dll" };

            foreach (var dir in candidateDirs)
            {
                foreach (var dllName in dllNames)
                {
                    var dll = Path.Combine(dir, dllName);
                    if (!File.Exists(dll)) continue;
                    try
                    {
                        var ver = AssemblyName.GetAssemblyName(dll).Version;
                        if (ver != null) return ver.ToString();
                    }
                    catch (Exception ex) { Trace.WriteLine($"ReadIPYVersion: skipping {dll}: {ex.Message}"); }
                }
            }

            return "Unknown";
        }
        /// <summary>
        /// Reads the active CPython engine version as an integer string (e.g. "3123")
        /// by scanning the <c>bin/cengines/CPY{version}</c> directories and returning
        /// the highest version found. Returns "0" if no CPython engine is installed.
        /// </summary>
        internal static string ReadCPYVersion(string pyRevitRoot)
        {
            if (string.IsNullOrEmpty(pyRevitRoot))
                return "0";

            try
            {
                var cenginesDir = Path.Combine(pyRevitRoot, "bin", "cengines");
                if (!Directory.Exists(cenginesDir))
                    return "0";

                int maxVersion = 0;
                foreach (var dir in Directory.GetDirectories(cenginesDir, "CPY*"))
                {
                    var dirName = Path.GetFileName(dir);
                    if (int.TryParse(dirName.Substring(3), out int ver) && ver > maxVersion)
                        maxVersion = ver;
                }

                return maxVersion > 0 ? maxVersion.ToString() : "0";
            }
            catch (Exception ex)
            {
                Trace.WriteLine($"ReadCPYVersion: {ex.Message}");
                return "0";
            }
        }
    }
}
