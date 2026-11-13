using System.IO;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitLabs.Common {
    /// <summary>
    /// Parses JSON text without rewriting its values.
    /// </summary>
    public static class JsonText {
        /// <summary>
        /// Parses <paramref name="json"/> as one JSON value, keeping date-like strings as strings.
        /// </summary>
        /// <remarks>
        /// <see cref="JToken.Parse(string)"/> turns <c>"2024-05-01"</c> into a date that serializes back
        /// as <c>"2024-05-01T00:00:00"</c>, so any text that must round-trip unchanged is parsed here.
        /// </remarks>
        /// <exception cref="JsonException">The text is not exactly one JSON value.</exception>
        public static JToken Parse(string json) {
            using (var reader = new JsonTextReader(new StringReader(json)) { DateParseHandling = DateParseHandling.None }) {
                var token = JToken.ReadFrom(reader);
                while (reader.Read()) {
                    if (reader.TokenType != JsonToken.Comment)
                        throw new JsonReaderException("Additional text found in JSON string after finishing deserializing value.");
                }
                return token;
            }
        }
    }
}
