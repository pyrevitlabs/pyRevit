using System.Linq;
using System.Text.RegularExpressions;

using pyRevitLabs.Json.Linq;

namespace pyRevitCLI {
    /// <summary>
    /// Shapes run responses for agents: what matters first, empty bookkeeping dropped, and
    /// a concrete next step attached to Revit API errors.
    /// </summary>
    /// <remarks>
    /// Clients often truncate long tool results, so <c>status</c> and <c>error</c> must lead.
    /// The full record stays available through <c>get_run</c>, so nothing dropped here is lost.
    /// </remarks>
    internal static class PyRevitMcpRunResults {
        private static readonly Regex MissingAttribute =
            new Regex(@"'(?<owner>[\w.]+)' object has no attribute '(?<member>\w+)'", RegexOptions.Compiled);
        private static readonly Regex WrongArgumentCount =
            new Regex(@"(?<member>\w+)\(\) takes (exactly|at least|at most|no) ", RegexOptions.Compiled);
        private static readonly Regex WrongArgumentType =
            new Regex(@"expected (?<expected>[\w\[\]., ]+?), got (?<got>[\w\[\]]+)", RegexOptions.Compiled);
        private static readonly Regex NetCollectionType =
            new Regex(@"^(I?Collection|IList|IEnumerable|ISet|List)\b", RegexOptions.Compiled);
        private static readonly Regex StaticCall =
            new Regex(@"\b(?!(?:DB|UI)\.)(?<type>[A-Z]\w*)\.(?<member>[A-Z]\w*)\s*\(", RegexOptions.Compiled);
        private static readonly Regex ConstructedCall =
            new Regex(@"\b(?!(?:DB|UI)\.)(?<type>[A-Z]\w*)\([^()]*\)\.(?<member>[A-Z]\w*)\s*\(", RegexOptions.Compiled);

        public static JObject Compact(JObject run) {
            var compact = new JObject {
                ["status"] = run["status"],
                ["run_id"] = run["run_id"],
            };

            if (run["error"] is JObject error) {
                var shaped = new JObject {
                    ["type"] = error["type"],
                    ["message"] = error["message"],
                };
                if (error["traceback"]?.Type == JTokenType.String)
                    shaped["traceback"] = error["traceback"];
                var hint = HintFor(error);
                if (hint != null)
                    shaped["hint"] = hint;
                compact["error"] = shaped;
            }

            if (run.Value<string>("mode") != "query")
                compact["decision"] = run["decision"];

            if (run["result"] != null && run["result"].Type != JTokenType.Null)
                compact["result"] = run["result"];
            if (run.Value<bool?>("result_truncated") == true) {
                compact["result_truncated"] = true;
                compact["result_note"] = "The result was too large to return inline; page it with get_run(run_id, offset, length).";
            }

            var output = run.Value<string>("output");
            if (!string.IsNullOrEmpty(output)) {
                compact["output"] = output;
                if (run.Value<bool?>("output_truncated") == true)
                    compact["output_truncated"] = true;
            }

            if (run["changes"] is JObject changes && HasChanges(changes))
                compact["changes"] = changes;
            CopyIfNotEmpty(run, compact, "failures");
            CopyIfNotEmpty(run, compact, "dialogs");
            CopyIfNotEmpty(run, compact, "blocked");

            if (run["engine"] is JObject engine)
                compact["engine"] = engine["implementation"] + " " + engine["python"];
            compact["elapsed_ms"] = run["elapsed_ms"];
            return compact;
        }

