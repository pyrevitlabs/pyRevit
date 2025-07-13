using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

namespace pyRevitExtensionParser
{
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

        public IEnumerable<string> GetSections()
        {
            var sb = new StringBuilder(2048);
            GetPrivateProfileString(null, null, null, sb, sb.Capacity, _path);
            return sb.ToString().Split(new[] { '\0' }, StringSplitOptions.RemoveEmptyEntries);
        }
        // Adds a value to the Python-like list in the .ini file
        public void AddValueToPythonList(string section, string key, string value)
        {
            var list = GetPythonList(section, key);
            if (!list.Contains(value))
            {
                list.Add(value);
                SavePythonList(section, key, list);
            }
        }

        // Removes a value from the Python-like list in the .ini file
        public void RemoveValueFromPythonList(string section, string key, string value)
        {
            var list = GetPythonList(section, key);
            if (list.Contains(value))
            {
                list.Remove(value);
                SavePythonList(section, key, list);
            }
        }

        // Reads the Python-like list from the .ini file
        public List<string> GetPythonList(string section, string key)
        {
            string pythonListString = IniReadValue(section, key);
            return PythonListParser.Parse(pythonListString);
        }

        // Saves the Python-like list to the .ini file
        public void SavePythonList(string section, string key, List<string> list)
        {
            string pythonListString = PythonListParser.ToPythonListString(list);
            IniWriteValue(section, key, pythonListString);
        }
    }
    public static class PythonListParser
    {
        // Parses a Python-like list string into a C# List<string>
        public static List<string> Parse(string pythonListString)
        {
            var list = new List<string>();
            var matches = Regex.Matches(pythonListString, @"""([^""]*)""");
            foreach (Match match in matches)
            {
                list.Add(match.Groups[1].Value.Replace(@"\\", @"\"));
            }
            return list;
        }

        // Converts a C# List<string> back to a Python-like list string
        public static string ToPythonListString(List<string> list)
        {
            return $"[{string.Join(", ", list.ConvertAll(item => $"\"{item.Replace(@"\", @"\\")}\""))}]";
        }
    }
}
