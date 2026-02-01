using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Text;
using System.Text.RegularExpressions;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Provides functionality for reading and writing INI configuration files using Windows API.
    /// Supports both standard key-value pairs and Python-style list values.
    /// </summary>
    internal class IniFile
    {
        /// <summary>
        /// The full path to the INI file.
        /// </summary>
        private readonly string _path;

        /// <summary>
        /// Initializes a new instance of the <see cref="IniFile"/> class.
        /// </summary>
        /// <param name="iniPath">The full path to the INI file.</param>
        public IniFile(string iniPath)
        {
            _path = iniPath;
        }

        /// <summary>
        /// Writes a value to an INI file using the Windows API.
        /// </summary>
        /// <param name="section">The section name in the INI file.</param>
        /// <param name="key">The key name within the section.</param>
        /// <param name="val">The value to write.</param>
        /// <param name="filePath">The path to the INI file.</param>
        /// <returns>Non-zero if successful; otherwise, zero.</returns>
        [DllImport("kernel32")]
        private static extern long WritePrivateProfileString(string section, string key, string val, string filePath);

        /// <summary>
        /// Retrieves a value from an INI file using the Windows API.
        /// </summary>
        /// <param name="section">The section name in the INI file. Pass null to retrieve all section names.</param>
        /// <param name="key">The key name within the section. Pass null to retrieve all keys in a section.</param>
        /// <param name="def">The default value to return if the key is not found.</param>
        /// <param name="retVal">A StringBuilder to receive the retrieved value.</param>
        /// <param name="size">The size of the buffer (StringBuilder capacity).</param>
        /// <param name="filePath">The path to the INI file.</param>
        /// <returns>The number of characters copied to the buffer, excluding the null terminator.</returns>
        [DllImport("kernel32")]
        private static extern int GetPrivateProfileString(string section, string key, string def, StringBuilder retVal, int size, string filePath);

        /// <summary>
        /// Reads a value from the INI file for the specified section and key.
        /// </summary>
        /// <param name="section">The section name to read from.</param>
        /// <param name="key">The key name within the section.</param>
        /// <returns>The value associated with the key, or an empty string if not found.</returns>
        public string IniReadValue(string section, string key)
        {
            // Increased capacity for larger ini values (like Python lists)
            var sb = new StringBuilder(2048);
            GetPrivateProfileString(section, key, "", sb, sb.Capacity, _path);
            return sb.ToString();
        }

        /// <summary>
        /// Writes a value to the INI file for the specified section and key.
        /// </summary>
        /// <param name="section">The section name to write to.</param>
        /// <param name="key">The key name within the section.</param>
        /// <param name="value">The value to write.</param>
        public void IniWriteValue(string section, string key, string value)
        {
            WritePrivateProfileString(section, key, value, _path);
        }

        /// <summary>
        /// Retrieves all section names from the INI file.
        /// </summary>
        /// <returns>An enumerable collection of section names.</returns>
        public IEnumerable<string> GetSections()
        {
            var sb = new StringBuilder(2048);
            GetPrivateProfileString(null, null, null, sb, sb.Capacity, _path);
            return sb.ToString().Split(new[] { '\0' }, StringSplitOptions.RemoveEmptyEntries);
        }
        /// <summary>
        /// Adds a value to a Python-style list stored in the INI file.
        /// The list is stored as a string in the format: ["value1", "value2", "value3"]
        /// </summary>
        /// <param name="section">The section name containing the list.</param>
        /// <param name="key">The key name for the list.</param>
        /// <param name="value">The value to add to the list. Duplicate values are not added.</param>
        public void AddValueToPythonList(string section, string key, string value)
        {
            var list = GetPythonList(section, key);
            if (!list.Contains(value))
            {
                list.Add(value);
                SavePythonList(section, key, list);
            }
        }

        /// <summary>
        /// Removes a value from a Python-style list stored in the INI file.
        /// </summary>
        /// <param name="section">The section name containing the list.</param>
        /// <param name="key">The key name for the list.</param>
        /// <param name="value">The value to remove from the list.</param>
        public void RemoveValueFromPythonList(string section, string key, string value)
        {
            var list = GetPythonList(section, key);
            if (list.Contains(value))
            {
                list.Remove(value);
                SavePythonList(section, key, list);
            }
        }

        /// <summary>
        /// Reads a Python-style list from the INI file and parses it into a C# List.
        /// Expected format: ["value1", "value2", "value3"]
        /// </summary>
        /// <param name="section">The section name containing the list.</param>
        /// <param name="key">The key name for the list.</param>
        /// <returns>A List&lt;string&gt; containing the parsed values.</returns>
        public List<string> GetPythonList(string section, string key)
        {
            string pythonListString = IniReadValue(section, key);
            return PythonListParser.Parse(pythonListString);
        }

        /// <summary>
        /// Converts a C# List to a Python-style list string and saves it to the INI file.
        /// The list is stored in the format: ["value1", "value2", "value3"]
        /// </summary>
        /// <param name="section">The section name to save the list to.</param>
        /// <param name="key">The key name for the list.</param>
        /// <param name="list">The list to save.</param>
        public void SavePythonList(string section, string key, List<string> list)
        {
            string pythonListString = PythonListParser.ToPythonListString(list);
            IniWriteValue(section, key, pythonListString);
        }
    }
    /// <summary>
    /// Provides utilities for parsing and formatting Python-style list strings.
    /// Handles conversion between Python list format (["item1", "item2"]) and C# List&lt;string&gt;.
    /// Optimized for performance with compiled regex and minimal string allocations.
    /// </summary>
    public static class PythonListParser
    {
        /// <summary>
        /// Pre-compiled regex pattern for extracting quoted values from Python-style lists.
        /// Pattern matches content between double quotes: "([^"]*)"
        /// Compiled for better performance when used repeatedly.
        /// </summary>
        private static readonly Regex QuotedValueRegex = new Regex(@"""([^""]*)""", RegexOptions.Compiled);

        /// <summary>
        /// Parses a Python-style list string into a C# List&lt;string&gt;.
        /// Handles escaped backslashes in paths (e.g., "C:\\path\\to\\file" becomes "C:\path\to\file").
        /// </summary>
        /// <param name="pythonListString">
        /// The Python-style list string to parse. Expected format: ["value1", "value2", "value3"]
        /// Can be null, empty, or contain escaped backslashes.
        /// </param>
        /// <returns>
        /// A List&lt;string&gt; containing the parsed values. Returns an empty list if input is null or empty.
        /// Backslashes are unescaped (double backslash \\ becomes single backslash \).
        /// </returns>
        /// <example>
        /// Input: ["C:\\Users\\Documents", "C:\\Program Files"]
        /// Output: List with "C:\Users\Documents" and "C:\Program Files"
        /// </example>
        public static List<string> Parse(string pythonListString)
        {
            if (string.IsNullOrEmpty(pythonListString))
                return new List<string>();

            var list = new List<string>();
            var matches = QuotedValueRegex.Matches(pythonListString);
            
            // Pre-allocate capacity if we know the count to avoid resizing
            if (matches.Count > 0)
            {
                list.Capacity = matches.Count;
            }

            foreach (Match match in matches)
            {
                // Only replace if backslashes are present to avoid unnecessary allocations
                string value = match.Groups[1].Value;
                if (value.Contains(@"\\"))
                {
                    // Unescape: convert \\ to \
                    list.Add(value.Replace(@"\\", @"\"));
                }
                else
                {
                    list.Add(value);
                }
            }
            return list;
        }

        /// <summary>
        /// Converts a C# List&lt;string&gt; to a Python-style list string.
        /// Escapes backslashes in paths (e.g., "C:\path\to\file" becomes "C:\\path\\to\\file").
        /// </summary>
        /// <param name="list">
        /// The list to convert. Can be null or empty.
        /// </param>
        /// <returns>
        /// A Python-style list string in the format: ["value1", "value2", "value3"]
        /// Returns "[]" for null or empty lists.
        /// Backslashes are escaped (single backslash \ becomes double backslash \\).
        /// </returns>
        /// <example>
        /// Input: List with "C:\Users\Documents" and "C:\Program Files"
        /// Output: ["C:\\Users\\Documents", "C:\\Program Files"]
        /// </example>
        public static string ToPythonListString(List<string> list)
        {
            if (list == null || list.Count == 0)
                return "[]";

            // Estimate capacity: brackets + items + quotes + commas + spaces
            // Average of 20 characters per item is a reasonable estimate for file paths
            int estimatedCapacity = 2 + (list.Count * 20);
            var sb = new StringBuilder(estimatedCapacity);
            sb.Append('[');

            for (int i = 0; i < list.Count; i++)
            {
                // Add comma separator after first item
                if (i > 0)
                    sb.Append(", ");

                sb.Append('"');
                string item = list[i];
                // Only replace if backslashes are present to avoid unnecessary allocations
                if (item.Contains(@"\"))
                {
                    // Escape: convert \ to \\
                    sb.Append(item.Replace(@"\", @"\\"));
                }
                else
                {
                    sb.Append(item);
                }
                sb.Append('"');
            }

            sb.Append(']');
            return sb.ToString();
        }
    }
}
