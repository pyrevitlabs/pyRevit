using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

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
        [DllImport("kernel32", CharSet = CharSet.Unicode, SetLastError = true)]
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
        [DllImport("kernel32", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern int GetPrivateProfileString(string section, string key, string def, StringBuilder retVal, int size, string filePath);

        /// <summary>
        /// Reads a value from the INI file for the specified section and key.
        /// </summary>
        /// <param name="section">The section name to read from.</param>
        /// <param name="key">The key name within the section.</param>
        /// <returns>The value associated with the key, or an empty string if not found.</returns>
        public string IniReadValue(string section, string key)
        {
            if (TryReadValueManaged(section, key, out var managedValue))
            {
                return managedValue ?? string.Empty;
            }

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
        /// Removes a key from the INI file (Win32 <c>WritePrivateProfileString</c> with a null value).
        /// </summary>
        public void IniRemoveKey(string section, string key)
        {
            WritePrivateProfileString(section, key, null, _path);
        }

        /// <summary>
        /// Retrieves all section names from the INI file.
        /// </summary>
        /// <returns>An enumerable collection of section names.</returns>
        public IEnumerable<string> GetSections()
        {
            if (TryReadSectionsManaged(out var sections))
            {
                return sections;
            }

            var sb = new StringBuilder(2048);
            GetPrivateProfileString(null, null, null, sb, sb.Capacity, _path);
            return sb.ToString().Split(new[] { '\0' }, StringSplitOptions.RemoveEmptyEntries);
        }

        private bool TryReadValueManaged(string section, string key, out string value)
        {
            value = string.Empty;
            if (string.IsNullOrEmpty(section) || string.IsNullOrEmpty(key))
                return false;

            if (!CanReadManaged())
                return false;

            try
            {
                foreach (var entry in EnumerateIniEntries())
                {
                    if (!entry.IsKeyValue)
                        continue;
                    if (!string.Equals(entry.Section, section, StringComparison.OrdinalIgnoreCase))
                        continue;
                    if (!string.Equals(entry.Key, key, StringComparison.OrdinalIgnoreCase))
                        continue;

                    value = entry.Value ?? string.Empty;
                    return true;
                }

                return false;
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }
            catch (ArgumentException)
            {
                return false;
            }
        }

        private bool TryReadSectionsManaged(out IEnumerable<string> sections)
        {
            sections = Array.Empty<string>();
            if (!CanReadManaged())
                return false;

            try
            {
                var sectionNames = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
                foreach (var entry in EnumerateIniEntries()
                    .Where(e => e.IsSection && !string.IsNullOrEmpty(e.Section)))
                {
                    sectionNames.Add(entry.Section);
                }

                sections = sectionNames;
                return true;
            }
            catch (IOException)
            {
                return false;
            }
            catch (UnauthorizedAccessException)
            {
                return false;
            }
            catch (ArgumentException)
            {
                return false;
            }
        }

        private bool CanReadManaged()
        {
            return !string.IsNullOrEmpty(_path) && File.Exists(_path);
        }

        private IEnumerable<IniEntry> EnumerateIniEntries()
        {
            string currentSection = null;
            foreach (var line in File.ReadLines(_path))
            {
                var trimmed = line.Trim();
                if (trimmed.Length == 0)
                    continue;
                if (trimmed.StartsWith(";") || trimmed.StartsWith("#"))
                    continue;

                if (trimmed.StartsWith("[") && trimmed.EndsWith("]"))
                {
                    currentSection = trimmed.Substring(1, trimmed.Length - 2).Trim();
                    yield return IniEntry.SectionEntry(currentSection);
                    continue;
                }

                var idx = trimmed.IndexOf('=');
                if (idx < 0)
                    continue;

                var keyPart = trimmed.Substring(0, idx).Trim();
                var valuePart = trimmed.Substring(idx + 1).Trim();
                yield return IniEntry.KeyValue(currentSection, keyPart, valuePart);
            }
        }

        private readonly struct IniEntry
        {
            public string Section { get; }
            public string Key { get; }
            public string Value { get; }
            public bool IsSection { get; }
            public bool IsKeyValue { get; }

            private IniEntry(string section, string key, string value, bool isSection, bool isKeyValue)
            {
                Section = section;
                Key = key;
                Value = value;
                IsSection = isSection;
                IsKeyValue = isKeyValue;
            }

            public static IniEntry SectionEntry(string section)
            {
                return new IniEntry(section, null, null, true, false);
            }

            public static IniEntry KeyValue(string section, string key, string value)
            {
                return new IniEntry(section, key, value, false, true);
            }
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
    /// Provides utilities for parsing and formatting list strings.
    /// Handles conversion between list format (["item1", "item2"]) and C# List&lt;string&gt;.
    /// </summary>
    public static class PythonListParser
    {
        /// <summary>
        /// Parses a list string into a C# List&lt;string&gt;.
        /// Accepts JSON arrays and preserves Unicode values.
        /// </summary>
        /// <param name="pythonListString">
        /// The list string to parse. Expected format: ["value1", "value2", "value3"]
        /// Can be null, empty, or a single non-list value.
        /// </param>
        /// <returns>
        /// A List&lt;string&gt; containing the parsed values. Returns an empty list if input is null or empty.
        ///
        /// </returns>
        /// <example>
        /// Input: ["C:\\Users\\Documents", "C:\\Program Files"]
        /// Output: List with "C:\Users\Documents" and "C:\Program Files"
        /// </example>
        public static List<string> Parse(string pythonListString)
        {
            if (string.IsNullOrEmpty(pythonListString))
                return new List<string>();

            var trimmed = pythonListString.Trim();
            if (!trimmed.StartsWith("["))
                return new List<string> { trimmed };

            var list = TryParseJsonList(trimmed);
            if (list != null)
                return list;

            var normalized = NormalizeSingleQuotedList(trimmed);
            if (!string.Equals(normalized, trimmed, StringComparison.Ordinal))
            {
                list = TryParseJsonList(normalized);
                if (list != null)
                    return list;
            }

            return new List<string>();
        }

        /// <summary>
        /// Converts a C# List&lt;string&gt; to a list string.
        /// </summary>
        /// <param name="list">
        /// The list to convert. Can be null or empty.
        /// </param>
        /// <returns>
        /// A list string in the format: ["value1", "value2", "value3"]
        /// Returns "[]" for null or empty lists.
        ///
        /// </returns>
        /// <example>
        /// Input: List with "C:\Users\Documents" and "C:\Program Files"
        /// Output: ["C:\\Users\\Documents", "C:\\Program Files"]
        /// </example>
        public static string ToPythonListString(List<string> list)
        {
            if (list == null || list.Count == 0)
                return "[]";

            var array = new JArray();
            foreach (var item in list)
                array.Add(item ?? string.Empty);

            return array.ToString(Formatting.None);
        }

        private static List<string> TryParseJsonList(string jsonListString)
        {
            try
            {
                var array = JArray.Parse(jsonListString);
                return array
                    .Where(token => token != null)
                    .Select(token => token.Type == JTokenType.String ? token.Value<string>() : token.ToString())
                    .ToList();
            }
            catch
            {
                return null;
            }
        }

        private static string NormalizeSingleQuotedList(string value)
        {
            if (string.IsNullOrEmpty(value))
                return value;
            if (!value.StartsWith("[") || !value.EndsWith("]"))
                return value;
            if (value.IndexOf('"') >= 0)
                return value;

            // Replace only single quotes that act as string delimiters, not embedded apostrophes.
            // Delimiters are: after [ or , (opening) and before ] or , (closing).
            var sb = new StringBuilder(value.Length);
            bool inString = false;
            for (int i = 0; i < value.Length; i++)
            {
                char c = value[i];
                if (c == '\'' && !inString)
                {
                    sb.Append('"');
                    inString = true;
                }
                else if (c == '\'' && inString)
                {
                    // Check if this quote is a closing delimiter:
                    // next non-whitespace should be , or ]
                    bool isClosing = false;
                    for (int j = i + 1; j < value.Length; j++)
                    {
                        if (char.IsWhiteSpace(value[j]))
                            continue;
                        if (value[j] == ',' || value[j] == ']')
                            isClosing = true;
                        break;
                    }

                    if (isClosing)
                    {
                        sb.Append('"');
                        inString = false;
                    }
                    else
                    {
                        // Embedded apostrophe — escape it for JSON
                        sb.Append('\'');
                    }
                }
                else
                {
                    sb.Append(c);
                }
            }

            return sb.ToString();
        }
    }
}
