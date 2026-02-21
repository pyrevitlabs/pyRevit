#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
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
                [KeyCPYVersion]         = "3.12.3",    // Known default for the bundled CPython engine

                [KeyLoggingLevel]       = config.LoggingLevel,
                [KeyFileLogging]        = config.FileLogging,

                [KeyTelemetryState]     = config.TelemetryState,
                [KeyTelemetryUTC]       = config.TelemetryUTCTimeStamps,
                [KeyTelemetryDir]       = config.TelemetryFilePath,
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

        private static string ReadPyRevitVersion(string pyRevitRoot)
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

        private static string ReadIPYVersion(string pyRevitRoot)
        {
            // IronPython engines live under bin/ inside the repo root as well as beside this DLL.
            // Check both the bin/ folder of the repo and the directory of the executing assembly.
            var candidateDirs = new List<string>();

            if (!string.IsNullOrEmpty(pyRevitRoot))
            {
                candidateDirs.Add(Path.Combine(pyRevitRoot, "bin", "IPY342"));
                candidateDirs.Add(Path.Combine(pyRevitRoot, "bin", "IPY2712PR"));
                candidateDirs.Add(Path.Combine(pyRevitRoot, "bin"));
            }

            var selfDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            if (!string.IsNullOrEmpty(selfDir))
                candidateDirs.Add(selfDir);

            foreach (var dir in candidateDirs)
            {
                var dll = Path.Combine(dir, "IronPython.dll");
                if (!File.Exists(dll)) continue;
                try
                {
                    var ver = AssemblyName.GetAssemblyName(dll).Version;
                    if (ver != null) return ver.ToString();
                }
                catch { /* try next candidate */ }
            }

            return "Unknown";
        }
    }
}
