using System;
using System.Collections.Generic;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;

namespace pyRevitAssemblyBuilder.Config
{
    public class PyRevitConfig
    {
        private readonly IniFile _ini;
        public string ConfigPath { get; }

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
    }

    internal class IniFile
    {
        private readonly string _path;

        public IniFile(string iniPath)
                {
            _path = iniPath;
                }

        [DllImport("kernel32")]
        private static extern long WritePrivateProfileString(string section, string key, string val, string filePath);

        [DllImport("kernel32")]
        private static extern int GetPrivateProfileString(string section, string key, string def, StringBuilder retVal, int size, string filePath);

        public string IniReadValue(string section, string key)
                        {
            var sb = new StringBuilder(512);
            GetPrivateProfileString(section, key, "", sb, sb.Capacity, _path);
            return sb.ToString();
            }

        public void IniWriteValue(string section, string key, string value)
        {
            WritePrivateProfileString(section, key, value, _path);
        }
    }
}
