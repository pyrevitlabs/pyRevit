using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Text.RegularExpressions;
using System.Globalization;

using Newtonsoft.Json;

namespace pyRevitLabs.Common.Extensions {
    public static class ConstHelper {
        /// <summary>
        /// Remaps international characters to ascii compatible ones
        /// based of: https://meta.stackexchange.com/questions/7435/non-us-ascii-characters-dropped-from-full-profile-url/7696#7696
        /// </summary>
        /// <param name="c">Charcter to remap</param>
        /// <returns>Remapped character</returns>
        public static string RemapInternationalCharToAscii(char c) {
            string s = c.ToString().ToLowerInvariant();
            if ("àåáâäãåą".Contains(s)) {
                return "a";
            }
            else if ("èéêëę".Contains(s)) {
                return "e";
            }
            else if ("ìíîïı".Contains(s)) {
                return "i";
            }
            else if ("òóôõöøőð".Contains(s)) {
                return "o";
            }
            else if ("ùúûüŭů".Contains(s)) {
                return "u";
            }
            else if ("çćčĉ".Contains(s)) {
                return "c";
            }
            else if ("żźž".Contains(s)) {
                return "z";
            }
            else if ("śşšŝ".Contains(s)) {
                return "s";
            }
            else if ("ñń".Contains(s)) {
                return "n";
            }
            else if ("ýÿ".Contains(s)) {
                return "y";
            }
            else if ("ğĝ".Contains(s)) {
                return "g";
            }
            else if (c == 'ř') {
                return "r";
            }
            else if (c == 'ł') {
                return "l";
            }
            else if (c == 'đ') {
                return "d";
            }
            else if (c == 'ß') {
                return "ss";
            }
            else if (c == 'þ') {
                return "th";
            }
            else if (c == 'ĥ') {
                return "h";
            }
            else if (c == 'ĵ') {
                return "j";
            }
            else {
                return "";
            }
        }
    }

    public static class FileSizeExtension {
        public static string CleanupSize(this float bytes) {
            var sizes = new List<String> { "Bytes", "KB", "MB", "GB", "TB" };

            if (bytes == 0)
                return "0 Byte";

            var i = (int)Math.Floor(Math.Log(bytes) / Math.Log(1024));
            if (i >= 0 && i <= sizes.Count)
                return Math.Round(bytes / Math.Pow(1024, i), 2) + " " + sizes[i];
            else
                return bytes + " Bytes";
        }

        public static string CleanupSize(this long bytes) {
            return CleanupSize((float)bytes);
        }

        public static string CleanupSize(this int bytes) {
            return CleanupSize((float)bytes);
        }
    }

    public static class InputExtensions {
        public static int LimitToRange(this int value, int inclusiveMinimum, int inclusiveMaximum) {
            if (value < inclusiveMinimum) { return inclusiveMinimum; }
            if (value > inclusiveMaximum) { return inclusiveMaximum; }
            return value;
        }
    }

    public static class StringExtensions {
        private static Regex DriveLetterFinder = new Regex(@"^(?<drive>[A-Za-z]):");
        private static Regex GuidFinder = new Regex(@".*(?<guid>[0-9A-Fa-f]{8}[-]" +
                                                        "[0-9A-Fa-f]{4}[-]" +
                                                        "[0-9A-Fa-f]{4}[-]" +
                                                        "[0-9A-Fa-f]{4}[-]" + 
                                                        "[0-9A-Fa-f]{12}).*");

        public static string GetDisplayPath(this string sourceString) {
            var separator = Path.AltDirectorySeparatorChar.ToString();
            return sourceString.Replace("||", separator)
                               .Replace("|\\", separator)
                               .Replace("|", separator)
                               .Replace(Path.DirectorySeparatorChar.ToString(), separator);
        }

        public static string TripleDot(this string sourceString, uint maxLength) {
            if (sourceString.Length > maxLength && maxLength > 3)
                return sourceString.Substring(0, (int)maxLength - 3) + "...";
            else
                return sourceString;
        }

        public static string NullToNA(this string sourceString) {
            if (sourceString == "" || sourceString == null)
                return "N/A";
            else
                return sourceString;
        }

        public static string NormalizeAsPath(this string path) {
            var normedPath =
                Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
            var match = DriveLetterFinder.Match(normedPath);
            if (match.Success) {
                var driveLetter = match.Groups["drive"].Value + ":";
                normedPath = normedPath.Replace(driveLetter, driveLetter.ToUpper());
            }

            return normedPath;
        }

        public static Version ConvertToVersion(this string version) {
            if (!version.Contains("."))
                version = version + ".0";
            return new Version(version);
        }

        public static List<string> ConvertFromCommaSeparatedString(this string commaSeparatedValue) {
            return new List<string>(commaSeparatedValue.Split(','));
        }

        public static List<string> ConvertFromTomlListString(this string tomlListString) {
            try {
                return JsonConvert.DeserializeObject<List<string>>(tomlListString);
            }
            catch {
                // try parsing using legacy method
                var cleanedValue = tomlListString.Replace("[", "").Replace("]", "");
                var quotedValues = new List<string>(cleanedValue.Split(','));
                var results = new List<string>();
                var valueFinder = new Regex(@"'(?<value>.+)'");
                foreach (var value in quotedValues) {
                    var m = valueFinder.Match(value);
                    if (m.Success)
                        results.Add(m.Groups["value"].Value);
                }
                return results;
            }
        }

