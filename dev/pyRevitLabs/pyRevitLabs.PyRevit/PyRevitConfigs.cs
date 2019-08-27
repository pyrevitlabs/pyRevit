using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Principal;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.PyRevit {
    public class PyRevitConfigValueNotSet : PyRevitException {
        public PyRevitConfigValueNotSet(string sectionName, string keyName) {
            ConfigSection = sectionName;
            ConfigKey = keyName;
        }

        public string ConfigSection { get; set; }
        public string ConfigKey { get; set; }

        public override string Message {
            get {
                return String.Format("Config value not set \"{0}:{1}\"", ConfigSection, ConfigKey);
            }
        }
    }

    public enum PyRevitLogLevels {
        None,
        Verbose,
        Debug
    }

    public static class PyRevitConfigs {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // get config file
        public static PyRevitConfig GetConfigFile() {
            // make sure the file exists and if not create an empty one
            if (!CommonUtils.VerifyFile(PyRevitConsts.ConfigFilePath))
                InitConfigFile();
            return new PyRevitConfig(PyRevitConsts.ConfigFilePath);
        }

        // deletes config file
        public static void DeleteConfig() {
            if (File.Exists(PyRevitConsts.ConfigFilePath))
                try {
                    File.Delete(PyRevitConsts.ConfigFilePath);
                }
                catch (Exception ex) {
                    throw new PyRevitException(string.Format("Failed deleting config file \"{0}\" | {1}", PyRevitConsts.ConfigFilePath, ex.Message));
                }
        }

        // copy config file into all users directory as seed config file
        // create user config file based on a template
        public static void SeedConfig(bool makeCurrentUserAsOwner = false, string setupFromTemplate = null) {
            // if setupFromTemplate is not specified: copy current config into Allusers folder
            // if setupFromTemplate is specified: copy setupFromTemplate as the main config
            string sourceFile = setupFromTemplate != null ? setupFromTemplate : PyRevitConsts.ConfigFilePath;
            string targetFile = setupFromTemplate != null ? PyRevitConsts.ConfigFilePath : PyRevitConsts.SeedConfigFilePath;

            logger.Debug("Seeding config file \"{0}\" to \"{1}\"", sourceFile, targetFile);

            try {
                if (File.Exists(sourceFile)) {
                    CommonUtils.EnsureFile(targetFile);
                    File.Copy(sourceFile, targetFile, true);

                    if (makeCurrentUserAsOwner) {
                        var fs = File.GetAccessControl(targetFile);
                        var currentUser = WindowsIdentity.GetCurrent();
                        try {
                            CommonUtils.SetFileSecurity(targetFile, currentUser.Name);
                        }
                        catch (InvalidOperationException ex) {
                            logger.Error(
                                string.Format(
                                    "You cannot assign ownership to user \"{0}\"." +
                                    "Either you don't have TakeOwnership permissions, " +
                                    "or it is not your user account. | {1}", currentUser.Name, ex.Message
                                    )
                            );
                        }
                    }
                }
            }
            catch (Exception ex) {
                throw new PyRevitException(string.Format("Failed seeding config file. | {0}", ex.Message));
            }
        }

        // specific configuration public access  ======================================================================
        // telemetry
        public static bool GetTelemetryStatus() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryStatusKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsTelemetryStatusDefault;
        }

        public static string GetTelemetryFilePath() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryFilePathKey) ?? string.Empty;
        }

        public static string GetTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryServerUrlKey) ?? string.Empty;
        }

        public static void EnableTelemetry(string telemetryFilePath = null, string telemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling telemetry... path: \"{0}\" server: {1}",
                                       telemetryFilePath, telemetryServerUrl));
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryStatusKey, true);

            if (telemetryFilePath != null) {
                if (telemetryFilePath == string.Empty) {
                    // set empty value
                    cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryFilePathKey, telemetryFilePath);
                }
                else {
                    if (CommonUtils.VerifyPath(telemetryFilePath))
                        cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryFilePathKey, telemetryFilePath);
                    else
                        logger.Debug("Invalid log path \"{0}\"", telemetryFilePath);
                }
            }

            if (telemetryServerUrl != null)
                cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryServerUrlKey, telemetryServerUrl);
        }

        public static void DisableTelemetry() {
            var cfg = GetConfigFile();
            logger.Debug("Disabling telemetry...");
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryStatusKey, false);
        }

        // app telemetry
        public static bool GetAppTelemetryStatus() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryStatusKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsAppTelemetryStatusDefault;
        }

        public static string GetAppTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryServerUrlKey) ?? string.Empty;
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling app telemetry... server: {0}", apptelemetryServerUrl));
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryStatusKey, true);

            if (apptelemetryServerUrl != null)
                cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryServerUrlKey, apptelemetryServerUrl);
        }

        public static void DisableAppTelemetry() {
            var cfg = GetConfigFile();
            logger.Debug("Disabling app telemetry...");
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryStatusKey, false);
        }

        public static string GetAppTelemetryFlags() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryEventFlagsKey) ?? string.Empty;
        }

        public static void SetAppTelemetryFlags(string flags) {
            var cfg = GetConfigFile();
            logger.Debug("Setting app telemetry flags...");
            if (flags != null)
                cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryEventFlagsKey, flags);
        }

        // update checking config
        public static bool GetCheckUpdates() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsCheckUpdatesKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsCheckUpdatesDefault;
        }

        public static void SetCheckUpdates(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsCheckUpdatesKey, state);
        }

        // auto update config
        public static bool GetAutoUpdate() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsAutoUpdateKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsAutoUpdateDefault;
        }

        public static void SetAutoUpdate(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsAutoUpdateKey, state);
        }

        // rocket mode config
        public static bool GetRocketMode() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsRocketModeKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsRocketModeDefault;
        }

        public static void SetRocketMode(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsRocketModeKey, state);
        }

        // logging level config
        public static PyRevitLogLevels GetLoggingLevel() {
            var cfg = GetConfigFile();
            var verboseCfg = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey);
            bool verbose = verboseCfg != null ? bool.Parse(verboseCfg) : PyRevitConsts.ConfigsVerboseDefault;

            var debugCfg = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey);
            bool debug = debugCfg != null ? bool.Parse(debugCfg) : PyRevitConsts.ConfigsDebugDefault;

            if (verbose && !debug)
                return PyRevitLogLevels.Verbose;
            else if (debug)
                return PyRevitLogLevels.Debug;

            return PyRevitLogLevels.None;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level) {
            var cfg = GetConfigFile();
            if (level == PyRevitLogLevels.None) {
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey, false);
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Verbose) {
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey, true);
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Debug) {
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsVerboseKey, true);
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsDebugKey, true);
            }
        }

        // file logging config
        public static bool GetFileLogging() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsFileLoggingKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsFileLoggingDefault;
        }

        public static void SetFileLogging(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsFileLoggingKey, state);
        }

        // load beta config
        public static bool GetLoadBetaTools() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsLoadBetaKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsLoadBetaDefault;
        }

        public static void SetLoadBetaTools(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsLoadBetaKey, state);
        }

        // output style sheet config
        public static string GetOutputStyleSheet() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsOutputStyleSheet) ?? string.Empty;
        }

        public static void SetOutputStyleSheet(string outputCSSFilePath) {
            var cfg = GetConfigFile();
            if (File.Exists(outputCSSFilePath))
                cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsOutputStyleSheet, outputCSSFilePath);
        }

        // user access to tools
        public static bool GetUserCanUpdate() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanUpdateKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsUserCanUpdateDefault;
        }

        public static bool GetUserCanExtend() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanExtendKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsUserCanExtendDefault;
        }

        public static bool GetUserCanConfig() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanConfigKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsUserCanConfigDefault;
        }

        public static void SetUserCanUpdate(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanUpdateKey, state);
        }

        public static void SetUserCanExtend(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanExtendKey, state);
        }

        public static void SetUserCanConfig(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsUserCanConfigKey, state);
        }

        // configurations private access methods  ====================================================================
        private static void InitConfigFile() {
            // get allusers seed config file
            // if admin config file exists, seed initial config states from there.
            var adminFile = PyRevitConsts.FindConfigFileInDirectory(PyRevitLabsConsts.PyRevitProgramDataPath);
            if (adminFile != null)
                SeedConfig(false, setupFromTemplate: adminFile);
            else
                CommonUtils.EnsureFile(PyRevitConsts.ConfigFilePath);
        }
    }
}