        /// <summary>
        /// Turns a failed run's error into a concrete next step: the <c>lookup_revit_api</c>
        /// call to make, or the idiom that fixes a common Revit API mistake.
        /// </summary>
        /// <remarks>
        /// Reads the error message and the failing line of the agent's script. Returns null
        /// when nothing specific applies, so hints stay trustworthy instead of generic.
        /// </remarks>
        internal static string HintFor(JObject error) {
            var type = error.Value<string>("type");
            var message = error.Value<string>("message") ?? string.Empty;
            var failingLine = LastSourceLine(error.Value<string>("traceback"));

            if (message.IndexOf("outside of transaction", System.StringComparison.OrdinalIgnoreCase) >= 0)
                return "This call changes the document, and that includes view state. To select, zoom, or temporarily "
                    + "isolate or hide elements, use the show_elements tool instead (no approval needed). For other changes, "
                    + "wrap the call in t = DB.Transaction(doc, 'name'); t.Start(); ...; t.Commit() and use run_modify.";

            if (type != "AttributeError" && type != "TypeError")
                return null;

            var missing = MissingAttribute.Match(message);
            if (missing.Success) {
                var owner = missing.Groups["owner"].Value;
                var member = missing.Groups["member"].Value;
                if (owner.StartsWith("Autodesk.Revit"))
                    return $"'{member}' does not exist in {owner}. Find the right name with lookup_revit_api(name='{member}') before retrying.";
                if (owner == "type") {
                    var named = OwnerOnLine(failingLine, member);
                    return named != null
                        ? $"{named} has no member '{member}'. If {named} is an enum, list its values with lookup_revit_api(name='{named}'); "
                            + $"otherwise check its members with lookup_revit_api(name='{named}.{member}')."
                        : $"No class or enum on the failing line has a member '{member}'. Check the names with lookup_revit_api before retrying.";
                }
                return $"{owner} has no '{member}'. If a collector returned elements of an unexpected class, filter with OfClass(...) "
                    + $"or isinstance(); otherwise check the members with lookup_revit_api(name='{owner}').";
            }

            var calls = CallsOnLine(failingLine);

            var argumentCount = WrongArgumentCount.Match(message);
            if (argumentCount.Success) {
                var member = argumentCount.Groups["member"].Value;
                var target = calls.FirstOrDefault(call => call.EndsWith("." + member)) ?? member;
                return $"Wrong number of arguments for {member}. Check its overloads with lookup_revit_api(name='{target}') before retrying.";
            }

            var argumentType = WrongArgumentType.Match(message);
            if (argumentType.Success) {
                var expected = argumentType.Groups["expected"].Value.Trim();
                var got = argumentType.Groups["got"].Value;
                if (NetCollectionType.IsMatch(expected) && (got == "list" || got == "tuple" || got == "set" || got == "generator")) {
                    var item = ItemType(expected) ?? "ElementId";
                    return $"The Revit API needs a .NET collection here, not a Python {got}. Convert it: "
                        + $"from System.Collections.Generic import List; items = List[DB.{item}](python_items).";
                }
                var wrongType = $"An argument has the wrong type (expected {expected}, got {got}). ";
                return calls.Count > 0
                    ? wrongType + "Check the overloads of the calls on the failing line with lookup_revit_api: "
                        + string.Join(", ", calls.Select(call => $"'{call}'")) + "."
                    : wrongType + "Check the called method's overloads with lookup_revit_api before retrying.";
            }

            return "Check the Revit API names and signatures used on the failing line with lookup_revit_api before retrying.";
        }

        private static string OwnerOnLine(string line, string member) {
            if (line == null)
                return null;
            var match = Regex.Match(line, @"\b(?!(?:DB|UI)\.)(?<owner>[A-Z]\w*)\." + Regex.Escape(member) + @"\b");
            return match.Success ? match.Groups["owner"].Value : null;
        }

        private static string ItemType(string collectionType) {
            var match = Regex.Match(collectionType, @"\[(?<item>\w+)\]");
            return match.Success ? match.Groups["item"].Value : null;
        }

        private static System.Collections.Generic.List<string> CallsOnLine(string line) {
            var calls = new System.Collections.Generic.List<string>();
            if (line == null)
                return calls;
            foreach (var pattern in new[] { StaticCall, ConstructedCall })
                foreach (Match match in pattern.Matches(line)) {
                    var call = match.Groups["type"].Value + "." + match.Groups["member"].Value;
                    if (!calls.Contains(call))
                        calls.Add(call);
                }
            return calls;
        }

        private static string LastSourceLine(string traceback) {
            if (string.IsNullOrEmpty(traceback))
                return null;
            var lines = traceback.Replace("\r\n", "\n").Split('\n');
            for (var i = lines.Length - 1; i > 0; i--)
                if (lines[i - 1].TrimStart().StartsWith("File \"<agent-script>\""))
                    return lines[i].Trim();
            return null;
        }

        private static bool HasChanges(JObject changes) {
            return changes.Value<int>("added_count") + changes.Value<int>("modified_count") + changes.Value<int>("deleted_count") > 0;
        }

        private static void CopyIfNotEmpty(JObject source, JObject target, string key) {
            if (source[key] is JArray array && array.Count > 0)
                target[key] = array;
        }
    }
}
