using System;
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
    /// means the run was interrupted before its outcome was recorded, so whether it committed is unknown.
    /// Invariant: it names the run the way the final record does, with the same session id and
    /// document title, so a record that survives can still be traced to its session and model.
    /// </remarks>
    internal static class AgentPendingRecord {
        public const string Status = "pending";
        public const string Decision = "awaiting_approval";

        /// <param name="sessionId">The agent session the run belongs to, or null without one.</param>
        /// <param name="document">Title of the document the run works in.</param>
        public static JObject Build(
            AgentRunRequest request, string runId, string runDir, string sessionId = null, string document = null) {
            return new JObject {
                ["run_id"] = runId,
                ["run_dir"] = runDir,
                ["request_id"] = request.RequestId,
                ["mode"] = request.ModeName,
                ["title"] = request.Title,
                ["reason"] = request.Reason,
                ["session_id"] = sessionId,
                ["document"] = document,
                ["status"] = Status,
                ["decision"] = Decision,
            };
        }

        /// <summary>
        /// Best effort: a failure to write only leaves the run without the provisional record.
        /// </summary>
        public static void Write(
            AgentRunRequest request, string runId, string runDir, string sessionId = null, string document = null) {
            try {
                File.WriteAllText(
                    Path.Combine(runDir, "response.json"),
                    Build(request, runId, runDir, sessionId, document).ToString(Formatting.Indented),
                    new UTF8Encoding(false));
            }
            catch (IOException) {
            }
            catch (UnauthorizedAccessException) {
            }
        }
    }
}
