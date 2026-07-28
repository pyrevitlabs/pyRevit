using System;
using System.Collections.Generic;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini;

using pyRevitLabs.Common;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Read-only facade over the shared pyRevit configuration service, exposing the
    /// typed core/telemetry settings and per-extension sections the loader reads.
    /// Backed by one process-wide instance so the loader, CLI, and Python engines
    /// agree on the same file. Core and telemetry values decode through the service
    /// so every reader interprets them identically; only the legacy Python-list and
    /// <c>load_beta</c> forms are still parsed here, pending the service learning them.
    /// </summary>
    public class PyRevitConfig
    {
        private readonly IConfiguration _config;

        // Per-extension settings are read through the shared configuration service
        // so the loader decodes them identically to the CLI and Python engines,
        // rather than maintaining a second decode path here.
        private IConfigurationService _service;

        /// <summary>
        /// Cached default instance over the shared service. Held only while it still
        /// wraps the configuration the shared store currently hands out, so a reload
        /// requested by any host (session load, the CLI, or a Python
        /// <c>user_config.reload()</c>) is picked up here too. Custom-path calls
        /// bypass it.
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

        // ── core ────────────────────────────────────────────────────────────────

        /// <summary>
        /// Gets the user's locale preference (e.g. "en_us"), normalized to a
        /// supported locale key or null.
        /// </summary>
        public string UserLocale
        {
            get
            {
                var value = AsService().Core.UserLocale;
                if (string.IsNullOrEmpty(value))
                    return null;

                var normalized = NormalizeLocaleValue(value);
                return string.IsNullOrEmpty(normalized) ? null : normalized;
            }
        }

        /// <summary>
        /// Gets whether the new loader architecture is enabled (default true).
        /// </summary>
        public bool NewLoader => AsService().Core.NewLoader ?? true;

        /// <summary>
        /// Gets whether Rocket Mode is enabled (default true).
        /// </summary>
        public bool RocketMode => AsService().Core.RocketMode ?? true;

        /// <summary>
        /// Gets whether to read script-level metadata dunders (default true).
        /// </summary>
        public bool ReadScriptMetadata => AsService().Core.ReadScriptMetadata ?? true;

        /// <summary>
        /// Gets whether to load beta/experimental commands (default false).
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
        }

        /// <summary>
        /// Gets the logging verbosity level (0 = Quiet, 1 = Verbose, 2 = Debug),
        /// derived from the [core] verbose and debug keys.
        /// </summary>
        public int LoggingLevel
        {
            get
            {
                var core = AsService().Core;
                if (core.Debug ?? false) return 2;
                if (core.Verbose ?? false) return 1;
                return 0;
            }
        }

        /// <summary>
        /// Gets whether to write log output to a file.
        /// </summary>
        public bool FileLogging => AsService().Core.FileLogging ?? false;

        /// <summary>
        /// Gets whether pyRevit should auto-update on startup.
        /// </summary>
        public bool AutoUpdate => AsService().Core.AutoUpdate ?? false;

        /// <summary>
        /// Gets the path to a custom CSS stylesheet for output windows.
        /// </summary>
        public string OutputStyleSheet
        {
            get
            {
                var value = AsService().Core.OutputStyleSheet;
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
        }

        /// <summary>
        /// Gets the timeout (seconds) for displaying startup log messages (default 10).
        /// </summary>
        public int StartupLogTimeout => AsService().Core.StartupLogTimeout ?? 10;

        /// <summary>
        /// Gets the user extensions as a parsed list of paths.
        /// </summary>
        public List<string> UserExtensionsList =>
            AsService().Core.UserExtensions ?? new List<string>();

        /// <summary>
        /// Gets the extension lookup sources as a parsed list of paths.
        /// </summary>
        public List<string> ExtensionLookupSources =>
            AsService().Environment.Sources ?? new List<string>();

        // ── telemetry ─────────────────────────────────────────────────────────────

        /// <summary>
        /// Gets whether script-execution telemetry is enabled.
        /// </summary>
        public bool TelemetryState => AsService().Telemetry.TelemetryStatus ?? false;

        /// <summary>
        /// Gets whether telemetry timestamps are recorded in UTC (default true).
        /// </summary>
        public bool TelemetryUTCTimeStamps => AsService().Telemetry.TelemetryUseUtcTimeStamps ?? true;

        /// <summary>
        /// Gets the directory path for telemetry log files.
        /// </summary>
        public string TelemetryFilePath
        {
            get
            {
                var value = AsService().Telemetry.TelemetryFileDir;
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
        }

        /// <summary>
        /// Gets the URL of the telemetry server.
        /// </summary>
        public string TelemetryServerUrl
        {
            get
            {
                var value = AsService().Telemetry.TelemetryServerUrl;
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
        }

        /// <summary>
        /// Gets whether hook script executions are included in telemetry.
        /// </summary>
        public bool TelemetryIncludeHooks => AsService().Telemetry.TelemetryIncludeHooks ?? false;

        /// <summary>
        /// Gets whether application-event telemetry is enabled.
        /// </summary>
        public bool AppTelemetryState => AsService().Telemetry.AppTelemetryStatus ?? false;

        /// <summary>
        /// Gets the URL of the application-event telemetry server.
        /// </summary>
        public string AppTelemetryServerUrl
        {
            get
            {
                var value = AsService().Telemetry.AppTelemetryServerUrl;
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
        }

        /// <summary>
        /// Gets the event-flags bitmask for application telemetry.
        /// </summary>
        public string AppTelemetryEventFlags
        {
            get
            {
                var value = AsService().Telemetry.AppTelemetryEventFlags;
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
        }

        // ── loading & per-extension config ────────────────────────────────────────

        /// <summary>
        /// Loads the shared pyRevit configuration, or a one-off configuration from
        /// <paramref name="customPath"/> (used by tests). The default instance is
        /// reused only while the shared store still hands out the same configuration,
        /// so any reload — from here or from another host — is observed.
        /// </summary>
        public static PyRevitConfig Load(string customPath = null)
        {
            // Custom-path calls are never cached and never touch the shared service.
            if (!string.IsNullOrEmpty(customPath))
                return new PyRevitConfig(IniConfiguration.Create(customPath));

            var shared = PyRevitConfigService.GetShared()[ConfigurationService.DefaultConfigurationName];

            var cached = _defaultInstance;
            if (cached != null && ReferenceEquals(cached._config, shared))
                return cached;

            lock (_cacheLock)
            {
                if (_defaultInstance == null || !ReferenceEquals(_defaultInstance._config, shared))
                    _defaultInstance = new PyRevitConfig(shared);

                return _defaultInstance;
            }
        }

        /// <summary>
        /// Drops the cached default instance and the shared service cache so the
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
            var section = AsService().GetExtensionSection(extensionName);
            if (section is null)
                return null;

            return new ExtensionConfig
            {
                Name = extensionName,
                Disabled = section.Disabled ?? false,
                PrivateRepo = section.PrivateRepo ?? false,
                Username = section.Username,
                Password = section.Password
            };
        }

        // Exposes the backing configuration through the service surface so the
        // typed section readers are available. The same IConfiguration underlies
        // both, so a custom-path instance and the shared default read alike.
        private IConfigurationService AsService()
        {
            return _service ?? (_service = new ConfigurationBuilder(false)
                .AddConfigurationSource(ConfigurationService.DefaultConfigurationName, _config)
                .Build());
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
        /// Parses a stored boolean, ignoring surrounding whitespace and the JSON or
        /// Python-literal quotes a value may carry. Accepts the same spellings as the
        /// shared configuration service, so the two agree on every value.
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

            return bool.TryParse(v, out result);
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
