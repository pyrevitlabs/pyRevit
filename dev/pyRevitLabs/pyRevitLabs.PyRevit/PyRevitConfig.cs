using System;
using System.Collections.Generic;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.NLog;


namespace pyRevitLabs.PyRevit {
    public class PyRevitConfig {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        private IniFile _config;

        public string ConfigFilePath { get; private set; }

        public PyRevitConfig(string cfgFilePath) {
            if (cfgFilePath != null) {
                if (CommonUtils.VerifyFile(cfgFilePath)) {
                    ConfigFilePath = cfgFilePath;

                    // INI formatting
                    var cfgOps = new IniOptions();
                    cfgOps.KeySpaceAroundDelimiter = true;
                    cfgOps.Encoding = CommonUtils.GetUTF8NoBOMEncoding();
                    _config = new IniFile(cfgOps);

                    _config.Load(cfgFilePath);
                }
                else
                    throw new PyRevitException("Can not access config file path.");
            }
            else
                throw new PyRevitException("Config file path can not be null.");
        }

        // save config file to standard location
        public void SaveConfigFile() {
            logger.Debug("Saving config file \"{0}\"", PyRevitConsts.ConfigFilePath);
            try {
                _config.Save(PyRevitConsts.ConfigFilePath);
            }
            catch (Exception ex) {
                throw new PyRevitException(string.Format("Failed to save config to \"{0}\". | {1}",
                                                         PyRevitConsts.ConfigFilePath, ex.Message));
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
            if (stringValue != null) {
                if (!_config.Sections.Contains(sectionName)) {
                    logger.Debug("Adding config section \"{0}\"", sectionName);
                    _config.Sections.Add(sectionName);
                }

                if (!_config.Sections[sectionName].Keys.Contains(keyName)) {
                    logger.Debug("Adding config key \"{0}:{1}\"", sectionName, keyName);
                    _config.Sections[sectionName].Keys.Add(keyName);
                }

                logger.Debug("Updating config \"{0}:{1} = {2}\"", sectionName, keyName, stringValue);
                _config.Sections[sectionName].Keys[keyName].Value = stringValue;

                SaveConfigFile();
            }
            else
                logger.Debug("Can not set null value for \"{0}:{1}\"", sectionName, keyName);
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
    }
}
