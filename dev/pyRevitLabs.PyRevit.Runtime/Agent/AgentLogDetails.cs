using System.Linq;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The summary of a run that the agent log keeps in memory: what it changed, what it
    /// printed, what went wrong, and the script, cut to sizes the panel can show.
    /// </summary>
    /// <remarks>
    /// The full response and script stay in the run folder on disk; <c>run_dir</c> points there.
    /// </remarks>
    internal static class AgentLogDetails {
        public const int MaxScriptChars = 20000;
        public const int MaxOutputChars = 4000;
        public const int MaxTracebackChars = 4000;
        public const int MaxElements = 20;

        public static JObject FromRun(JObject response, string script) {
            var changes = response["changes"] as JObject ?? new JObject();
            var error = response["error"] as JObject;
            var engine = response["engine"] as JObject;
            return new JObject {
                ["mode"] = response["mode"],
                ["status"] = response["status"],
                ["decision"] = response["decision"],
                ["approval"] = response["approval"],
                ["elapsed_ms"] = response["elapsed_ms"],
                ["document"] = response["document"],
                ["run_id"] = response["run_id"],
                ["run_dir"] = response["run_dir"],
                ["added"] = changes.Value<int?>("added_count") ?? 0,
                ["modified"] = changes.Value<int?>("modified_count") ?? 0,
                ["deleted"] = changes.Value<int?>("deleted_count") ?? 0,
                ["by_category"] = changes["by_category"] as JObject ?? new JObject(),
                ["elements"] = Elements(changes),
                ["other_documents"] = (changes["other_documents"] as JArray)?.Count ?? 0,
                ["unreverted_documents"] = UnrevertedDocuments(changes),
                ["warnings"] = response["warnings"] as JArray ?? new JArray(),
                ["output"] = Text(Cut(response.Value<string>("output"), MaxOutputChars)),
                ["error"] = error == null ? null : new JObject {
                    ["type"] = error["type"],
                    ["message"] = error["message"],
                    ["traceback"] = Text(Cut(error.Value<string>("traceback"), MaxTracebackChars)),
                },
                ["engine"] = engine == null ? JValue.CreateNull() : Text((engine.Value<string>("implementation") + " " + engine.Value<string>("python")).Trim()),
                ["script"] = Text(Cut(script, MaxScriptChars)),
            };
        }

        private static JArray Elements(JObject changes) {
            var described = (changes["added"] as JArray ?? new JArray())
                .Concat(changes["modified"] as JArray ?? new JArray())
                .OfType<JObject>()
                .Where(element => element["id"] != null)
                .Take(MaxElements);
            return new JArray(described);
        }

        /// <summary>
        /// Documents that were open before the run and still hold its changes, because the host
        /// could neither roll them back nor close them unsaved. The user must close them without
        /// saving.
        /// </summary>
        private static JArray UnrevertedDocuments(JObject changes) {
            var names = (changes["other_documents"] as JArray ?? new JArray())
                .OfType<JObject>()
                .Where(other => other.Value<bool?>("opened_during_run") != true
                    && other.Value<bool?>("rolled_back") != true
                    && other.Value<bool?>("discarded_on_close") != true)
                .Select(other => other.Value<string>("document"))
                .Where(name => !string.IsNullOrEmpty(name));
            return new JArray(names);
        }

        private static JToken Text(string text) {
            return text == null ? JValue.CreateNull() : new JValue(text);
        }

        private static string Cut(string text, int max) {
            if (text == null || text.Length <= max)
                return text;
            return text.Substring(0, max) + "\n…";
        }
    }
}
