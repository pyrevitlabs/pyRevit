using System;
using System.Collections.Generic;
using System.Linq;

using pyRevitLabs.Configurations.Abstractions;
using pyRevitLabs.NLog;


namespace pyRevitLabs.PyRevit
{
    public class PyRevitConfig
    {
        private readonly IConfiguration _configuration;
        private static readonly Logger _logger = LogManager.GetCurrentClassLogger();

        public PyRevitConfig(IConfiguration configuration)
        {
            _configuration = configuration ?? throw new ArgumentNullException(nameof(configuration));
        }

        /// <summary>
        /// Get config key value
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <returns></returns>
        public string GetValue(string sectionName, string keyName)
        {
            _logger.Debug("Try getting config value \"{@SectionName}:{@KeyName}\"", sectionName, keyName);
            return _configuration.GetValueOrDefault<string>(sectionName, keyName);
        }

        /// <summary>
        /// Get config key value and make a string list out of it
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <returns></returns>
        public List<string> GetListValue(string sectionName, string keyName)
        {
            _logger.Debug("Try getting config as list value \"{SectionName}:{KeyName}\"", sectionName, keyName);
            return _configuration.GetValueOrDefault(sectionName, keyName, new List<string>());
        }

        /// <summary>
        /// Get config key value and make a string dictionary out of it
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <returns></returns>
        public Dictionary<string, string> GetDictValue(string sectionName, string keyName)
        {
            _logger.Debug("Try getting config as dict value \"{SectionName}:{KeyName}\"", sectionName, keyName);
            return _configuration.GetValueOrDefault(sectionName, keyName, new Dictionary<string, string>());
        }

        /// <summary>
        /// Set config key value, creates the config if not set yet
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <param name="value"></param>
        public void SetValue(string sectionName, string keyName, string value)
        {
            _configuration.SetValue(sectionName, keyName, value);
        }

        /// <summary>
        /// Sets config key value as bool
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <param name="value"></param>
        public void SetValue(string sectionName, string keyName, bool value)
        {
            _configuration.SetValue(sectionName, keyName, value);
        }

        /// <summary>
        /// Sets config key value as int
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <param name="value"></param>
        public void SetValue(string sectionName, string keyName, int value)
        {
            _configuration.SetValue(sectionName, keyName, value);
        }

        /// <summary>
        /// Sets config key value as string list
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <param name="value"></param>
        public void SetValue(string sectionName, string keyName, IEnumerable<string> value)
        {
            _configuration.SetValue(sectionName, keyName, value.ToArray());
        }

        /// <summary>
        /// Sets config key value as string dictionary
        /// </summary>
        /// <param name="sectionName"></param>
        /// <param name="keyName"></param>
        /// <param name="dictString"></param>
        public void SetValue(string sectionName, string keyName, IDictionary<string, string> dictString)
        {
            _configuration.SetValue(sectionName, keyName, dictString);
        }
    }
}