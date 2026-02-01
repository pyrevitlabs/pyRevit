using System;
using System.Collections.Generic;
using System.IO;

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
                return string.IsNullOrEmpty(value) ? null : value.Trim();
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
        /// Gets or sets whether to load beta/experimental commands.
        /// </summary>
        /// <remarks>
        /// When false (default), commands marked as beta (__beta__ = True) will not be loaded.
        /// When true, beta commands will be visible in the UI.
        /// Defaults to false if not configured or if the value cannot be parsed.
        /// </remarks>
        public bool LoadBeta
        {
            get
            {
                var value = _ini.IniReadValue("core", "load_beta");
                return bool.TryParse(value, out var result) ? result : false;
            }
            set
            {
                _ini.IniWriteValue("core", "load_beta", value ? TrueString : FalseString);
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
                var value = _ini.IniReadValue("core", "userextensions");
                return string.IsNullOrEmpty(value) ? new List<string>() : PythonListParser.Parse(value);
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

        /// <summary>
        /// Loads a pyRevit configuration from the default or specified location.
        /// </summary>
        /// <param name="customPath">
        /// Optional custom path to the configuration file. 
        /// If null, uses the default location: %APPDATA%\pyRevit\pyRevit_config.ini
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
            string configName = "pyRevit_config.ini";
            string defaultPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                configName);

            string finalPath = customPath ?? defaultPath;
            return new PyRevitConfig(finalPath);
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
        /// <para>Setting this property to null or empty will reset to the default ("IronPython").</para>
        /// </remarks>
        private string _type;

        public string Type
        {
            get => string.IsNullOrEmpty(_type) ? "IronPython" : _type;
            set => _type = value;
        }

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
