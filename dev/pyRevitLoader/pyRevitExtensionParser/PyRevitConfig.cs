using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.RegularExpressions;
using System.Windows.Documents;

namespace pyRevitExtensionParser
{
    public class PyRevitConfig
    {
        private readonly IniFile _ini;
        public string ConfigPath { get; }

        public string UserExtensions 
        {
            get
            {
                var value = _ini.IniReadValue("core", "userextensions");
                return string.IsNullOrEmpty(value) ? null : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("core", "userextensions", value);
            }
        }

        public string UserLocale
        {
            get
            {
                var value = _ini.IniReadValue("core", "user_locale");
                return string.IsNullOrEmpty(value) ? null : value.Trim();
            }
            set
            {
                _ini.IniWriteValue("core", "user_locale", value);
            }
        }

        public bool NewLoader
        {
            get
            {
                var value = _ini.IniReadValue("core", "new_loader");
                return bool.TryParse(value, out var result) ? result : false;
            }
            set
            {
                _ini.IniWriteValue("core", "new_loader", value.ToString().ToLowerInvariant());
            }
        }
        public bool NewLoaderRoslyn
        {
            get
            {
                var value = _ini.IniReadValue("core", "new_loader_roslyn");
                return bool.TryParse(value, out var result) ? result : false;
            }
            set
            {
                _ini.IniWriteValue("core", "new_loader_roslyn", value.ToString().ToLowerInvariant());
            }
        }
        
        public int StartupLogTimeout
        {
            get
            {
                var value = _ini.IniReadValue("core", "startuplogtimeout");
                return int.TryParse(value, out var result) ? result : 10; // Default to 10 seconds
            }
            set
            {
                _ini.IniWriteValue("core", "startuplogtimeout", value.ToString());
            }
        }
        public List<string> UserExtensionsList
        {
            get
            {
                var value = _ini.IniReadValue("core", "userextensions");
                return string.IsNullOrEmpty(value) ? new List<string>() : PythonListParser.Parse(value);
            }
            set
            {
                _ini.IniWriteValue("core", "userextensions", PythonListParser.ToPythonListString(value));
            }
        }
        public PyRevitConfig(string configPath)
        {
            ConfigPath = configPath;
            _ini = new IniFile(configPath);
        }

        public static PyRevitConfig Load(string customPath = null)
        {
            string configName = "pyRevit_config.ini";
            string defaultPath = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
                "pyRevit",
                configName);

            string finalPath = customPath ?? defaultPath;
            return new PyRevitConfig(finalPath);
        }

        public ExtensionConfig ParseExtensionByName(string extensionName)
        {
            // Try both possible section names directly
            var possibleSections = new[]
            {
                $"{extensionName}.extension",
                $"{extensionName}.lib"
            };

            foreach (var section in possibleSections)
            {
                // Try to read the 'disabled' key - if it returns non-empty, the section exists
                var disabledValue = _ini.IniReadValue(section, "disabled");
                
                if (!string.IsNullOrEmpty(disabledValue) || 
                    !string.IsNullOrEmpty(_ini.IniReadValue(section, "private_repo")) ||
                    !string.IsNullOrEmpty(_ini.IniReadValue(section, "username")))
                {
                    // Section exists, parse all values
                    return new ExtensionConfig
                    {
                        Name = extensionName,
                        Disabled = bool.TryParse(disabledValue, out var disabled) && disabled,
                        PrivateRepo = bool.TryParse(_ini.IniReadValue(section, "private_repo"), out var privateRepo) && privateRepo,
                        Username = _ini.IniReadValue(section, "username"),
                        Password = _ini.IniReadValue(section, "password")
                    };
                }
            }

            return null; // Return null if the extension is not found
        }
    }
}
