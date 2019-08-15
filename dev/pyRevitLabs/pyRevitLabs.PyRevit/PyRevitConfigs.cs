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
            if (!CommonUtils.VerifyFile(PyRevit.ConfigFilePath))
                InitConfigFile();
            return new PyRevitConfig(PyRevit.ConfigFilePath);
        }

        // deletes config file
        public static void DeleteConfig() {
            if (File.Exists(PyRevit.ConfigFilePath))
                try {
                    File.Delete(PyRevit.ConfigFilePath);
                }
                catch (Exception ex) {
                    throw new PyRevitException(string.Format("Failed deleting config file \"{0}\" | {1}", PyRevit.ConfigFilePath, ex.Message));
                }
        }

        // copy config file into all users directory as seed config file
        // create user config file based on a template
        public static void SeedConfig(bool makeCurrentUserAsOwner = false, string setupFromTemplate = null) {
            // if setupFromTemplate is not specified: copy current config into Allusers folder
            // if setupFromTemplate is specified: copy setupFromTemplate as the main config
            string sourceFile = setupFromTemplate != null ? setupFromTemplate : PyRevit.ConfigFilePath;
            string targetFile = setupFromTemplate != null ? PyRevit.ConfigFilePath : PyRevit.SeedConfigFilePath;

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
            var status = cfg.GetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryStatusKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsTelemetryStatusDefault;
        }

        public static string GetTelemetryFilePath() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryFilePathKey) ?? string.Empty;
        }

        public static string GetTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryServerUrlKey) ?? string.Empty;
        }

        public static void EnableTelemetry(string telemetryFilePath = null, string telemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling telemetry... path: \"{0}\" server: {1}",
                                       telemetryFilePath, telemetryServerUrl));
            cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryStatusKey, true);

            if (telemetryFilePath != null) {
                if (telemetryFilePath == string.Empty) {
                    // set empty value
                    cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryFilePathKey, telemetryFilePath);
                }
                else {
                    if (CommonUtils.VerifyPath(telemetryFilePath))
                        cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryFilePathKey, telemetryFilePath);
                    else
                        logger.Debug("Invalid log path \"{0}\"", telemetryFilePath);
                }
            }

            if (telemetryServerUrl != null)
                cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryServerUrlKey, telemetryServerUrl);
        }

        public static void DisableTelemetry() {
            var cfg = GetConfigFile();
            logger.Debug("Disabling telemetry...");
            cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryStatusKey, false);
        }

        // app telemetry
        public static bool GetAppTelemetryStatus() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryStatusKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsAppTelemetryStatusDefault;
        }

        public static string GetAppTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryServerUrlKey) ?? string.Empty;
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling app telemetry... server: {0}", apptelemetryServerUrl));
            cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryStatusKey, true);

            if (apptelemetryServerUrl != null)
                cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryServerUrlKey, apptelemetryServerUrl);
        }

        public static void DisableAppTelemetry() {
            var cfg = GetConfigFile();
            logger.Debug("Disabling app telemetry...");
            cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryStatusKey, false);
        }

        public static string GetAppTelemetryFlags() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryEventFlagsKey) ?? string.Empty;
        }

        public static void SetAppTelemetryFlags(string flags) {
            var cfg = GetConfigFile();
            logger.Debug("Setting app telemetry flags...");
            if (flags != null)
                cfg.SetValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryEventFlagsKey, flags);
        }

        // update checking config
        public static bool GetCheckUpdates() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsCheckUpdatesKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsCheckUpdatesDefault;
        }

        public static void SetCheckUpdates(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsCheckUpdatesKey, state);
        }

        // auto update config
        public static bool GetAutoUpdate() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsAutoUpdateKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsAutoUpdateDefault;
        }

        public static void SetAutoUpdate(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsAutoUpdateKey, state);
        }

        // rocket mode config
        public static bool GetRocketMode() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsRocketModeKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsRocketModeDefault;
        }

        public static void SetRocketMode(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsRocketModeKey, state);
        }

        // logging level config
        public static PyRevitLogLevels GetLoggingLevel() {
            var cfg = GetConfigFile();
            var verboseCfg = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey);
            bool verbose = verboseCfg != null ? bool.Parse(verboseCfg) : PyRevit.ConfigsVerboseDefault;

            var debugCfg = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey);
            bool debug = debugCfg != null ? bool.Parse(debugCfg) : PyRevit.ConfigsDebugDefault;

            if (verbose && !debug)
                return PyRevitLogLevels.Verbose;
            else if (debug)
                return PyRevitLogLevels.Debug;

            return PyRevitLogLevels.None;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level) {
            var cfg = GetConfigFile();
            if (level == PyRevitLogLevels.None) {
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, false);
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Verbose) {
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, true);
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Debug) {
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, true);
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, true);
            }
        }

        // file logging config
        public static bool GetFileLogging() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsFileLoggingKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsFileLoggingDefault;
        }

        public static void SetFileLogging(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsFileLoggingKey, state);
        }

        // load beta config
        public static bool GetLoadBetaTools() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsLoadBetaKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsLoadBetaDefault;
        }

        public static void SetLoadBetaTools(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsLoadBetaKey, state);
        }

        // output style sheet config
        public static string GetOutputStyleSheet() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsOutputStyleSheet) ?? string.Empty;
        }

        public static void SetOutputStyleSheet(string outputCSSFilePath) {
            var cfg = GetConfigFile();
            if (File.Exists(outputCSSFilePath))
                cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsOutputStyleSheet, outputCSSFilePath);
        }

        // user access to tools
        public static bool GetUserCanUpdate() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanUpdateKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsUserCanUpdateDefault;
        }

        public static bool GetUserCanExtend() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanExtendKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsUserCanExtendDefault;
        }

        public static bool GetUserCanConfig() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanConfigKey);
            return status != null ? bool.Parse(status) : PyRevit.ConfigsUserCanConfigDefault;
        }

        public static void SetUserCanUpdate(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanUpdateKey, state);
        }

        public static void SetUserCanExtend(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanExtendKey, state);
        }

        public static void SetUserCanConfig(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanConfigKey, state);
        }

        // configurations private access methods  ====================================================================
        private static void InitConfigFile() {
            // get allusers seed config file
            // if admin config file exists, seed initial config states from there.
            var adminFile = PyRevit.FindConfigFileInDirectory(PyRevit.pyRevitProgramDataPath);
            if (adminFile != null)
                SeedConfig(false, setupFromTemplate: adminFile);
            else
                CommonUtils.EnsureFile(PyRevit.ConfigFilePath);
        }
    }
}
