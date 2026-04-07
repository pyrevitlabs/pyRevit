using System;
using System.Collections.Generic;
using System.IO;
using System.Text.RegularExpressions;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Provides access to pyRevit configuration settings stored in an INI file.
    /// Handles core settings like user extensions, locale, loader options, and extension-specific configurations.
    /// </summary>
    public class PyRevitConfig
    {
        /// <summary>
        /// The underlying INI file handler for reading and writing configuration values.
        /// </summary>
        private readonly IniFile _ini;

        /// <summary>
        /// Cached default-path instance. Cleared via <see cref="ClearCache"/> at the
        /// start of each session load so that config changes made between reloads are
        /// picked up.  Custom-path calls bypass this cache.
        /// </summary>
        private static PyRevitConfig _defaultInstance;
        private static readonly object _cacheLock = new object();

        /// <summary>
        /// Cached values for boolean conversion to avoid repeated string allocations.
        /// </summary>
        private const string TrueString = "true";
        private const string FalseString = "false";
        
        /// <summary>
        /// Gets the full path to the configuration file.
        /// </summary>
        public string ConfigPath { get; }

        /// <summary>
        /// Gets or sets the user extensions configuration as a raw string.
        /// This can be a single path or a Python-style list of paths.
        /// Use <see cref="UserExtensionsList"/> for parsed list access.
        /// </summary>
        /// <remarks>
        /// Returns null if the value is not set or empty.
        /// Trailing/leading whitespace is automatically trimmed on read.
        /// </remarks>
        public string UserExtensions 
        {
            get
            {
                var value = _ini.IniReadValue("core", "userextensions");
                return string.IsNullOrEmpty(value) ? null : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("core", "userextensions", value);
            }
        }

        /// <summary>
        /// Gets or sets the user's locale preference for pyRevit interface.
        /// </summary>
        /// <remarks>
        /// Expected format: language code (e.g., "en-US", "de-DE", "fr-FR").
        /// Returns null if not configured.
        /// </remarks>
        /// <example>
        /// config.UserLocale = "en-US";
        /// </example>
        public string UserLocale
        {
            get
            {
                var value = _ini.IniReadValue("core", "user_locale");
                if (string.IsNullOrEmpty(value))
                    return null;

                var normalized = NormalizeLocaleValue(value);
                return string.IsNullOrEmpty(normalized) ? null : normalized;
            }
            set
            {
                _ini.IniWriteValue("core", "user_locale", value);
            }
        }

        /// <summary>
        /// Gets or sets whether the new loader architecture is enabled.
        /// </summary>
        /// <remarks>
        /// Defaults to false if not configured or if the value cannot be parsed.
        /// </remarks>
        public bool NewLoader
        {
            get
            {
                var value = _ini.IniReadValue("core", "new_loader");
                return bool.TryParse(value, out var result) ? result : true;
            }
            set
            {
                _ini.IniWriteValue("core", "new_loader", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets whether Rocket Mode is enabled.
        /// </summary>
        /// <remarks>
        /// When true, pyRevit skips non-critical startup work (e.g. icon pre-loading)
        /// to reduce session load time. Defaults to false.
        /// </remarks>
        public bool RocketMode
        {
            get
            {
                var value = _ini.IniReadValue("core", "rocketmode");
                return bool.TryParse(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("core", "rocketmode", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets whether to load beta/experimental commands.
        /// </summary>
        /// <remarks>
        /// When false (default), commands marked as beta (bundle <c>is_beta</c> or script <c>__beta__</c>) will not be loaded.
        /// When true, beta commands will be visible in the UI.
        /// Defaults to false if not configured or if the value cannot be parsed.
        /// Reads <c>loadbeta</c> first (same INI key as pyRevitLabs and Python <c>user_config.load_beta</c>);
        /// falls back to <c>load_beta</c> for older INI files written by earlier C# builds.
        /// </remarks>
        public bool LoadBeta
        {
            get
            {
                var value = _ini.IniReadValue("core", "loadbeta");
                if (string.IsNullOrWhiteSpace(value))
                    value = _ini.IniReadValue("core", "load_beta");
                return TryParseConfigBool(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("core", "loadbeta", value ? TrueString : FalseString);
                // Drop legacy key so the file does not show two competing entries.
                _ini.IniRemoveKey("core", "load_beta");
            }
        }

        /// <summary>
        /// Gets or sets the logging verbosity level.
        /// </summary>
        /// <remarks>
        /// 0 = Quiet (default), 1 = Verbose, 2 = Debug.
        /// Derived from the [core] verbose and debug keys, matching PyRevitLogLevels in the CLI library.
        /// Read-only; change level by setting the [core] verbose or debug INI keys.
        /// </remarks>
        public int LoggingLevel
        {
            get
            {
                var verbose = _ini.IniReadValue("core", "verbose");
                var debug = _ini.IniReadValue("core", "debug");
                bool isDebug = bool.TryParse(debug, out var d) && d;
                bool isVerbose = bool.TryParse(verbose, out var v) && v;
                if (isDebug) return 2;
                if (isVerbose) return 1;
                return 0;
            }
        }

        /// <summary>
        /// Gets or sets whether to write log output to a file.
        /// </summary>
        public bool FileLogging
        {
            get
            {
                var value = _ini.IniReadValue("core", "filelogging");
                return bool.TryParse(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("core", "filelogging", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets whether pyRevit should auto-update on startup.
        /// </summary>
        public bool AutoUpdate
        {
            get
            {
                var value = _ini.IniReadValue("core", "autoupdate");
                return bool.TryParse(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("core", "autoupdate", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets the path to a custom CSS stylesheet for pyRevit output windows.
        /// </summary>
        public string OutputStyleSheet
        {
            get
            {
                var value = _ini.IniReadValue("core", "outputstylesheet");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("core", "outputstylesheet", value ?? string.Empty);
            }
        }

        // ── Telemetry ────────────────────────────────────────────────────────────

        /// <summary>
        /// Gets or sets whether script-execution telemetry is enabled.
        /// </summary>
        public bool TelemetryState
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "active");
                return bool.TryParse(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("telemetry", "active", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets whether telemetry timestamps are recorded in UTC.
        /// </summary>
        public bool TelemetryUTCTimeStamps
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "utc_timestamps");
                if (bool.TryParse(value, out var result))
                    return result;

                // Default to true when the value is missing or unparseable so that
                // loader behavior matches CLI/user_config defaults.
                return true;
            }
            set
            {
                _ini.IniWriteValue("telemetry", "utc_timestamps", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets the directory path for telemetry log files.
        /// </summary>
        public string TelemetryFilePath
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "telemetry_file_dir");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("telemetry", "telemetry_file_dir", value ?? string.Empty);
            }
        }

        /// <summary>
        /// Gets or sets the URL of the telemetry server.
        /// </summary>
        public string TelemetryServerUrl
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "telemetry_server_url");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("telemetry", "telemetry_server_url", value ?? string.Empty);
            }
        }

        /// <summary>
        /// Gets or sets whether hook script executions are included in telemetry.
        /// </summary>
        public bool TelemetryIncludeHooks
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "include_hooks");
                return bool.TryParse(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("telemetry", "include_hooks", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets whether application-event telemetry is enabled.
        /// </summary>
        public bool AppTelemetryState
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "active_app");
                return bool.TryParse(value, out var result) && result;
            }
            set
            {
                _ini.IniWriteValue("telemetry", "active_app", value ? TrueString : FalseString);
            }
        }

        /// <summary>
        /// Gets or sets the URL of the application-event telemetry server.
        /// </summary>
        public string AppTelemetryServerUrl
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "apptelemetry_server_url");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("telemetry", "apptelemetry_server_url", value ?? string.Empty);
            }
        }

        /// <summary>
        /// Gets or sets the event-flags bitmask for application telemetry.
        /// </summary>
        public string AppTelemetryEventFlags
        {
            get
            {
                var value = _ini.IniReadValue("telemetry", "apptelemetry_event_flags");
                return string.IsNullOrEmpty(value) ? string.Empty : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("telemetry", "apptelemetry_event_flags", value ?? string.Empty);
            }
        }

        /// <summary>
        /// Gets or sets the timeout (in seconds) for displaying startup log messages.
        /// </summary>
        /// <remarks>
        /// Default value is 10 seconds if not configured or if the value cannot be parsed.
        /// This controls how long startup diagnostic messages remain visible.
        /// </remarks>
        /// <value>Timeout in seconds. Must be a positive integer.</value>
        public int StartupLogTimeout
        {
            get
            {
                var value = _ini.IniReadValue("core", "startuplogtimeout");
                return int.TryParse(value, out var result) ? result : 10;
            }
            set
            {
                _ini.IniWriteValue("core", "startuplogtimeout", value.ToString());
            }
        }
        /// <summary>
        /// Gets or sets the user extensions as a parsed list of paths.
        /// This property automatically converts between Python list format and C# List.
        /// </summary>
        /// <remarks>
        /// <para>Returns an empty list if no extensions are configured.</para>
        /// <para>Each path typically points to a pyRevit extension directory.</para>
        /// <para>The underlying storage format is Python-style: ["path1", "path2"]</para>
        /// </remarks>
        /// <example>
        /// <code>
        /// config.UserExtensionsList = new List&lt;string&gt; 
        /// { 
        ///     @"C:\pyRevit\Extensions\MyExtension",
        ///     @"D:\CustomExtensions\AnotherExtension"
        /// };
        /// </code>
        /// </example>
        public List<string> UserExtensionsList
        {
            get
            {
                return _ini.GetPythonList("core", "userextensions");
            }
            set
            {
                _ini.IniWriteValue("core", "userextensions", PythonListParser.ToPythonListString(value));
            }
        }
        /// <summary>
        /// Initializes a new instance of the <see cref="PyRevitConfig"/> class with the specified configuration file path.
        /// </summary>
        /// <param name="configPath">The full path to the pyRevit configuration INI file.</param>
        public PyRevitConfig(string configPath)
        {
            ConfigPath = configPath;
            _ini = new IniFile(configPath);
        }

        private static string NormalizeLocaleValue(string rawValue)
        {
            if (string.IsNullOrEmpty(rawValue))
                return null;

            var value = rawValue.Trim();
            if (value.Length >= 2)
            {
                var first = value[0];
                var last = value[value.Length - 1];
                if ((first == '"' && last == '"') || (first == '\'' && last == '\''))
                {
                    value = value.Substring(1, value.Length - 2).Trim();
                }
            }

            if (string.IsNullOrEmpty(value))
                return null;

            value = value.Replace('-', '_').ToLowerInvariant();
            return LocaleSupport.NormalizeLocaleKey(value);
        }

        /// <summary>
        /// Loads a pyRevit configuration from the default or specified location.
        /// </summary>
        /// <param name="customPath">
        /// Optional custom path to the configuration file. 
        /// If null, uses the same discovery as pyRevitLabs/Python: first <c>*.ini</c> under
        /// <c>%APPDATA%\pyRevit\</c> matching the labs config filename pattern, else
        /// <c>%APPDATA%\pyRevit\pyRevit_config.ini</c>.
        /// </param>
        /// <returns>A new <see cref="PyRevitConfig"/> instance for the specified configuration file.</returns>
        /// <remarks>
        /// This method does not verify that the configuration file exists.
        /// The file will be created automatically when values are written.
        /// </remarks>
        /// <example>
        /// <code>
        /// // Load from default location
        /// var config = PyRevitConfig.Load();
        /// 
        /// // Load from custom location
        /// var customConfig = PyRevitConfig.Load(@"C:\MyApp\custom_config.ini");
        /// </code>
        /// </example>
        public static PyRevitConfig Load(string customPath = null)
        {
            // Custom-path calls (used by tests) always create a fresh instance — no caching.
            if (!string.IsNullOrEmpty(customPath))
                return new PyRevitConfig(customPath);

            // Return cached default-path instance.
            if (_defaultInstance != null)
                return _defaultInstance;

            lock (_cacheLock)
            {
                if (_defaultInstance != null)
                    return _defaultInstance;

                var appDataPyRevit = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                    "pyRevit");
                var discovered = TryFindConfigIniInDirectory(appDataPyRevit);
                var fallback = Path.Combine(appDataPyRevit, "pyRevit_config.ini");
                var finalPath = discovered ?? fallback;

                // Ensure the file exists so Python's configparser can write to it
                if (!File.Exists(finalPath))
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(finalPath));
                    File.Create(finalPath).Dispose();
                }

                _defaultInstance = new PyRevitConfig(finalPath);
                return _defaultInstance;
            }
        }

        /// <summary>
        /// Clears the cached default-path config instance so that the next
        /// <see cref="Load()"/> call re-reads from disk.  Called at session reload
        /// via <see cref="ExtensionParser.ClearAllCaches"/>.
        /// </summary>
        public static void ClearCache()
        {
            _defaultInstance = null;
        }

        /// <summary>
        /// Matches pyRevitLabs <c>ConfigsFileRegexPattern</c> (first match wins).
        /// </summary>
        private static string TryFindConfigIniInDirectory(string directory)
        {
            if (string.IsNullOrEmpty(directory) || !Directory.Exists(directory))
                return null;

            try
            {
                var configMatcher = new Regex(@".*[pyrevit|config].*\.ini", RegexOptions.IgnoreCase);
                foreach (var fullPath in Directory.GetFiles(directory, "*.ini", SearchOption.TopDirectoryOnly))
                {
                    if (configMatcher.IsMatch(Path.GetFileName(fullPath)))
                        return fullPath;
                }
            }
            catch
            {
                // ignore
            }

            return null;
        }

        /// <summary>
        /// Retrieves the configuration for a specific extension by its name.
        /// </summary>
        /// <param name="extensionName">
        /// The name of the extension (without the .extension or .lib suffix).
        /// For example, use "pyRevitCore" not "pyRevitCore.extension".
        /// </param>
        /// <returns>
        /// An <see cref="ExtensionConfig"/> object containing the extension's configuration,
        /// or null if the extension is not found in the configuration.
        /// </returns>
        /// <remarks>
        /// <para>This method searches for extensions in the following section name formats:</para>
        /// <list type="bullet">
        /// <item><description>{extensionName}.extension</description></item>
        /// <item><description>{extensionName}.lib</description></item>
        /// </list>
        /// <para>The method is optimized to minimize INI file reads by checking for section existence first.</para>
        /// </remarks>
        /// <example>
        /// <code>
        /// var config = PyRevitConfig.Load();
        /// var extConfig = config.ParseExtensionByName("pyRevitCore");
        /// if (extConfig != null &amp;&amp; !extConfig.Disabled)
        /// {
        ///     // Extension is enabled
        /// }
        /// </code>
        /// </example>
        public ExtensionConfig ParseExtensionByName(string extensionName)
        {
            // Try both possible section names directly
            var possibleSections = new[]
            {
                $"{extensionName}.extension",
                $"{extensionName}.lib"
            };

            foreach (var section in possibleSections)
            {
                // Optimization: Read all values once and cache them to minimize P/Invoke calls
                var disabledValue = _ini.IniReadValue(section, "disabled");
                var privateRepoValue = _ini.IniReadValue(section, "private_repo");
                var usernameValue = _ini.IniReadValue(section, "username");
                
                // Check if section exists by verifying any key has a value
                if (!string.IsNullOrEmpty(disabledValue) || 
                    !string.IsNullOrEmpty(privateRepoValue) ||
                    !string.IsNullOrEmpty(usernameValue))
                {
                    // Section exists, parse all values
                    // Read password only if section exists (one less P/Invoke call for non-existent sections)
                    var passwordValue = _ini.IniReadValue(section, "password");
                    
                    return new ExtensionConfig
                    {
                        Name = extensionName,
                        Disabled = bool.TryParse(disabledValue, out var disabled) && disabled,
                        PrivateRepo = bool.TryParse(privateRepoValue, out var privateRepo) && privateRepo,
                        Username = usernameValue,
                        Password = passwordValue
                    };
                }
            }

            return null; // Return null if the extension is not found
        }

        /// <summary>
        /// Parses booleans from INI values (matches Python/json-style and common variants).
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
