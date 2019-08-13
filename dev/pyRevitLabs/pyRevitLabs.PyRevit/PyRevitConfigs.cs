using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text.RegularExpressions;
using System.Security.Principal;
using System.Text;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.Json.Linq;
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

        // managing configs ==========================================================================================
        // pyrevit config getter/setter
        // telemetry config
        // @handled @logs
        public static string FindConfigFileInDirectory(string sourcePath) {
            var configMatcher = new Regex(PyRevit.ConfigsFileRegexPattern, RegexOptions.IgnoreCase);
            if (CommonUtils.VerifyPath(sourcePath))
                foreach (string subFile in Directory.GetFiles(sourcePath))
                    if (configMatcher.IsMatch(Path.GetFileName(subFile)))
                        return subFile;
            return null;
        }

        public static bool GetTelemetryStatus() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsTelemetrySection,
                                          PyRevit.ConfigsTelemetryStatusKey));
        }

        public static string GetTelemetryFilePath() {
            return GetKeyValue(PyRevit.ConfigsTelemetrySection,
                               PyRevit.ConfigsTelemetryFilePathKey);
        }

        public static string GetTelemetryServerUrl() {
            return GetKeyValue(PyRevit.ConfigsTelemetrySection,
                               PyRevit.ConfigsTelemetryServerUrlKey);
        }

        public static void EnableTelemetry(string telemetryFilePath = null, string telemetryServerUrl = null) {
            logger.Debug(string.Format("Enabling telemetry... path: \"{0}\" server: {1}",
                                       telemetryFilePath, telemetryServerUrl));
            SetKeyValue(PyRevit.ConfigsTelemetrySection,
                        PyRevit.ConfigsTelemetryStatusKey,
                        true);

            if (telemetryFilePath != null)
                if (CommonUtils.VerifyPath(telemetryFilePath))
                    SetKeyValue(PyRevit.ConfigsTelemetrySection,
                                PyRevit.ConfigsTelemetryFilePathKey,
                                telemetryFilePath);
                else
                    logger.Debug("Invalid log path \"{0}\"", telemetryFilePath);

            if (telemetryServerUrl != null)
                SetKeyValue(PyRevit.ConfigsTelemetrySection,
                            PyRevit.ConfigsTelemetryServerUrlKey,
                            telemetryServerUrl);
        }

        public static void DisableTelemetry() {
            logger.Debug("Disabling telemetry...");
            SetKeyValue(PyRevit.ConfigsTelemetrySection,
                        PyRevit.ConfigsTelemetryStatusKey,
                        false);
        }

        // app telemetry
        public static bool GetAppTelemetryStatus() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsTelemetrySection,
                                          PyRevit.ConfigsAppTelemetryStatusKey));
        }

        public static string GetAppTelemetryServerUrl() {
            return GetKeyValue(PyRevit.ConfigsTelemetrySection,
                               PyRevit.ConfigsAppTelemetryServerUrlKey);
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null) {
            logger.Debug(string.Format("Enabling app telemetry... server: {0}", apptelemetryServerUrl));
            SetKeyValue(PyRevit.ConfigsTelemetrySection,
                        PyRevit.ConfigsAppTelemetryStatusKey,
                        true);

            if (apptelemetryServerUrl != null)
                SetKeyValue(PyRevit.ConfigsTelemetrySection,
                            PyRevit.ConfigsAppTelemetryServerUrlKey,
                            apptelemetryServerUrl);
        }

        public static void DisableAppTelemetry() {
            logger.Debug("Disabling app telemetry...");
            SetKeyValue(PyRevit.ConfigsTelemetrySection,
                        PyRevit.ConfigsAppTelemetryStatusKey,
                        false);
        }

        public static string GetAppTelemetryFlags() {
            return GetKeyValue(PyRevit.ConfigsTelemetrySection,
                               PyRevit.ConfigsAppTelemetryEventFlagsKey);
        }

        public static void SetAppTelemetryFlags(string flags) {
            logger.Debug("Setting app telemetry flags...");
            if (flags != null)
                SetKeyValue(PyRevit.ConfigsTelemetrySection,
                            PyRevit.ConfigsAppTelemetryEventFlagsKey,
                            flags);
        }

        // update checking config
        // @handled @logs
        public static bool GetCheckUpdates() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection,
                                             PyRevit.ConfigsCheckUpdatesKey));
        }

        public static void SetCheckUpdates(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsCheckUpdatesKey, state);
        }

        // auto update config
        // @handled @logs
        public static bool GetAutoUpdate() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection,
                                          PyRevit.ConfigsAutoUpdateKey));
        }

        public static void SetAutoUpdate(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsAutoUpdateKey, state);
        }

        // rocket mode config
        // @handled @logs
        public static bool GetRocketMode() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection,
                                          PyRevit.ConfigsRocketModeKey));
        }

        public static void SetRocketMode(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsRocketModeKey, state);
        }

        // logging level config
        // @handled @logs
        public static PyRevitLogLevels GetLoggingLevel() {
            bool verbose = bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection,
                                                  PyRevit.ConfigsVerboseKey));
            bool debug = bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection,
                                                PyRevit.ConfigsDebugKey));

            if (verbose && !debug)
                return PyRevitLogLevels.Verbose;
            else if (debug)
                return PyRevitLogLevels.Debug;

            return PyRevitLogLevels.None;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level) {
            if (level == PyRevitLogLevels.None) {
                SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, false);
                SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Verbose) {
                SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, true);
                SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, false);
            }

            if (level == PyRevitLogLevels.Debug) {
                SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsVerboseKey, true);
                SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsDebugKey, true);
            }
        }

        // file logging config
        // @handled @logs
        public static bool GetFileLogging() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection,
                                          PyRevit.ConfigsFileLoggingKey));
        }

        public static void SetFileLogging(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsFileLoggingKey, state);
        }

        // load beta config
        // @handled @logs
        public static bool GetLoadBetaTools() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsLoadBetaKey));
        }

        public static void SetLoadBetaTools(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsLoadBetaKey, state);
        }

        // output style sheet config
        // @handled @logs
        public static string GetOutputStyleSheet() {
            return GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsOutputStyleSheet);
        }

        public static void SetOutputStyleSheet(string outputCSSFilePath) {
            if (File.Exists(outputCSSFilePath))
                SetKeyValue(PyRevit.ConfigsCoreSection,
                            PyRevit.ConfigsOutputStyleSheet,
                            outputCSSFilePath);
        }

        // user access to tools
        // @handled @logs
        public static bool GetUserCanUpdate() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanUpdateKey));
        }

        public static bool GetUserCanExtend() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanExtendKey));
        }

        public static bool GetUserCanConfig() {
            return bool.Parse(GetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanConfigKey));
        }

        public static void SetUserCanUpdate(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanUpdateKey, state);
        }

        public static void SetUserCanExtend(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanExtendKey, state);
        }

        public static void SetUserCanConfig(bool state) {
            SetKeyValue(PyRevit.ConfigsCoreSection, PyRevit.ConfigsUserCanConfigKey, state);
        }

        // deletes config file
        // @handled @logs
        public static void DeleteConfigs() {
            if (File.Exists(PyRevit.pyRevitConfigFilePath))
                try {
                    File.Delete(PyRevit.pyRevitConfigFilePath);
                }
                catch (Exception ex) {
                    throw new PyRevitException(string.Format("Failed deleting config file \"{0}\" | {1}",
                                                             PyRevit.pyRevitConfigFilePath, ex.Message));
                }
        }

        // generic configuration public access  ======================================================================
        // @handled @logs
        public static string GetConfig(string sectionName, string keyName) {
            return GetKeyValue(sectionName, keyName);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, bool boolValue) {
            SetKeyValue(sectionName, keyName, boolValue);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, int intValue) {
            SetKeyValue(sectionName, keyName, intValue);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, string stringValue) {
            SetKeyValue(sectionName, keyName, stringValue);
        }

        // @handled @logs
        public static void SetConfig(string sectionName, string keyName, IEnumerable<string> stringListValue) {
            SetKeyValue(sectionName, keyName, stringListValue);
        }

        // copy config file into all users directory as seed config file
        // create user config file based on a template
        // @handled @logs
        public static void SeedConfig(bool makeCurrentUserAsOwner = false, string setupFromTemplate = null) {
            // if setupFromTemplate is not specified: copy current config into Allusers folder
            // if setupFromTemplate is specified: copy setupFromTemplate as the main config
            string sourceFile = setupFromTemplate != null ? setupFromTemplate : PyRevit.pyRevitConfigFilePath;
            string targetFile = setupFromTemplate != null ? PyRevit.pyRevitConfigFilePath : PyRevit.pyRevitSeedConfigFilePath;

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

        // configurations private access methods  ====================================================================
        private static void InitConfigFile() {
            // get allusers seed config file
            var adminFile = FindConfigFileInDirectory(PyRevit.pyRevitProgramDataPath);
            if (adminFile != null)
                SeedConfig(false, setupFromTemplate: adminFile);
            else
                CommonUtils.EnsureFile(PyRevit.pyRevitConfigFilePath);
        }

        private static IniFile GetConfigFile() {
            // INI formatting
            var cfgOps = new IniOptions();
            cfgOps.KeySpaceAroundDelimiter = true;
            cfgOps.Encoding = CommonUtils.GetUTF8NoBOMEncoding();
            IniFile cfgFile = new IniFile(cfgOps);

            // default to current user config
            string configFile = PyRevit.pyRevitConfigFilePath;
            // make sure the file exists and if not create an empty one
            if (!CommonUtils.VerifyFile(configFile))
                InitConfigFile();

            // load the config file
            cfgFile.Load(configFile);
            return cfgFile;
        }

        // save config file to standard location
        // @handled @logs
        private static void SaveConfigFile(IniFile cfgFile) {
            logger.Debug("Saving config file \"{0}\"", PyRevit.pyRevitConfigFilePath);
            try {
                cfgFile.Save(PyRevit.pyRevitConfigFilePath);
            }
            catch (Exception ex) {
                throw new PyRevitException(string.Format("Failed to save config to \"{0}\". | {1}",
                                                         PyRevit.pyRevitConfigFilePath, ex.Message));
            }
        }

        // get config key value
        // @handled @logs
        private static string GetKeyValue(string sectionName,
                                          string keyName,
                                          string defaultValue = null,
                                          bool throwNotSetException = true) {
            var c = GetConfigFile();
            logger.Debug(string.Format("Try getting config \"{0}:{1}\" ?? {2}",
                                       sectionName, keyName, defaultValue ?? "NULL"));
            if (c.Sections.Contains(sectionName) && c.Sections[sectionName].Keys.Contains(keyName))
                return c.Sections[sectionName].Keys[keyName].Value as string;
            else {
                if (defaultValue == null && throwNotSetException)
                    throw new PyRevitConfigValueNotSet(sectionName, keyName);
                else {
                    logger.Debug(string.Format("Config is not set. Returning default value \"{0}\"",
                                               defaultValue ?? "NULL"));
                    return defaultValue;
                }
            }
        }

        // get config key value and make a string list out of it
        // @handled @logs
        public static List<string> GetKeyValueAsList(string sectionName,
                                                      string keyName,
                                                      bool throwNotSetException = true) {
            logger.Debug("Try getting config as list \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetKeyValue(sectionName, keyName, "[]", throwNotSetException: throwNotSetException);

            return stringValue.ConvertFromTomlListString();
        }

        // get config key value and make a string dictionary out of it
        // @handled @logs
        public static Dictionary<string, string> GetKeyValueAsDict(string sectionName,
                                                                    string keyName,
                                                                    IEnumerable<string> defaultValue = null,
                                                                    bool throwNotSetException = true) {
            logger.Debug("Try getting config as dict \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetKeyValue(sectionName,
                                          keyName, defaultValue: "{}",
                                          throwNotSetException: throwNotSetException);
            return stringValue.ConvertFromTomlDictString();
        }

        // updates config key value, creates the config if not set yet
        // @handled @logs
        private static void UpdateKeyValue(string sectionName, string keyName, string stringValue) {
            if (stringValue != null) {
                var c = GetConfigFile();

                if (!c.Sections.Contains(sectionName)) {
                    logger.Debug("Adding config section \"{0}\"", sectionName);
                    c.Sections.Add(sectionName);
                }

                if (!c.Sections[sectionName].Keys.Contains(keyName)) {
                    logger.Debug("Adding config key \"{0}:{1}\"", sectionName, keyName);
                    c.Sections[sectionName].Keys.Add(keyName);
                }

                logger.Debug("Updating config \"{0}:{1} = {2}\"", sectionName, keyName, stringValue);
                c.Sections[sectionName].Keys[keyName].Value = stringValue;

                SaveConfigFile(c);
            }
            else
                logger.Debug("Can not set null value for \"{0}:{1}\"", sectionName, keyName);
        }

        // sets config key value as bool
        // @handled @logs
        public static void SetKeyValue(string sectionName, string keyName, bool boolValue) {
            UpdateKeyValue(sectionName, keyName, boolValue.ConvertToTomlBoolString());
        }

        // sets config key value as int
        // @handled @logs
        public static void SetKeyValue(string sectionName, string keyName, int intValue) {
            UpdateKeyValue(sectionName, keyName, intValue.ConvertToTomlIntString());
        }

        // sets config key value as string
        // @handled @logs
        public static void SetKeyValue(string sectionName, string keyName, string stringValue) {
            UpdateKeyValue(sectionName, keyName, stringValue.ConvertToTomlString());
        }

        // sets config key value as string list
        // @handled @logs
        public static void SetKeyValue(string sectionName, string keyName, IEnumerable<string> listString) {
            UpdateKeyValue(sectionName, keyName, listString.ConvertToTomlListString());
        }

        // sets config key value as string dictionary
        // @handled @logs
        public static void SetKeyValue(string sectionName, string keyName, IDictionary<string, string> dictString) {
            UpdateKeyValue(sectionName, keyName, dictString.ConvertToTomlDictString());
        }

        // updates the config value for registered clones
        // @handled @logs
        public static void SaveRegisteredClones(IEnumerable<PyRevitClone> clonesList) {
            var newValueDic = new Dictionary<string, string>();
            foreach (var clone in clonesList)
                newValueDic[clone.Name] = clone.ClonePath;

            SetKeyValue(PyRevit.EnvConfigsSectionName,
                        PyRevit.EnvConfigsInstalledClonesKey,
                        newValueDic);
        }

        // updates the config value for extensions lookup sources
        // @handled @logs
        public static void SaveExtensionLookupSources(IEnumerable<string> sourcesList) {
            SetKeyValue(PyRevit.EnvConfigsSectionName,
                        PyRevit.EnvConfigsExtensionLookupSourcesKey,
                        sourcesList);
        }
    }
}
