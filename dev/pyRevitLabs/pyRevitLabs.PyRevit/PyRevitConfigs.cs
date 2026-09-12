using System;
using System.IO;
using System.Security.Principal;
using System.Security.AccessControl;
using pyRevitLabs.Common;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.Configurations.Sections;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit
{
    public enum PyRevitLogLevels
    {
        Quiet,
        Verbose,
        Debug
    }

    public enum OutputCloseMode
    {
        CurrentCommand,
        CloseAll
    }

    public static class PyRevitConfigs
    {
        private static readonly Logger _logger = LogManager.GetCurrentClassLogger();

        /// <summary>
        /// Routes the Configurations-layer diagnostics (discovery, migration,
        /// tolerant-read fallbacks) to the pyRevit log.
        /// </summary>
        static PyRevitConfigs()
        {
            ConfigurationDiagnostics.Warn = message => _logger.Warn(message);
            ConfigurationDiagnostics.Info = message => _logger.Info(message);
        }

        /// <summary>
        /// Returns the shared config service, built once and cached for the
        /// process. Call <see cref="ReloadConfig"/> after a settings change to
        /// force the next access to re-read from disk.
        /// </summary>
        public static IConfigurationService GetConfigFile()
            => PyRevitConfigService.GetShared();

        /// <summary>
        /// Drops the cached config service so the next <see cref="GetConfigFile"/>
        /// rebuilds from disk. Used when settings are edited and a reload is required.
        /// </summary>
        public static void ReloadConfig() => PyRevitConfigService.Reload();

        /// <summary>
        /// Writes the disabled flag for shipped extensions whose definition sets
        /// default_enabled=false, so freshly installed clones honor the shipped
        /// default. An existing entry is never overwritten, preserving any explicit
        /// user choice.
        /// </summary>
        public static void SeedShippedExtensionDefaults(string clonePath = null)
        {
            string extensionsRoot = null;
            if (!string.IsNullOrWhiteSpace(clonePath))
            {
                extensionsRoot = Path.Combine(clonePath, PyRevitConsts.ExtensionsDirName);
            }
            else
            {
                foreach (var clone in PyRevitClones.GetRegisteredClones())
                {
                    if (CommonUtils.VerifyPath(clone.ExtensionsPath))
                    {
                        extensionsRoot = clone.ExtensionsPath;
                        break;
                    }
                }
            }

            if (!CommonUtils.VerifyPath(extensionsRoot))
            {
                _logger.Debug("No shipped extensions directory found for seeding defaults.");
                return;
            }

            var cfg = GetConfigFile();
            foreach (var postfix in new[] { PyRevitConsts.ExtensionUIPostfix, PyRevitConsts.ExtensionLibraryPostfix })
            {
                foreach (var extDir in Directory.GetDirectories(extensionsRoot, "*" + postfix))
                {
                    try
                    {
                        var ext = new PyRevitExtension(extDir);
                        if (ext.Definition != null && !ext.Definition.DefaultEnabled)
                        {
                            string existing = cfg.GetSectionKeyValueOrDefault<string>(
                                ext.ConfigName, PyRevitConsts.ExtensionDisabledKey, null);
                            if (existing is null)
                                cfg.SetSectionKeyValue(
                                    ext.ConfigName, PyRevitConsts.ExtensionDisabledKey, true);
                        }
                    }
                    catch (Exception ex)
                    {
                        _logger.Debug("Skipping shipped extension seed for \"{0}\" | {1}", extDir, ex.Message);
                    }
                }
            }
        }

        /// <summary>
        /// Deletes the user config file and drops the cached service, so the
        /// next access rebuilds from a fresh config. Does nothing when no file
        /// is present.
        /// </summary>
        /// <exception cref="PyRevitException">The file exists but could not be deleted.</exception>
        public static void DeleteConfig()
        {
            PyRevitConfigService.Reload();
            if (!File.Exists(PyRevitConsts.ConfigFilePath)) return;

            _logger.Info("Deleting config {@ConfigPath}...", PyRevitConsts.ConfigFilePath);

            try
            {
                File.Delete(PyRevitConsts.ConfigFilePath);
            }
            catch (Exception ex)
            {
                throw new PyRevitException($"Failed deleting config file \"{PyRevitConsts.ConfigFilePath}\"", ex);
            }
        }

        // copy config file into all users directory as seed config file
        public static void SeedConfig(bool lockSeedConfig = false)
        {
            string sourceFile = PyRevitConsts.ConfigFilePath;
            string targetFile = PyRevitConsts.AdminConfigFilePath;

            _logger.Debug("Seeding config file \"{@SourceFile}\" to \"{@TargetFile}\"", sourceFile, targetFile);

            if (!File.Exists(sourceFile)) return;

            try
            {
                File.Copy(sourceFile, targetFile, true);

                if (lockSeedConfig)
                {
                    try
                    {
                        File.SetAttributes(targetFile, FileAttributes.ReadOnly);
                    }
                    catch (InvalidOperationException ex)
                    {
                        var currentUser = WindowsIdentity.GetCurrent();
                        _logger.Error(ex,
                            $"You cannot assign ownership to user \"{currentUser.Name}\"."
                            + "Either you don't have TakeOwnership permissions, "
                            + "or it is not your user account.");
                    }
                }
            }
            catch (Exception ex)
            {
                throw new PyRevitException("Failed seeding config file.", ex);
            }
        }

        // create user config file based on a template
        // if admin config file exists, create initial config file from seed config
        public static void SetupConfig(string templateConfigFilePath = null)
        {
            PyRevitConfigService.Reload();
            string sourceFile = templateConfigFilePath;
            string targetFile = PyRevitConsts.ConfigFilePath;

            if (string.IsNullOrEmpty(sourceFile))
            {
                CommonUtils.EnsureFile(targetFile);
                return;
            }


            _logger.Debug("Seeding config file \"{@SourceFile}\" to \"{@TargetFile}\"", sourceFile, targetFile);

            try
            {
                string targetDir = Path.GetDirectoryName(targetFile);
                if (!string.IsNullOrEmpty(targetDir))
                    CommonUtils.EnsurePath(targetDir);

                File.WriteAllText(targetFile, File.ReadAllText(sourceFile));
            }
            catch (Exception ex)
            {
                throw new PyRevitException($"Failed configuring config file from template at {sourceFile}...", ex);
            }
        }

        // specific configuration public access  ======================================================================
        // general telemetry
        public static bool GetUTCStamps()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry?.TelemetryUseUtcTimeStamps ?? false;
        }

        public static void SetUTCStamps(bool state)
        {
            _logger.Debug("Setting telemetry utc timestamps to {@UseUtc}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new TelemetrySection() { TelemetryUseUtcTimeStamps = state });
        }

        // routes
        public static bool GetRoutesServerStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.Status ?? false;
        }

        public static void SetRoutesServerStatus(bool state)
        {
            _logger.Debug("Setting routes server status to {@Status}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new RoutesSection() { Status = state });
        }

        public static void EnableRoutesServer()
            => SetRoutesServerStatus(true);

        public static void DisableRoutesServer()
            => SetRoutesServerStatus(false);

        public static string GetRoutesServerHost()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.Host;
        }

        public static void SetRoutesServerHost(string host)
        {
            _logger.Debug("Setting routes server host to {@Host}...", host);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new RoutesSection() { Host = host });
        }

        public static int GetRoutesServerPort()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.Port ?? 48884;
        }

        public static void SetRoutesServerPort(int port)
        {
            _logger.Debug("Setting routes server port to {@Port}...", port);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new RoutesSection() { Port = port });
        }

        public static bool GetRoutesLoadCoreAPIStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.LoadCoreApi ?? false;
        }

        public static void SetRoutesLoadCoreAPIStatus(bool state)
        {
            _logger.Debug("Setting routes load core API status to {@LoadCoreApi}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new RoutesSection() { LoadCoreApi = state });
        }

        // telemetry
        public static bool GetTelemetryStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry?.TelemetryStatus ?? false;
        }

        public static void SetTelemetryStatus(bool state)
        {
            _logger.Debug("Setting telemetry status to {@TelemetryStatus}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new TelemetrySection() { TelemetryStatus = state });
        }

        public static string GetTelemetryFilePath()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.TelemetryFileDir ?? string.Empty;
        }

        public static string GetTelemetryServerUrl()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.TelemetryServerUrl ?? string.Empty;
        }

        public static void EnableTelemetry(string telemetryFileDir = null,
            string telemetryServerUrl = null)
        {
            _logger.Debug("Enabling telemetry...");

            if (!string.IsNullOrEmpty(telemetryFileDir) && !Directory.Exists(telemetryFileDir))
            {
                _logger.Warn("Directory \"{@TelemetryFileDir}\" does not exist", telemetryFileDir);
                telemetryFileDir = default;
            }

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(
                new TelemetrySection()
                {
                    TelemetryStatus = true,
                    TelemetryFileDir = telemetryFileDir,
                    TelemetryServerUrl = telemetryServerUrl
                });
        }

        public static bool GetTelemetryIncludeHooks()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.TelemetryIncludeHooks ?? false;
        }

        public static void SetTelemetryIncludeHooks(bool state)
        {
            _logger.Debug("Setting telemetry include hooks to {@TelemetryIncludeHooks}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new TelemetrySection() { TelemetryIncludeHooks = state });
        }

        public static void DisableTelemetry()
        {
            _logger.Debug("Disabling telemetry...");

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new TelemetrySection() { TelemetryStatus = false });
        }

        // app telemetry
        public static bool GetAppTelemetryStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.AppTelemetryStatus ?? false;
        }

        public static void SetAppTelemetryStatus(bool state)
        {
            _logger.Debug("Setting app telemetry status to {@AppTelemetryStatus}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new TelemetrySection() { AppTelemetryStatus = state });
        }

        public static string GetAppTelemetryServerUrl()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.AppTelemetryServerUrl ?? string.Empty;
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null)
        {
            _logger.Debug("Enabling app telemetry...");

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(
                new TelemetrySection()
                {
                    AppTelemetryStatus = true,
                    AppTelemetryServerUrl = apptelemetryServerUrl
                });
        }

        public static void DisableAppTelemetry()
        {
            _logger.Debug("Disabling app telemetry...");

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new TelemetrySection() { AppTelemetryStatus = false });
        }

        public static string GetAppTelemetryFlags()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.AppTelemetryEventFlags ?? string.Empty;
        }

        public static void SetAppTelemetryFlags(string flags)
        {
            _logger.Debug("Setting app telemetry flags to {@AppTelemetryEventFlags}...", flags);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(
                new TelemetrySection()
                { AppTelemetryEventFlags = flags });
        }

        // caching
        public static bool GetBinaryCaches()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.BinCache ?? PyRevitConsts.ConfigsBinaryCacheDefault;
        }

        public static void SetBinaryCaches(bool state)
        {
            _logger.Debug("Setting binary caches {@BinCache}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { BinCache = state });
        }

        // update checking config
        public static bool GetCheckUpdates()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.CheckUpdates ?? false;
        }

        public static void SetCheckUpdates(bool state)
        {
            _logger.Debug("Setting check updates to {@CheckUpdates}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { CheckUpdates = state });
        }

        // auto update config
        public static bool GetAutoUpdate()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.AutoUpdate ?? false;
        }

        public static void SetAutoUpdate(bool state)
        {
            _logger.Debug("Setting auto update to {@AutoUpdate}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { AutoUpdate = state });
        }

        // rocket mode config
        public static bool GetRocketMode()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.RocketMode ?? false;
        }

        public static void SetRocketMode(bool state)
        {
            _logger.Debug("Setting rocket mode to {@RocketMode}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { RocketMode = state });
        }

        // logging level config

        /// <summary>
        /// Maps the stored debug/verbose flags to a log level. Shared by this facade
        /// and the Python config facade so both agree on the representation without
        /// either re-deriving it.
        /// </summary>
        public static PyRevitLogLevels ToLoggingLevel(bool? debug, bool? verbose)
        {
            if (verbose == true && debug != true)
                return PyRevitLogLevels.Verbose;
            if (debug == true)
                return PyRevitLogLevels.Debug;
            return PyRevitLogLevels.Quiet;
        }

        /// <summary>Debug implies verbose, so the two flags are always written together.</summary>
        public static bool LoggingLevelDebugFlag(PyRevitLogLevels level)
            => level == PyRevitLogLevels.Debug;

        public static bool LoggingLevelVerboseFlag(PyRevitLogLevels level)
            => level == PyRevitLogLevels.Debug || level == PyRevitLogLevels.Verbose;

        public static PyRevitLogLevels GetLoggingLevel()
        {
            IConfigurationService cfg = GetConfigFile();
            return ToLoggingLevel(cfg.Core.Debug, cfg.Core.Verbose);
        }

        public static void SetLoggingLevel(PyRevitLogLevels level)
        {
            _logger.Debug("Setting logging level to {@LogLevel}...", level);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection()
            {
                Debug = LoggingLevelDebugFlag(level),
                Verbose = LoggingLevelVerboseFlag(level),
            });
        }

        // file logging config
        public static bool GetFileLogging()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.FileLogging ?? false;
        }

        public static void SetFileLogging(bool state)
        {
            _logger.Debug("Setting file logging to {@FileLogging}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { FileLogging = state });
        }

        // misc startup
        public static int GetStartupLogTimeout()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.StartupLogTimeout ?? 0;
        }

        public static void SetStartupLogTimeout(int timeout)
        {
            _logger.Debug("Setting startup log timeout to {@StartupLogTimeout}...", timeout);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { StartupLogTimeout = timeout });
        }

        public static string GetRequiredHostBuild()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.RequiredHostBuild ?? string.Empty;
        }

        public static void SetRequiredHostBuild(string buildnumber)
        {
            _logger.Debug("Setting required host build to {@RequiredHostBuild}...", buildnumber);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { RequiredHostBuild = buildnumber });
        }

        public static long GetMinHostDriveFreeSpace()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.MinHostDriveFreeSpace ?? 0;
        }

        public static void SetMinHostDriveFreeSpace(long freespace)
        {
            _logger.Debug("Setting min host drive free space to {@MinHostDriveFreeSpace}...", freespace);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { MinHostDriveFreeSpace = freespace });
        }

        // load beta config
        public static bool GetLoadBetaTools()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.LoadBeta ?? false;
        }

        public static void SetLoadBetaTools(bool state)
        {
            _logger.Debug("Setting load beta tools to {@LoadBeta}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { LoadBeta = state });
        }

        // close other outputs config
        public static bool GetCloseOtherOutputs()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.CloseOtherOutputs ?? false;
        }

        public static void SetCloseOtherOutputs(bool state)
        {
            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { CloseOtherOutputs = state });
        }

        /// <summary>
        /// Maps the stored close-output-mode value to the enum, tolerating
        /// quoting/casing and falling back to the default. Shared by this facade
        /// and the Python config facade.
        /// </summary>
        public static OutputCloseMode ToCloseOutputMode(string rawValue)
        {
            var s = (rawValue ?? PyRevitConsts.ConfigsCloseOutputModeDefault).Trim().Trim('"', '\'');
            if (s.Equals(PyRevitConsts.ConfigsCloseOutputModeCloseAll, StringComparison.InvariantCultureIgnoreCase))
                return OutputCloseMode.CloseAll;
            return OutputCloseMode.CurrentCommand;
        }

        public static string CloseOutputModeConfigValue(OutputCloseMode mode)
            => (mode == OutputCloseMode.CloseAll)
                ? PyRevitConsts.ConfigsCloseOutputModeCloseAll
                : PyRevitConsts.ConfigsCloseOutputModeCurrentCommand;

        public static OutputCloseMode GetCloseOutputMode()
        {
            IConfigurationService cfg = GetConfigFile();
            return ToCloseOutputMode(cfg.Core.CloseOutputMode);
        }

        public static void SetCloseOutputMode(OutputCloseMode mode)
        {
            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(
                new CoreSection() { CloseOutputMode = CloseOutputModeConfigValue(mode) });
        }

        // cpythonengine
        public static int GetCpythonEngineVersion()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.CpythonEngineVersion ?? 0;
        }

        public static void SetCpythonEngineVersion(int version)
        {
            _logger.Debug("Setting cpyhon engine version to {@CpythonEngineVersion}...", version);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { CpythonEngineVersion = version });
        }

        // ux ui
        public static string GetUserLocale()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.UserLocale ?? "";
        }

        public static void SetUserLocale(string localCode)
        {
            _logger.Debug("Setting user locale to {@LocalCode}...", localCode);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { UserLocale = localCode });
        }

        public static string GetOutputStyleSheet()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.OutputStyleSheet ?? string.Empty;
        }

        /// <summary>
        /// Sets the output stylesheet path, or clears the key when
        /// <paramref name="outputCssFilePath"/> is empty so consumers revert to
        /// their built-in default stylesheet.
        /// </summary>
        public static void SetOutputStyleSheet(string outputCssFilePath)
        {
            _logger.Debug("Setting output style sheet to {@OutputCssFilePath}...", outputCssFilePath);

            IConfigurationService cfg = GetConfigFile();
            if (string.IsNullOrEmpty(outputCssFilePath))
            {
                cfg.Configuration.RemoveOption("core", "outputstylesheet");
                cfg.Configuration.SaveConfiguration();
            }
            else if (File.Exists(outputCssFilePath))
                cfg.SaveSection(new CoreSection() { OutputStyleSheet = outputCssFilePath });
        }

        // user access to tools
        public static bool GetUserCanUpdate()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.UserCanUpdate ?? false;
        }

        public static bool GetUserCanExtend()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.UserCanExtend ?? false;
        }

        public static bool GetUserCanConfig()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.UserCanConfig ?? false;
        }

        public static void SetUserCanUpdate(bool state)
        {
            _logger.Debug("Setting user can install to {@UserCanUpdate}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { UserCanUpdate = state });
        }

        public static void SetUserCanExtend(bool state)
        {
            _logger.Debug("Setting user can install to {@UserCanExtend}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { UserCanExtend = state });
        }

        public static void SetUserCanConfig(bool state)
        {
            _logger.Debug("Setting user can install to {@UserCanConfig}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { UserCanConfig = state });
        }

        public static bool GetColorizeDocs()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.ColorizeDocs ?? false;
        }

        public static void SetColorizeDocs(bool state)
        {
            _logger.Debug("Setting colorize docs to {@ColorizeDocs}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { ColorizeDocs = state });
        }

        public static bool GetAppendTooltipEx()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.TooltipDebugInfo ?? false;
        }

        public static void SetAppendTooltipEx(bool state)
        {
            _logger.Debug("Setting tooltip debug info to {@TooltipDebugInfo}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(new CoreSection() { TooltipDebugInfo = state });
        }
    }
}