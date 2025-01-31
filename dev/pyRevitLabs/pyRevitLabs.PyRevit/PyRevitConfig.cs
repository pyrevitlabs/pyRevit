using System;
using System.Collections.Generic;
using System.IO;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.NLog;


namespace pyRevitLabs.PyRevit {
    public class PyRevitConfig {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private IniFile _config;
        private bool _adminMode;

        public string ConfigFilePath { get; private set; }

        public PyRevitConfig(string cfgFilePath, bool adminMode = false) {
            if (cfgFilePath is null)
                throw new PyRevitException("Config file path can not be null.");

            if (CommonUtils.VerifyFile(cfgFilePath))
            {
                ConfigFilePath = cfgFilePath;

                // INI formatting
                var cfgOps = new IniOptions();
                cfgOps.KeySpaceAroundDelimiter = true;
                cfgOps.Encoding = CommonUtils.GetUTF8NoBOMEncoding();
                _config = new IniFile(cfgOps);

                using (var cfgStream = File.Open(cfgFilePath, FileMode.Open, FileAccess.Read, FileShare.Read)) {
                    _config.Load(cfgStream);
                }
                _adminMode = adminMode;
            }
            else
                throw new PyRevitException($"Can not access config file at {cfgFilePath}");
        }

        // save config file to standard location
        public void SaveConfigFile() {
            if (_adminMode) {
                logger.Debug("Config is in admin mode. Skipping save");
                return;
            }

            logger.Debug("Saving config file \"{0}\"", PyRevitConsts.ConfigFilePath);
            try {
                _config.Save(PyRevitConsts.ConfigFilePath);
            }
            catch (Exception ex)
            {
                throw new PyRevitException(
                    $"Failed to save config to \"{PyRevitConsts.ConfigFilePath}\". | {ex.Message}");
            }
        }

        // get config key value
        public string GetValue(string sectionName, string keyName) {
            logger.Debug(string.Format("Try getting config \"{0}:{1}\"", sectionName, keyName));
            if (_config.Sections.Contains(sectionName) && _config.Sections[sectionName].Keys.Contains(keyName)) {
                var cfgValue = _config.Sections[sectionName].Keys[keyName].Value as string;
                logger.Debug(string.Format("Config \"{0}:{1}\" = \"{2}\"", sectionName, keyName, cfgValue));
                return cfgValue;
            }
            else {
                logger.Debug(string.Format("Config \"{0}:{1}\" not set.", sectionName, keyName));
                return null;
            }
        }

        // get config key value and make a string list out of it
        public List<string> GetListValue(string sectionName, string keyName) {
            logger.Debug("Try getting config as list \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetValue(sectionName, keyName);
            if (stringValue != null)
                return stringValue.ConvertFromTomlListString();
            else
                return null;
        }

        // get config key value and make a string dictionary out of it
        public Dictionary<string, string> GetDictValue(string sectionName, string keyName) {
            logger.Debug("Try getting config as dict \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetValue(sectionName, keyName);
            if (stringValue != null)
                return stringValue.ConvertFromTomlDictString();
            else
                return null;
        }

        // set config key value, creates the config if not set yet
        public void SetValue(string sectionName, string keyName, string stringValue) {
            if (stringValue is null)
            {
                logger.Debug("Can not set null value for \"{0}:{1}\"", sectionName, keyName);
                return;
            }
            if (!_config.Sections.Contains(sectionName))
            {
                logger.Debug("Adding config section \"{0}\"", sectionName);
                _config.Sections.Add(sectionName);
            }
            if (!_config.Sections[sectionName].Keys.Contains(keyName))
            {
                logger.Debug("Adding config key \"{0}:{1}\"", sectionName, keyName);
                _config.Sections[sectionName].Keys.Add(keyName);
            }
            if (_config.Sections[sectionName].Keys[keyName].Value == stringValue)
            {
                logger.Debug("Config \"{0}:{1}\" already set to \"{2}\"", sectionName, keyName, stringValue);
                return;
            }
            logger.Debug("Updating config \"{0}:{1} = {2}\"", sectionName, keyName, stringValue);
            _config.Sections[sectionName].Keys[keyName].Value = stringValue;
            SaveConfigFile();
        }

        // sets config key value as bool
        public void SetValue(string sectionName, string keyName, bool boolValue) {
            SetValue(sectionName, keyName, boolValue.ConvertToTomlBoolString());
        }

        // sets config key value as int
        public void SetValue(string sectionName, string keyName, int intValue) {
            SetValue(sectionName, keyName, intValue.ConvertToTomlIntString());
        }

        // sets config key value as string list
        public void SetValue(string sectionName, string keyName, IEnumerable<string> listString) {
            SetValue(sectionName, keyName, listString.ConvertToTomlListString());
        }

        // sets config key value as string dictionary
        public void SetValue(string sectionName, string keyName, IDictionary<string, string> dictString) {
            SetValue(sectionName, keyName, dictString.ConvertToTomlDictString());
        }
    
        // removes a value from config file
        public bool DeleteValue(string sectionName, string keyName) {
            logger.Debug(string.Format("Try getting config \"{0}:{1}\"", sectionName, keyName));
            if (_config.Sections.Contains(sectionName) && _config.Sections[sectionName].Keys.Contains(keyName)) {
                logger.Debug(string.Format("Removing config \"{0}:{1}\"", sectionName, keyName));
                return _config.Sections[sectionName].Keys.Remove(keyName);
            }
            else {
                logger.Debug(string.Format("Config \"{0}:{1}\" not set.", sectionName, keyName));
                return false;
            }
        }
    }
}
