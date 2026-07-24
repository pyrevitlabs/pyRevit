using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitExtensionParser
{
    /// <summary>
    /// Provides utilities for parsing and formatting list strings.
    /// Handles conversion between list format (["item1", "item2"]) and C# List&lt;string&gt;.
    /// </summary>
    public static class PythonListParser
    {
        /// <summary>
        /// Parses a list string into a C# List&lt;string&gt;.
        /// Accepts JSON arrays and legacy Python single-quoted literals, and
        /// preserves Unicode values.
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

            list = TryParseSingleQuotedList(trimmed);
            if (list != null)
                return list;

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

        /// <summary>
        /// Reads a legacy Python-style single-quoted list directly, without routing
        /// it through a JSON parser. Backslashes are taken literally so that
        /// unescaped Windows paths survive; only the two escapes Python itself can
        /// emit inside a single-quoted literal are decoded. Returns null when the
        /// value is not a single-quoted list, so the caller can fall through.
        /// </summary>
        private static List<string> TryParseSingleQuotedList(string value)
        {
            if (!value.StartsWith("[") || !value.EndsWith("]"))
                return null;
            // A double quote means this was meant to be JSON; the JSON reader
            // already had its turn and rejected it.
            if (value.IndexOf('"') >= 0)
                return null;

            var items = new List<string>();
            var item = new StringBuilder();
            int end = value.Length - 1;
            bool inString = false;

            for (int i = 1; i < end; i++)
            {
                char c = value[i];

                if (!inString)
                {
                    if (c == '\'')
                    {
                        inString = true;
                        item.Length = 0;
                    }
                    else if (c != ',' && !char.IsWhiteSpace(c))
                    {
                        // Unquoted content between items: not a list of strings.
                        return null;
                    }

                    continue;
                }

                if (c == '\\' && i + 1 < end && (value[i + 1] == '\\' || value[i + 1] == '\''))
                {
                    item.Append(value[i + 1]);
                    i++;
                }
                else if (c == '\'' && IsClosingDelimiter(value, i, end))
                {
                    inString = false;
                    items.Add(item.ToString());
                }
                else
                {
                    item.Append(c);
                }
            }

            return inString ? null : items;
        }

        // An apostrophe inside a hand-edited value is only a delimiter when the
        // next meaningful character ends the item.
        private static bool IsClosingDelimiter(string value, int index, int end)
        {
            for (int i = index + 1; i < end; i++)
            {
                if (char.IsWhiteSpace(value[i]))
                    continue;

                return value[i] == ',';
            }

            return true;
        }
    }
}
