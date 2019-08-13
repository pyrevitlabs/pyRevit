using System;
using System.Collections.Generic;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using MadMilkman.Ini;
using pyRevitLabs.NLog;


namespace pyRevitLabs.PyRevit {
    public struct PyRevitConfig {
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
            logger.Debug("Saving config file \"{0}\"", PyRevit.ConfigFilePath);
            try {
                _config.Save(PyRevit.ConfigFilePath);
            }
            catch (Exception ex) {
                throw new PyRevitException(string.Format("Failed to save config to \"{0}\". | {1}",
                                                         PyRevit.ConfigFilePath, ex.Message));
            }
        }

        // get config key value
        public string GetKeyValue(string sectionName, string keyName, string defaultValue = null, bool throwNotSetException = true) {
            logger.Debug(string.Format("Try getting config \"{0}:{1}\" ?? {2}", sectionName, keyName, defaultValue ?? "NULL"));
            if (_config.Sections.Contains(sectionName) && _config.Sections[sectionName].Keys.Contains(keyName))
                return _config.Sections[sectionName].Keys[keyName].Value as string;
            else {
                if (defaultValue == null && throwNotSetException)
                    throw new PyRevitConfigValueNotSet(sectionName, keyName);
                else {
                    logger.Debug(string.Format("Config is not set. Returning default value \"{0}\"", defaultValue ?? "NULL"));
                    return defaultValue;
                }
            }
        }

        // get config key value and make a string list out of it
        public List<string> GetKeyValueAsList(string sectionName, string keyName, bool throwNotSetException = true) {
            logger.Debug("Try getting config as list \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetKeyValue(sectionName, keyName, "[]", throwNotSetException: throwNotSetException);

            return stringValue.ConvertFromTomlListString();
        }

        // get config key value and make a string dictionary out of it
        public  Dictionary<string, string> GetKeyValueAsDict(string sectionName, string keyName, IEnumerable<string> defaultValue = null, bool throwNotSetException = true) {
            logger.Debug("Try getting config as dict \"{0}:{1}\"", sectionName, keyName);
            var stringValue = GetKeyValue(sectionName,
                                          keyName, defaultValue: "{}",
                                          throwNotSetException: throwNotSetException);
            return stringValue.ConvertFromTomlDictString();
        }

        // set config key value, creates the config if not set yet
        public void SetKeyValue(string sectionName, string keyName, string stringValue) {
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
        public void SetKeyValue(string sectionName, string keyName, bool boolValue) {
            SetKeyValue(sectionName, keyName, boolValue.ConvertToTomlBoolString());
        }

        // sets config key value as int
        public void SetKeyValue(string sectionName, string keyName, int intValue) {
            SetKeyValue(sectionName, keyName, intValue.ConvertToTomlIntString());
        }

        // sets config key value as string list
        public void SetKeyValue(string sectionName, string keyName, IEnumerable<string> listString) {
            SetKeyValue(sectionName, keyName, listString.ConvertToTomlListString());
        }

        // sets config key value as string dictionary
        public void SetKeyValue(string sectionName, string keyName, IDictionary<string, string> dictString) {
            SetKeyValue(sectionName, keyName, dictString.ConvertToTomlDictString());
        }
    }
}