        public static Dictionary<string, string> ConvertFromTomlDictString(this string tomlDictString) {
            try {
                return JsonConvert.DeserializeObject<Dictionary<string, string>>(tomlDictString);
            }
            catch {
                // try parsing using legacy method
                var cleanedValue = tomlDictString.Replace("{", "").Replace("}", "");
                var quotedKeyValuePairs = new List<string>(cleanedValue.Split(','));
                var results = new Dictionary<string, string>();
                var valueFinder = new Regex(@"'(?<key>.+)'\s*:\s*'(?<value>.+)'");
                foreach (var keyValueString in quotedKeyValuePairs) {
                    var m = valueFinder.Match(keyValueString);
                    if (m.Success)
                        results[m.Groups["key"].Value] = m.Groups["value"].Value;
                }
                return results;
            }
        }

        public static Guid ExtractGuid(this string inputString) {
            var zeroGuid = new Guid();
            var m = GuidFinder.Match(inputString);
            if (m.Success) {
                try {
                    var guid = new Guid(m.Groups["guid"].Value);
                    if (guid != zeroGuid)
                        return guid;
                } catch {
                    return zeroGuid;
                }
            }
            return zeroGuid;
        }

        public static bool IsValidHttpUrl(this string sourceString) {
            Uri uriResult;
            return Uri.TryCreate(sourceString, UriKind.Absolute, out uriResult)
                && (uriResult.Scheme == Uri.UriSchemeHttp || uriResult.Scheme == Uri.UriSchemeHttps);
        }

        /// <summary>
        /// Creates a URL And SEO friendly slug
        /// </summary>
        /// <param name="text">Text to slugify</param>
        /// <param name="maxLength">Max length of slug</param>
        /// <returns>URL and SEO friendly string</returns>
        public static string UrlFriendly(this string text, int maxLength = 0) {
            // Return empty value if text is null
            if (text == null) return "";
            var normalizedString = text
                // Make lowercase
                .ToLowerInvariant()
                // Normalize the text
                .Normalize(NormalizationForm.FormD);
            var stringBuilder = new StringBuilder();
            var stringLength = normalizedString.Length;
            var prevdash = false;
            var trueLength = 0;
            char c;
            for (int i = 0; i < stringLength; i++) {
                c = normalizedString[i];
                switch (CharUnicodeInfo.GetUnicodeCategory(c)) {
                    // Check if the character is a letter or a digit if the character is a
                    // international character remap it to an ascii valid character
                    case UnicodeCategory.LowercaseLetter:
                    case UnicodeCategory.UppercaseLetter:
                    case UnicodeCategory.DecimalDigitNumber:
                        if (c < 128)
                            stringBuilder.Append(c);
                        else
                            stringBuilder.Append(ConstHelper.RemapInternationalCharToAscii(c));
                        prevdash = false;
                        trueLength = stringBuilder.Length;
                        break;
                    // Check if the character is to be replaced by a hyphen but only if the last character wasn't
                    case UnicodeCategory.SpaceSeparator:
                    case UnicodeCategory.ConnectorPunctuation:
                    case UnicodeCategory.DashPunctuation:
                    case UnicodeCategory.OtherPunctuation:
                    case UnicodeCategory.MathSymbol:
                        if (!prevdash) {
                            stringBuilder.Append('-');
                            prevdash = true;
                            trueLength = stringBuilder.Length;
                        }
                        break;
                }
                // If we are at max length, stop parsing
                if (maxLength > 0 && trueLength >= maxLength)
                    break;
            }
            // Trim excess hyphens
            var result = stringBuilder.ToString().Trim('-');
            // Remove any excess character to meet maxlength criteria
            return maxLength <= 0 || result.Length <= maxLength ? result : result.Substring(0, maxLength);
        }
    }

    public static class DateTimeExtensions {
        public static string NeatTime(this DateTime sourceDate) {
            return String.Format("{0:dd/MM/yyyy HH:mm:ss}", sourceDate);
        }
    }

    public static class StringEnumerableExtensions {
        public static string ConvertToCommaSeparatedString(this IEnumerable<string> sourceValues) {
            return string.Join(",", sourceValues);
        }

        public static string ConvertToTomlListString(this IEnumerable<string> sourceValues) {
            //var quotedValues = new List<string>();
            //foreach (var value in sourceValues)
            //    quotedValues.Add(string.Format("'{0}'", value));
            //return "[" + string.Join(",", quotedValues) + "]";
            return JsonConvert.SerializeObject(sourceValues);
        }
    }

    public static class StringDictionaryExtensions {
        public static string ConvertToTomlDictString(this IDictionary<string, string> sourceValues) {
            //var quotedValues = new List<string>();
            //foreach (var keyValuePair in sourceValues) {
            //    string quotedKey = string.Format("'{0}'", keyValuePair.Key);
            //    string quotedValue = string.Format("'{0}'", keyValuePair.Value);
            //    quotedValues.Add(string.Format("{0}:{1}", quotedKey, quotedValue));
            //}
            //return "{" + string.Join(",", quotedValues) + "}";
            return JsonConvert.SerializeObject(sourceValues);
        }
    }
}
