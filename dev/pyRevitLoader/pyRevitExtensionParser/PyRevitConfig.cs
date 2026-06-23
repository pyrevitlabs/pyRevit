using System;
using System.Collections.Generic;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Json;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Adapter over the shared pyRevit configuration service, exposing the typed
    /// core/telemetry settings and per-extension sections the loader reads.
    /// Backed by one process-wide instance so the loader, CLI, and Python engines
    /// agree on the same file. Stored values are decoded tolerantly: a
    /// JSON-encoded value is unescaped, a bare legacy value is returned as-is.
    /// </summary>
    public class PyRevitConfig
    {
        private readonly IConfiguration _config;

        /// <summary>
        /// Cached default instance over the shared service. Cleared via
        /// <see cref="ClearCache"/> at the start of each session load so config
        /// changes made between reloads are picked up. Custom-path calls bypass it.
        /// </summary>
        private static volatile PyRevitConfig _defaultInstance;
        private static readonly object _cacheLock = new object();

        /// <summary>
        /// Gets the full path to the configuration file.
        /// </summary>
        public string ConfigPath => _config.ConfigurationPath;

        /// <summary>
        /// Initializes a new instance over the given configuration source.
        /// </summary>
        public PyRevitConfig(IConfiguration config)
        {
            _config = config ?? throw new ArgumentNullException(nameof(config));
        }

        // ── value access ──────────────────────────────────────────────────────────

        private string ReadRaw(string section, string key)
        {
            return _config.GetRawValueOrDefault(section, key, null);
        }

        // Decodes a stored string the way Python user_config does: a JSON-encoded
        // value is unescaped, a bare legacy value is returned unchanged.
        private string ReadString(string section, string key)
        {
            var raw = ReadRaw(section, key);
            if (string.IsNullOrEmpty(raw))
                return raw;
            try
            {
                return JsonConvert.DeserializeObject<string>(raw) ?? raw;
            }
            catch
            {
                return raw;
            }
        }

        private bool ReadBool(string section, string key, bool defaultValue)
        {
            return bool.TryParse(ReadRaw(section, key), out var result) ? result : defaultValue;
        }

        private int ReadInt(string section, string key, int defaultValue)
        {
            var raw = ReadRaw(section, key);
            if (string.IsNullOrEmpty(raw))
                return defaultValue;
            return int.TryParse(raw.Trim().Trim('"'), out var result) ? result : defaultValue;
        }

        private void Write(string section, string key, string jsonValue)
        {
            _config.SetRawValue(section, key, jsonValue);
            _config.SaveConfiguration();
        }

        private static string JsonString(string value)
        {
            return JsonConvert.SerializeObject(value ?? string.Empty);
        }

        private static string JsonBool(bool value)
        {
            return value ? "true" : "false";
        }

        // ── core ────────────────────────────────────────────────────────────────

        /// <summary>
        /// Gets or sets the user extensions configuration as a raw list string.
        /// Use <see cref="UserExtensionsList"/> for parsed list access.
        /// </summary>
        public string UserExtensions
        {
            get
            {
                var value = ReadRaw("core", "userextensions");
                return string.IsNullOrEmpty(value) ? null : value.Trim();
            }
            set { Write("core", "userextensions", value); }
        }

        /// <summary>
        /// Gets or sets the user's locale preference (e.g. "en_us").
        /// </summary>
        public string UserLocale
        {
            get
            {
                var value = ReadString("core", "user_locale");
                if (string.IsNullOrEmpty(value))
                    return null;

                var normalized = NormalizeLocaleValue(value);
                return string.IsNullOrEmpty(normalized) ? null : normalized;
            }
            set { Write("core", "user_locale", JsonString(value)); }
        }

        /// <summary>
        /// Gets or sets whether the new loader architecture is enabled (default true).
        /// </summary>
        public bool NewLoader
        {
            get { return ReadBool("core", "new_loader", true); }
            set { Write("core", "new_loader", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets whether Rocket Mode is enabled (default false).
        /// </summary>
        public bool RocketMode
        {
            get { return ReadBool("core", "rocketmode", false); }
            set { Write("core", "rocketmode", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets whether to read script-level metadata dunders (default true).
        /// </summary>
        public bool ReadScriptMetadata
        {
            get { return ReadBool("core", "read_script_metadata", true); }
            set { Write("core", "read_script_metadata", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets whether to load beta/experimental commands (default false).
        /// Reads <c>loadbeta</c> first, falling back to legacy <c>load_beta</c>.
        /// </summary>
        public bool LoadBeta
        {
            get
            {
                var value = ReadRaw("core", "loadbeta");
                if (string.IsNullOrWhiteSpace(value))
                    value = ReadRaw("core", "load_beta");
                return TryParseConfigBool(value, out var result) && result;
            }
            set
            {
                _config.SetRawValue("core", "loadbeta", JsonBool(value));
                // Drop the legacy key so the file does not carry two competing entries.
                _config.RemoveOption("core", "load_beta");
                _config.SaveConfiguration();
            }
        }

        /// <summary>
        /// Gets the logging verbosity level (0 = Quiet, 1 = Verbose, 2 = Debug),
        /// derived from the [core] verbose and debug keys.
        /// </summary>
        public int LoggingLevel
        {
            get
            {
                if (ReadBool("core", "debug", false)) return 2;
                if (ReadBool("core", "verbose", false)) return 1;
                return 0;
            }
        }

        /// <summary>
        /// Gets or sets whether to write log output to a file.
        /// </summary>
        public bool FileLogging
        {
            get { return ReadBool("core", "filelogging", false); }
            set { Write("core", "filelogging", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets whether pyRevit should auto-update on startup.
        /// </summary>
        public bool AutoUpdate
        {
            get { return ReadBool("core", "autoupdate", false); }
            set { Write("core", "autoupdate", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets the path to a custom CSS stylesheet for output windows.
        /// </summary>
        public string OutputStyleSheet
        {
            get
            {
                var value = ReadString("core", "outputstylesheet");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set { Write("core", "outputstylesheet", JsonString(value)); }
        }

        /// <summary>
        /// Gets or sets the timeout (seconds) for displaying startup log messages (default 10).
        /// </summary>
        public int StartupLogTimeout
        {
            get { return ReadInt("core", "startuplogtimeout", 10); }
            set { Write("core", "startuplogtimeout", value.ToString()); }
        }

        /// <summary>
        /// Gets or sets the user extensions as a parsed list of paths.
        /// </summary>
        public List<string> UserExtensionsList
        {
            get { return PythonListParser.Parse(ReadRaw("core", "userextensions")); }
            set { Write("core", "userextensions", PythonListParser.ToPythonListString(value)); }
        }

        // ── telemetry ─────────────────────────────────────────────────────────────

        /// <summary>
        /// Gets or sets whether script-execution telemetry is enabled.
        /// </summary>
        public bool TelemetryState
        {
            get { return ReadBool("telemetry", "active", false); }
            set { Write("telemetry", "active", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets whether telemetry timestamps are recorded in UTC (default true).
        /// </summary>
        public bool TelemetryUTCTimeStamps
        {
            get { return ReadBool("telemetry", "utc_timestamps", true); }
            set { Write("telemetry", "utc_timestamps", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets the directory path for telemetry log files.
        /// </summary>
        public string TelemetryFilePath
        {
            get
            {
                var value = ReadString("telemetry", "telemetry_file_dir");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set { Write("telemetry", "telemetry_file_dir", JsonString(value)); }
        }

        /// <summary>
        /// Gets or sets the URL of the telemetry server.
        /// </summary>
        public string TelemetryServerUrl
        {
            get
            {
                var value = ReadString("telemetry", "telemetry_server_url");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set { Write("telemetry", "telemetry_server_url", JsonString(value)); }
        }

        /// <summary>
        /// Gets or sets whether hook script executions are included in telemetry.
        /// </summary>
        public bool TelemetryIncludeHooks
        {
            get { return ReadBool("telemetry", "include_hooks", false); }
            set { Write("telemetry", "include_hooks", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets whether application-event telemetry is enabled.
        /// </summary>
        public bool AppTelemetryState
        {
            get { return ReadBool("telemetry", "active_app", false); }
            set { Write("telemetry", "active_app", JsonBool(value)); }
        }

        /// <summary>
        /// Gets or sets the URL of the application-event telemetry server.
        /// </summary>
        public string AppTelemetryServerUrl
        {
            get
            {
                var value = ReadString("telemetry", "apptelemetry_server_url");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set { Write("telemetry", "apptelemetry_server_url", JsonString(value)); }
        }

        /// <summary>
        /// Gets or sets the event-flags bitmask for application telemetry.
        /// </summary>
        public string AppTelemetryEventFlags
        {
            get
            {
                var value = ReadString("telemetry", "apptelemetry_event_flags");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set { Write("telemetry", "apptelemetry_event_flags", JsonString(value)); }
        }

        // ── loading & per-extension config ────────────────────────────────────────

        /// <summary>
        /// Loads the shared pyRevit configuration, or a one-off configuration from
        /// <paramref name="customPath"/> (used by tests). The default instance is
        /// cached for the session; call <see cref="ClearCache"/> to force a re-read.
        /// </summary>
        public static PyRevitConfig Load(string customPath = null)
        {
            // Custom-path calls are never cached and never touch the shared service.
            if (!string.IsNullOrEmpty(customPath))
                return new PyRevitConfig(IniConfiguration.Create(customPath));

            if (_defaultInstance != null)
                return _defaultInstance;

            lock (_cacheLock)
            {
                if (_defaultInstance != null)
                    return _defaultInstance;

                _defaultInstance = new PyRevitConfig(
                    PyRevitConfigService.GetShared()[ConfigurationService.DefaultConfigurationName]);
                return _defaultInstance;
            }
        }

        /// <summary>
        /// Clears the cached default instance and the shared service cache so the
        /// next <see cref="Load()"/> re-reads from disk. Called at session reload
        /// via <see cref="ExtensionParser.ClearAllCaches"/>.
        /// </summary>
        public static void ClearCache()
        {
            lock (_cacheLock)
            {
                _defaultInstance = null;
            }
            PyRevitConfigService.Reload();
        }

        /// <summary>
        /// Retrieves the configuration for a specific extension by its name
        /// (without the .extension or .lib suffix), or null if not configured.
        /// </summary>
        public ExtensionConfig ParseExtensionByName(string extensionName)
        {
            var possibleSections = new[]
            {
                $"{extensionName}.extension",
                $"{extensionName}.lib"
            };

            foreach (var section in possibleSections)
            {
                if (!_config.HasSection(section))
                    continue;

                return new ExtensionConfig
                {
                    Name = extensionName,
                    Disabled = ReadBool(section, "disabled", false),
                    PrivateRepo = ReadBool(section, "private_repo", false),
                    Username = ReadString(section, "username"),
                    Password = ReadString(section, "password")
                };
            }

            return null;
        }

        private static string NormalizeLocaleValue(string rawValue)
        {
            if (string.IsNullOrEmpty(rawValue))
                return null;

            var value = rawValue.Trim();

            if (string.IsNullOrEmpty(value))
                return null;

            value = value.Replace('-', '_').ToLowerInvariant();
            return LocaleSupport.NormalizeLocaleKey(value);
        }

        /// <summary>
        /// Parses booleans from config values (json-style plus common variants).
        /// </summary>
        private static bool TryParseConfigBool(string raw, out bool result)
        {
            result = false;
            if (string.IsNullOrWhiteSpace(raw))
                return false;

            var v = raw.Trim();
            if (v.Length >= 2 &&
                ((v[0] == '"' && v[v.Length - 1] == '"') ||
                 (v[0] == '\'' && v[v.Length - 1] == '\'')))
            {
                v = v.Substring(1, v.Length - 2).Trim();
            }

            if (bool.TryParse(v, out result))
                return true;

            if (v.Equals("1", StringComparison.Ordinal) ||
                v.Equals("yes", StringComparison.OrdinalIgnoreCase) ||
                v.Equals("on", StringComparison.OrdinalIgnoreCase))
            {
                result = true;
                return true;
            }

            if (v.Equals("0", StringComparison.Ordinal) ||
                v.Equals("no", StringComparison.OrdinalIgnoreCase) ||
                v.Equals("off", StringComparison.OrdinalIgnoreCase))
            {
                result = false;
                return true;
            }

            return false;
        }
    }

    /// <summary>
    /// Represents the configuration settings for a pyRevit extension.
    /// Contains information about extension state, repository access, and authentication.
    /// </summary>
    public class ExtensionConfig
    {
        /// <summary>
        /// Gets or sets the name of the extension (without the .extension or .lib suffix).
        /// </summary>
        /// <example>
        /// "pyRevitCore" (not "pyRevitCore.extension")
        /// </example>
        public string Name { get; set; }

        /// <summary>
        /// Gets or sets whether the extension is disabled.
        /// </summary>
        /// <remarks>
        /// When true, the extension will not be loaded by pyRevit.
        /// Defaults to false if not specified in configuration.
        /// </remarks>
        public bool Disabled { get; set; }

        /// <summary>
        /// Gets or sets whether this extension is hosted in a private repository.
        /// </summary>
        /// <remarks>
        /// Private repositories may require authentication credentials.
        /// See <see cref="Username"/> and <see cref="Password"/> properties.
        /// </remarks>
        public bool PrivateRepo { get; set; }

        /// <summary>
        /// Gets or sets the username for accessing a private repository.
        /// </summary>
        /// <remarks>
        /// Only used when <see cref="PrivateRepo"/> is true.
        /// May be null or empty for public repositories.
        /// </remarks>
        public string Username { get; set; }

        /// <summary>
        /// Gets or sets the password for accessing a private repository.
        /// </summary>
        /// <remarks>
        /// Only used when <see cref="PrivateRepo"/> is true.
        /// May be null or empty for public repositories.
        /// </remarks>
        public string Password { get; set; }
    }

    /// <summary>
    /// Represents engine-specific configuration for script execution.
    /// Controls how scripts are executed, including threading, scope, and engine-specific options.
    /// </summary>
    public class EngineConfig
    {
        /// <summary>
        /// Gets or sets the script engine type to use (e.g., "IronPython", "CPython").
        /// </summary>
        /// <remarks>
        /// <para>Specifies which Python runtime to use for executing scripts.</para>
        /// <para>Valid values: "IronPython" (default), "CPython"</para>
        /// <para>Other values may be supported in the future but are not guaranteed.</para>
        /// <para>Setting this property to null or empty clears any explicit override.</para>
        /// </remarks>
        private string _type;

        public string Type
        {
            get => string.IsNullOrEmpty(_type) ? "IronPython" : _type;
            set => _type = value;
        }

        /// <summary>
        /// Gets whether engine type was explicitly configured by user metadata.
        /// </summary>
        public bool HasTypeOverride => !string.IsNullOrWhiteSpace(_type);

        /// <summary>
        /// Gets or sets whether to use a clean engine scope for execution.
        /// </summary>
        /// <remarks>
        /// When true, each script execution gets a fresh, isolated engine scope.
        /// When false, the engine scope persists between executions (default).
        /// </remarks>
        public bool Clean { get; set; } = false;

        /// <summary>
        /// Gets or sets whether to enable full frame mode for debugging.
        /// </summary>
        /// <remarks>
        /// When true, provides more detailed stack traces and debugging information.
        /// May impact performance. Defaults to false.
        /// </remarks>
        public bool FullFrame { get; set; } = false;

        /// <summary>
        /// Gets or sets whether the engine scope should persist between executions.
        /// </summary>
        /// <remarks>
        /// When true, variables and state are maintained across multiple script runs.
        /// When false, each execution starts fresh. Defaults to false.
        /// </remarks>
        public bool Persistent { get; set; } = false;

        /// <summary>
        /// Gets or sets whether the script should execute on the main UI thread.
        /// </summary>
        /// <remarks>
        /// <para>When true, script executes synchronously on the main thread.</para>
        /// <para>When false or null, script may execute on a background thread.</para>
        /// <para>Use this for scripts that need direct UI interaction.</para>
        /// </remarks>
        public bool? MainThread { get; set; }

        /// <summary>
        /// Gets or sets whether to automate execution (Dynamo-specific).
        /// </summary>
        /// <remarks>
        /// <para>This is a Dynamo-specific synonym for <see cref="MainThread"/>.</para>
        /// <para>When true for Dynamo scripts, runs on main thread with automatic execution.</para>
        /// </remarks>
        public bool? Automate { get; set; }

        /// <summary>
        /// Gets or sets the path to a Dynamo script file (.dyn).
        /// </summary>
        /// <remarks>
        /// <para>Specifies a Dynamo graph file to execute.</para>
        /// <para>Can be an absolute path or relative to the command directory.</para>
        /// <para>Only applicable for Dynamo-based commands.</para>
        /// </remarks>
        /// <example>
        /// dynamo_path: "scripts/MyGraph.dyn"
        /// </example>
        public string DynamoPath { get; set; }

        /// <summary>
        /// Gets or sets whether to execute the Dynamo graph automatically.
        /// </summary>
        /// <remarks>
        /// <para>Defaults to true for backward compatibility.</para>
        /// <para>When true, the graph runs automatically after loading.</para>
        /// <para>When false, the graph is loaded but not executed.</para>
        /// </remarks>
        public bool? DynamoPathExec { get; set; } = true;

        /// <summary>
        /// Gets or sets whether to check for existing Dynamo instances before execution.
        /// </summary>
        /// <remarks>
        /// <para>When true, checks if Dynamo is already running.</para>
        /// <para>Defaults to false.</para>
        /// </remarks>
        public bool? DynamoPathCheckExisting { get; set; } = false;

        /// <summary>
        /// Gets or sets whether to force manual run mode for Dynamo graphs.
        /// </summary>
        /// <remarks>
        /// <para>When true, sets the graph to manual execution mode.</para>
        /// <para>When false or null, uses the graph's default run mode.</para>
        /// <para>Defaults to false.</para>
        /// </remarks>
        public bool? DynamoForceManualRun { get; set; } = false;

        /// <summary>
        /// Gets or sets additional node information for Dynamo model execution.
        /// </summary>
        /// <remarks>
        /// <para>Specifies which nodes to execute or configuration for nodes.</para>
        /// <para>Format and usage depend on Dynamo engine implementation.</para>
        /// </remarks>
        public string DynamoModelNodesInfo { get; set; }

        /// <summary>
        /// Gets whether the engine requires execution on the main thread.
        /// </summary>
        /// <remarks>
        /// <para>Returns true if either <see cref="MainThread"/> or <see cref="Automate"/> is true.</para>
        /// <para>This combines both generic and Dynamo-specific threading requirements.</para>
        /// </remarks>
        public bool RequiresMainThread => (MainThread ?? false) || (Automate ?? false);
    }
}
