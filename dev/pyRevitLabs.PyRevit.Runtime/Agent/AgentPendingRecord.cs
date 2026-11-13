using System.IO;
using System.Text;

using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// The provisional <c>response.json</c> of a run that waits for the user's approval.
    /// </summary>
    /// <remarks>
    /// <c>response.json</c> is otherwise written once the run ends, so a Revit that exits while
    /// the approval prompt is up would leave a run folder with no outcome, which a reader can't
    /// tell from a run that never started. The final record replaces this one; one that survives
    /// means the run was interrupted at the prompt and nothing was committed.
    /// </remarks>
    internal static class AgentPendingRecord {
        public const string Status = "pending";
        public const string Decision = "awaiting_approval";

        public static JObject Build(AgentRunRequest request, string runId, string runDir) {
            return new JObject {
                ["run_id"] = runId,
                ["run_dir"] = runDir,
                ["request_id"] = request.RequestId,
                ["mode"] = request.ModeName,
                ["title"] = request.Title,
                ["status"] = Status,
                ["decision"] = Decision,
            };
        }

        /// <summary>
        /// Best effort: a failure to write only leaves the run without the provisional record.
        /// </summary>
        public static void Write(AgentRunRequest request, string runId, string runDir) {
            try {
                File.WriteAllText(
                    Path.Combine(runDir, "response.json"),
                    Build(request, runId, runDir).ToString(Formatting.Indented),
                    new UTF8Encoding(false));
            }
            catch (IOException) {
            }
        }
    }
}
