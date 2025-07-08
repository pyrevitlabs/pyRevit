using System;
using System.IO;
using System.Text.RegularExpressions;

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
            var sectionPattern = new Regex($"^{extensionName}\\.(extension|lib)$", RegexOptions.IgnoreCase);

            foreach (var section in _ini.GetSections())
            {
                if (sectionPattern.IsMatch(section))
                {
                    return new ExtensionConfig
                    {
                        Name = extensionName,
                        Disabled = bool.TryParse(_ini.IniReadValue(section, "disabled"), out var disabled) && disabled,
                        PrivateRepo = bool.TryParse(_ini.IniReadValue(section, "private_repo"), out var privateRepo) && privateRepo,
                        Username = _ini.IniReadValue(section, "username"),
                        Password = _ini.IniReadValue(section, "password")
                    };
                }
            }

            return null; // Return null if the extension is not found
        }
    }


    public class ExtensionConfig
    {
        public string Name { get; set; }
        public bool Disabled { get; set; }
        public bool PrivateRepo { get; set; }
        public string Username { get; set; }
        public string Password { get; set; }
    }
}
