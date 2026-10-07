using System.Collections.Generic;
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
                ["elements"] = Elements(changes, response.Value<string>("decision") == "committed"),
                ["other_documents"] = OtherDocumentsOpenBeforeRun(changes).Count(),
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

        /// <remarks>
        /// Elements a run added exist only if it committed, and Revit can give the ids of rolled
        /// back ones to new elements, so a run that didn't commit offers only the elements it
        /// modified, which exist either way.
        /// </remarks>
        private static JArray Elements(JObject changes, bool committed) {
            var added = committed ? changes["added"] as JArray ?? new JArray() : new JArray();
            var described = added
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
            var names = OtherDocumentsOpenBeforeRun(changes)
                .Where(other => other.Value<bool?>("rolled_back") != true
                    && other.Value<bool?>("discarded_on_close") != true)
                .Select(other => other.Value<string>("document"))
                .Where(name => !string.IsNullOrEmpty(name));
            return new JArray(names);
        }

        /// <summary>
        /// The other documents the run changed, except those it created: a run may change a
        /// document it created and still commit.
        /// </summary>
        private static IEnumerable<JObject> OtherDocumentsOpenBeforeRun(JObject changes) {
            return (changes["other_documents"] as JArray ?? new JArray())
                .OfType<JObject>()
                .Where(other => other.Value<bool?>("opened_during_run") != true);
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
