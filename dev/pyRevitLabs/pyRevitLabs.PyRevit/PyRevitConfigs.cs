using System;
using System.IO;
using System.Security.Principal;
using System.Security.AccessControl;

using pyRevitLabs.Common;
using pyRevitLabs.Configurations;
using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.Configurations.Ini;
using pyRevitLabs.Configurations.Ini.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit
{
    public enum PyRevitLogLevels
    {
        Quiet,
        Verbose,
        Debug
    }

    public static class PyRevitConfigs
    {
        private static readonly Logger _logger = LogManager.GetCurrentClassLogger();

        /// <summary>
        /// Returns config file.
        /// </summary>
        /// <returns>Returns admin config if admin config exists and user config not found.</returns>
        public static IConfigurationService GetConfigFile(
            string overrideName = ConfigurationService.DefaultConfigurationName)
        {
            // make sure the file exists and if not create an empty one
            string userConfig = PyRevitConsts.ConfigFilePath;
            string adminConfig = PyRevitConsts.AdminConfigFilePath;

            if (!File.Exists(userConfig)
                && File.Exists(adminConfig))
            {
                _logger.Info("Creating admin config {@ConfigPath}...", adminConfig);
                return CreateConfiguration(adminConfig, true, overrideName);
            }

            _logger.Info("Creating user config {@ConfigPath}...", userConfig);
            return CreateConfiguration(userConfig, false, overrideName);
        }

        /// <summary>
        /// Removes user config file.
        /// </summary>
        /// <exception cref="PyRevitException"></exception>
        public static void DeleteConfig()
        {
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
                File.WriteAllText(targetFile, File.ReadAllText(sourceFile));
            }
            catch (Exception ex)
            {
                throw new PyRevitException($"Failed configuring config file from template at {sourceFile}...", ex);
            }
        }

        private static IConfigurationService CreateConfiguration(
            string configPath,
            bool readOnly = false,
            string overrideName = ConfigurationService.DefaultConfigurationName)
        {
            var builder = new ConfigurationBuilder()
                .AddIniConfiguration(configPath, "default", readOnly);

            if (string.IsNullOrEmpty(overrideName))
            {
                builder.AddIniConfiguration(
                    Path.ChangeExtension(configPath,
                        $"{overrideName}.{IniConfiguration.DefaultFileExtension}"), overrideName);
            }

            return builder.Build();
        }

        // specific configuration public access  ======================================================================
        // general telemetry
        public static bool GetUTCStamps()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry?.TelemetryUseUtcTimeStamps ?? false;
        }

        public static void SetUTCStamps(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting telemetry utc timestamps to {@TelemetryStatus}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {TelemetryStatus = state});
        }

        // routes
        public static bool GetRoutesServerStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.Status ?? false;
        }

        public static void SetRoutesServerStatus(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting routes server status to {@Status}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new RoutesSection() {Status = state});
        }

        public static void EnableRoutesServer(string revitVersion = ConfigurationService.DefaultConfigurationName)
            => SetRoutesServerStatus(true, revitVersion);

        public static void DisableRoutesServer(string revitVersion = ConfigurationService.DefaultConfigurationName)
            => SetRoutesServerStatus(false, revitVersion);

        public static string GetRoutesServerHost()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.Host;
        }

        public static void SetRoutesServerHost(string host,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting routes server host to {@Host}...", host);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new RoutesSection() {Host = host});
        }

        public static int GetRoutesServerPort()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.Port ?? 48884;
        }

        public static void SetRoutesServerPort(int port,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting routes server port to {@Port}...", port);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new RoutesSection() {Port = port});
        }

        public static bool GetRoutesLoadCoreAPIStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Routes.LoadCoreApi ?? false;
        }

        public static void SetRoutesLoadCoreAPIStatus(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting routes load core API status to {@LoadCoreApi}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new RoutesSection() {LoadCoreApi = state});
        }

        // telemetry
        public static bool GetTelemetryStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry?.TelemetryStatus ?? false;
        }

        public static void SetTelemetryStatus(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting telemetry status to {@TelemetryStatus}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {TelemetryStatus = state});
        }

        public static string GetTelemetryFilePath()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.TelemetryFileDir;
        }

        public static string GetTelemetryServerUrl()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.TelemetryServerUrl;
        }

        public static void EnableTelemetry(string telemetryFileDir = null,
            string telemetryServerUrl = null,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Enabling telemetry...");

            if (!Directory.Exists(telemetryFileDir))
            {
                _logger.Warn("Directory \"{@TelemetryFileDir}\" does not exist", telemetryFileDir);
                telemetryFileDir = default;
            }

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion,
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

        public static void SetTelemetryIncludeHooks(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting telemetry include hooks to {@TelemetryIncludeHooks}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {TelemetryIncludeHooks = state});
        }

        public static void DisableTelemetry(string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Disabling telemetry...");

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {TelemetryStatus = false});
        }

        // app telemetry
        public static bool GetAppTelemetryStatus()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.AppTelemetryStatus ?? false;
        }

        public static void SetAppTelemetryStatus(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting app telemetry status to {@AppTelemetryStatus}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {AppTelemetryStatus = state});
        }

        public static string GetAppTelemetryServerUrl()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.AppTelemetryServerUrl;
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Enabling app telemetry...");

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {AppTelemetryServerUrl = apptelemetryServerUrl});
        }

        public static void DisableAppTelemetry(string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Disabling app telemetry...");

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new TelemetrySection() {AppTelemetryStatus = false});
        }

        public static string GetAppTelemetryFlags()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Telemetry.AppTelemetryEventFlags?.ToString("X") ?? string.Empty;
        }

        public static void SetAppTelemetryFlags(string flags,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting app telemetry flags to {@AppTelemetryEventFlags}...", flags);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion,
                new TelemetrySection()
                    {AppTelemetryEventFlags = int.Parse(flags, System.Globalization.NumberStyles.HexNumber)});
        }

        // caching
        public static bool GetBinaryCaches()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.BinCache ?? false;
        }

        public static void SetBinaryCaches(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting binary caches {@BinCache}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {BinCache = state});
        }

        // update checking config
        public static bool GetCheckUpdates()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.CheckUpdates ?? false;
        }

        public static void SetCheckUpdates(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting check updates to {@CheckUpdates}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {CheckUpdates = state});
        }

        // auto update config
        public static bool GetAutoUpdate()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.AutoUpdate ?? false;
        }

        public static void SetAutoUpdate(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting auto update to {@AutoUpdate}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {AutoUpdate = state});
        }

        // rocket mode config
        public static bool GetRocketMode()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.RocketMode ?? false;
        }

        public static void SetRocketMode(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting rocket mode to {@RocketMode}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {RocketMode = state});
        }

        // logging level config
        public static PyRevitLogLevels GetLoggingLevel()
        {
            IConfigurationService cfg = GetConfigFile();

            if (cfg.Core.Verbose == true
                && cfg.Core.Debug != true)
                return PyRevitLogLevels.Verbose;
            else if (cfg.Core.Debug == true)
                return PyRevitLogLevels.Debug;

            return PyRevitLogLevels.Quiet;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting logging level to {@LogLevel}...", level);

            IConfigurationService cfg = GetConfigFile();
            if (level == PyRevitLogLevels.Quiet)
            {
                cfg.SaveSection(revitVersion, new CoreSection() {Debug = false, Verbose = false});
            }
            else if (level == PyRevitLogLevels.Verbose)
            {
                cfg.SaveSection(revitVersion, new CoreSection() {Debug = false, Verbose = true});
            }
            else if (level == PyRevitLogLevels.Debug)
            {
                cfg.SaveSection(revitVersion, new CoreSection() {Debug = true, Verbose = false});
            }
        }

        // file logging config
        public static bool GetFileLogging()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.FileLogging ?? false;
        }

        public static void SetFileLogging(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting file logging to {@FileLogging}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {FileLogging = state});
        }

        // misc startup
        public static int GetStartupLogTimeout()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.StartupLogTimeout ?? 0;
        }

        public static void SetStartupLogTimeout(int timeout,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting startup log timeout to {@StartupLogTimeout}...", timeout);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {StartupLogTimeout = timeout});
        }

        public static string GetRequiredHostBuild()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.RequiredHostBuild ?? string.Empty;
        }

        public static void SetRequiredHostBuild(string buildnumber,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting required host build to {@RequiredHostBuild}...", buildnumber);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {RequiredHostBuild = buildnumber});
        }

        public static long GetMinHostDriveFreeSpace()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.MinHostDriveFreeSpace ?? 0;
        }

        public static void SetMinHostDriveFreeSpace(long freespace,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting min host drive free space to {@MinHostDriveFreeSpace}...", freespace);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {MinHostDriveFreeSpace = freespace});
        }

        // load beta config
        public static bool GetLoadBetaTools()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.LoadBeta ?? false;
        }

        public static void SetLoadBetaTools(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting load beta tools to {@LoadBeta}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {LoadBeta = state});
        }

        // cpythonengine
        public static int GetCpythonEngineVersion()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.CpythonEngineVersion ?? 0;
        }

        public static void SetCpythonEngineVersion(int version,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting cpyhon engine version to {@CpythonEngineVersion}...", version);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {CpythonEngineVersion = version});
        }

        // ux ui
        public static string GetUserLocale()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.UserLocale ?? "en_us";
        }

        public static void SetUserLocale(string localCode,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting user locale to {@LocalCode}...", localCode);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {UserLocale = localCode});
        }

        public static string GetOutputStyleSheet()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.OutputStyleSheet ?? string.Empty;
        }

        public static void SetOutputStyleSheet(string outputCssFilePath,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting output style sheet to {@OutputCssFilePath}...", outputCssFilePath);

            IConfigurationService cfg = GetConfigFile();
            if (File.Exists(outputCssFilePath))
                cfg.SaveSection(revitVersion, new CoreSection() {OutputStyleSheet = outputCssFilePath});
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

        public static void SetUserCanUpdate(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting user can install to {@UserCanUpdate}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {UserCanUpdate = state});
        }

        public static void SetUserCanExtend(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting user can install to {@UserCanExtend}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {UserCanExtend = state});
        }

        public static void SetUserCanConfig(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting user can install to {@UserCanConfig}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {UserCanConfig = state});
        }

        public static bool GetColorizeDocs()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.ColorizeDocs ?? false;
        }

        public static void SetColorizeDocs(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting colorize docs to {@ColorizeDocs}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {ColorizeDocs = state});
        }

        public static bool GetAppendTooltipEx()
        {
            IConfigurationService cfg = GetConfigFile();
            return cfg.Core.TooltipDebugInfo ?? false;
        }

        public static void SetAppendTooltipEx(bool state,
            string revitVersion = ConfigurationService.DefaultConfigurationName)
        {
            _logger.Debug("Setting tooltip debug info to {@TooltipDebugInfo}...", state);

            IConfigurationService cfg = GetConfigFile();
            cfg.SaveSection(revitVersion, new CoreSection() {TooltipDebugInfo = state});
        }
    }
}
