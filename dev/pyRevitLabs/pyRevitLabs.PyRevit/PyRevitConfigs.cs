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
        Quiet,
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
        // general telemetry
        public static bool GetUTCStamps() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryUTCTimestampsKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsTelemetryUTCTimestampsDefault;
        }

        public static void SetUTCStamps(bool state) {
            var cfg = GetConfigFile();
            logger.Debug("Setting telemetry utc timestamps...");
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryUTCTimestampsKey, state);
        }

        // routes
        public static bool GetRoutesServerStatus() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesServerKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsRoutesServerDefault;
        }

        public static void SetRoutesServerStatus(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesServerKey, state);
        }

        public static void EnableRoutesServer() => SetRoutesServerStatus(true);

        public static void DisableRoutesServer() => SetRoutesServerStatus(false);

        public static string GetRoutesServerHost() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesHostKey);
        }

        public static void SetRoutesServerHost(string host) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesHostKey, host);
        }

        public static int GetRoutesServerPort(int revitYear) {
            var cfg = GetConfigFile();
            var portsDict = cfg.GetDictValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesPortsKey);
            if (portsDict is null || !portsDict.ContainsKey(revitYear.ToString()))
                return revitYear + PyRevitConsts.ConfigsRoutesPortsDefault;
            else
                return int.Parse(portsDict[revitYear.ToString()]);
        }

        public static void SetRoutesServerPort(int revitYear, int port) {
            var cfg = GetConfigFile();
            var portsDict = cfg.GetDictValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesPortsKey);
            if (portsDict is null)
                portsDict = new Dictionary<string, string>();
            
            portsDict[revitYear.ToString()] = port.ToString();
            cfg.SetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesPortsKey, portsDict);
        }

        public static void RemoveRoutesServerPort(int revitYear) {
            var cfg = GetConfigFile();
            var portsDict = cfg.GetDictValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesPortsKey);
            if (portsDict != null) {
                portsDict.Remove(revitYear.ToString());
                cfg.SetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsRoutesPortsKey, portsDict);
            }
        }

        public static bool GetRoutesLoadCoreAPIStatus() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsLoadCoreAPIKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsRoutesServerDefault;
        }

        public static void SetRoutesLoadCoreAPIStatus(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsRoutesSection, PyRevitConsts.ConfigsLoadCoreAPIKey, state);
        }


        // telemetry
        public static bool GetTelemetryStatus() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryStatusKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsTelemetryStatusDefault;
        }

        public static void SetTelemetryStatus(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryStatusKey, state);
        }

        public static string GetTelemetryFilePath() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryFileDirKey) ?? string.Empty;
        }

        public static string GetTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryServerUrlKey) ?? string.Empty;
        }

        public static void EnableTelemetry(string telemetryFileDir = null, string telemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling telemetry... path: \"{0}\" server: {1}",
                                       telemetryFileDir, telemetryServerUrl));
            SetTelemetryStatus(true);

            if (telemetryFileDir != null) {
                if (telemetryFileDir == string.Empty) {
                    // set empty value
                    cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryFileDirKey, telemetryFileDir);
                }
                else {
                    if (CommonUtils.VerifyPath(telemetryFileDir))
                        cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsTelemetryFileDirKey, telemetryFileDir);
                    else
                        logger.Debug("Invalid log path \"{0}\"", telemetryFileDir);
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

        public static void SetAppTelemetryStatus(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryStatusKey, state);
        }

        public static string GetAppTelemetryServerUrl() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsTelemetrySection, PyRevitConsts.ConfigsAppTelemetryServerUrlKey) ?? string.Empty;
        }

        public static void EnableAppTelemetry(string apptelemetryServerUrl = null) {
            var cfg = GetConfigFile();
            logger.Debug(string.Format("Enabling app telemetry... server: {0}", apptelemetryServerUrl));
            SetAppTelemetryStatus(true);

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

        // caching
        public static bool GetBinaryCaches() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsBinaryCacheKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsBinaryCacheDefault;
        }

        public static void SetBinaryCaches(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsBinaryCacheKey, state);
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

            return PyRevitLogLevels.Quiet;
        }

        public static void SetLoggingLevel(PyRevitLogLevels level) {
            var cfg = GetConfigFile();
            if (level == PyRevitLogLevels.Quiet) {
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

        // misc startup
        public static int GetStartupLogTimeout() {
            var cfg = GetConfigFile();
            var timeout = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsStartupLogTimeoutKey);
            return timeout != null ? int.Parse(timeout) : PyRevitConsts.ConfigsStartupLogTimeoutDefault;
        }

        public static void SetStartupLogTimeout(int timeout) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsStartupLogTimeoutKey, timeout);
        }

        public static string GetRequiredHostBuild() {
            var cfg = GetConfigFile();
            var timeout = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsRequiredHostBuildKey);
            return timeout != null ? timeout : string.Empty;
        }

        public static void SetRequiredHostBuild(string buildnumber) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsRequiredHostBuildKey, buildnumber);
        }

        public static int GetMinHostDriveFreeSpace() {
            var cfg = GetConfigFile();
            var timeout = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsMinDriveSpaceKey);
            return timeout != null ? int.Parse(timeout) : 0;
        }

        public static void SetMinHostDriveFreeSpace(int freespace) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsMinDriveSpaceKey, freespace);
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

        // cpythonengine
        public static int GetCpythonEngineVersion() {
            var cfg = GetConfigFile();
            var timeout = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsCPythonEngineKey);
            return timeout != null ? int.Parse(timeout) : PyRevitConsts.ConfigsCPythonEngineDefault;
        }

        public static void SetCpythonEngineVersion(int version) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsCPythonEngineKey, version);
        }

        // ux ui
        public static string GetUserLocale() {
            var cfg = GetConfigFile();
            return cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsLocaleKey) ?? string.Empty;
        }

        public static void SetUserLocale(string localCode) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsLocaleKey, localCode);
        }

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

        public static bool GetColorizeDocs() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsColorizeDocsKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsColorizeDocsDefault;
        }

        public static void SetColorizeDocs(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsColorizeDocsKey, state);
        }

        public static bool GetAppendTooltipEx() {
            var cfg = GetConfigFile();
            var status = cfg.GetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsAppendTooltipExKey);
            return status != null ? bool.Parse(status) : PyRevitConsts.ConfigsAppendTooltipExDefault;
        }

        public static void SetAppendTooltipEx(bool state) {
            var cfg = GetConfigFile();
            cfg.SetValue(PyRevitConsts.ConfigsCoreSection, PyRevitConsts.ConfigsAppendTooltipExKey, state);
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
