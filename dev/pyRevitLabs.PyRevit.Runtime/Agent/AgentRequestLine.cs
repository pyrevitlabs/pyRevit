using System.IO;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Parses one request line of the agent pipe.
    /// </summary>
    internal static class AgentRequestLine {
        /// <summary>
        /// Parses <paramref name="line"/> as a single JSON object without converting date-like strings.
        /// </summary>
        /// <exception cref="JsonException">The line is not one JSON object.</exception>
        public static JObject Parse(string line) {
            using (var reader = new JsonTextReader(new StringReader(line)) { DateParseHandling = DateParseHandling.None }) {
                var request = JObject.Load(reader);
                while (reader.Read()) {
                    if (reader.TokenType != JsonToken.Comment)
                        throw new JsonReaderException("Additional text found in JSON string after finishing deserializing object.");
                }
                return request;
            }
        }
    }
}
