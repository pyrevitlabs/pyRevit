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
