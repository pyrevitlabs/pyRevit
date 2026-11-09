using System;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// A failure reported to the agent with a stable machine-readable <see cref="Code"/>.
    /// </summary>
    public sealed class AgentException : Exception {
        public const string NotRunCode = "revit_busy";

        public AgentException(string code, string message) : base(message) {
            Code = code;
        }

        public string Code { get; }

        /// <summary>
        /// Extra fields for the error's <c>data</c> object, next to <c>type</c>.
        /// </summary>
        public JObject Details { get; } = new JObject();

        /// <summary>
        /// A request the host refused before running any of it because Revit was busy.
        /// </summary>
        /// <remarks>
        /// Invariant: every <c>revit_busy</c> the host raises goes through here. It means the
        /// request was discarded and will never run later, so the caller may send it again.
        /// The message says so and <c>data.outcome</c> is <c>not_run</c>.
        /// </remarks>
        public static AgentException NotRun(string message) {
            var exception = new AgentException(
                NotRunCode,
                message + " The request was not run and has been discarded; it will not run later, "
                + "so it is safe to send again once Revit is idle.");
            exception.Details["outcome"] = "not_run";
            return exception;
        }
    }
}
