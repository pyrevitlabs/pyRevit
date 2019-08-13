using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Principal;

using pyRevitLabs.Common;

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
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryStatusKey));
        }

        public static string GetTelemetryFilePath() {
            var cfg = GetConfigFile();
            return cfg.GetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryFilePathKey);
        }

        public static string GetTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryServerUrlKey);
        }

        public static void EnableTelemetry(string telemetryFilePath = null, string telemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling telemetry... path: \"{0}\" server: {1}",
                                       telemetryFilePath, telemetryServerUrl));
            cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryStatusKey, true);

            if (telemetryFilePath != null)
                if (CommonUtils.VerifyPath(telemetryFilePath))
                    cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryFilePathKey, telemetryFilePath);
                else
                    logger.Debug("Invalid log path \"{0}\"", telemetryFilePath);

            if (telemetryServerUrl != null)
                cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryServerUrlKey, telemetryServerUrl);
        }

        public static void DisableTelemetry() {
            var cfg = GetConfigFile();
            logger.Debug("Disabling telemetry...");
            cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsTelemetryStatusKey, false);
        }

        // app telemetry
        public static bool GetAppTelemetryStatus() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryStatusKey));
        }

        public static string GetAppTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryServerUrlKey);
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling app telemetry... server: {0}", apptelemetryServerUrl));
            cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryStatusKey, true);

            if (apptelemetryServerUrl != null)
                cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryServerUrlKey, apptelemetryServerUrl);
        }

        public static void DisableAppTelemetry() {
            var cfg = GetConfigFile();
            logger.Debug("Disabling app telemetry...");
            cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryStatusKey, false);
        }

        public static string GetAppTelemetryFlags() {
            var cfg = GetConfigFile();
            return cfg.GetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryEventFlagsKey);
        }

        public static void SetAppTelemetryFlags(string flags) {
            var cfg = GetConfigFile();
            logger.Debug("Setting app telemetry flags...");
            if (flags != null)
                cfg.SetKeyValue(PyRevit.ConfigsTelemetrySection, PyRevit.ConfigsAppTelemetryEventFlagsKey, flags);
        }

        // clones
        // updates the config value for registered clones
        public static void SaveRegisteredClones(IEnumerable<PyRevitClone> clonesList) {
            var cfg = GetConfigFile();
            var newValueDic = new Dictionary<string, string>();
            foreach (var clone in clonesList)
                newValueDic[clone.Name] = clone.ClonePath;

            cfg.SetKeyValue(PyRevit.EnvConfigsSectionName, PyRevit.EnvConfigsInstalledClonesKey, newValueDic);
        }

        // extensions
        // updates the config value for extensions lookup sources
        public static void SaveExtensionLookupSources(IEnumerable<string> sourcesList) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.EnvConfigsSectionName, PyRevit.EnvConfigsExtensionLookupSourcesKey, sourcesList);
        }

        // update checking config
        public static bool GetCheckUpdates() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsCheckUpdatesKey));
        }

        public static void SetCheckUpdates(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsCheckUpdatesKey, state);
        }

        // auto update config
        public static bool GetAutoUpdate() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsAutoUpdateKey));
        }

        public static void SetAutoUpdate(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsAutoUpdateKey, state);
        }

        // rocket mode config
        public static bool GetRocketMode() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsRocketModeKey));
        }

        public static void SetRocketMode(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsRocketModeKey, state);
        }

        // logging level config
        public static PyRevitLogLevels GetLoggingLevel() {
            var cfg = GetConfigFile();
            bool verbose = bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey));
            bool debug = bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey));

            if (verbose && !debug)
                return PyRevitLogLevels.Verbose;
            else if (debug)
                return PyRevitLogLevels.Debug;

            return PyRevitLogLevels.None;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level) {
            var cfg = GetConfigFile();
            if (level == PyRevitLogLevels.None) {
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, false);
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Verbose) {
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, true);
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Debug) {
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, true);
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, true);
            }
        }

        // file logging config
        public static bool GetFileLogging() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsFileLoggingKey));
        }

        public static void SetFileLogging(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsFileLoggingKey, state);
        }

        // load beta config
        public static bool GetLoadBetaTools() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsLoadBetaKey));
        }

        public static void SetLoadBetaTools(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsLoadBetaKey, state);
        }

        // output style sheet config
        public static string GetOutputStyleSheet() {
            var cfg = GetConfigFile();
            return cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsOutputStyleSheet);
        }

        public static void SetOutputStyleSheet(string outputCSSFilePath) {
            var cfg = GetConfigFile();
            if (File.Exists(outputCSSFilePath))
                cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsOutputStyleSheet, outputCSSFilePath);
        }

        // user access to tools
        public static bool GetUserCanUpdate() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanUpdateKey));
        }

        public static bool GetUserCanExtend() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanExtendKey));
        }

        public static bool GetUserCanConfig() {
            var cfg = GetConfigFile();
            return bool.Parse(cfg.GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanConfigKey));
        }

        public static void SetUserCanUpdate(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanUpdateKey, state);
        }

        public static void SetUserCanExtend(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanExtendKey, state);
        }

        public static void SetUserCanConfig(bool state) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanConfigKey, state);
        }

        // generic configuration public access  ======================================================================
        public static string GetConfig(string sectionName, string keyName) {
            var cfg = GetConfigFile();
            return cfg.GetKeyValue(sectionName, keyName);
        }

        public static List<string> GetListConfig(string sectionName, string keyName) {
            var cfg = GetConfigFile();
            return cfg.GetKeyValueAsList(sectionName, keyName, throwNotSetException: false);
        }

        public static void SetConfig(string sectionName, string keyName, bool boolValue) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(sectionName, keyName, boolValue);
        }

        public static void SetConfig(string sectionName, string keyName, int intValue) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(sectionName, keyName, intValue);
        }

        public static void SetConfig(string sectionName, string keyName, string stringValue) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(sectionName, keyName, stringValue);
        }

        public static void SetConfig(string sectionName, string keyName, IEnumerable<string> stringListValue) {
            var cfg = GetConfigFile();
            cfg.SetKeyValue(sectionName, keyName, stringListValue);
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
