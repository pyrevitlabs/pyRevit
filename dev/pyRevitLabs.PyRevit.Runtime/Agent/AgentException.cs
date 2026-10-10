using System;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// A failure reported to the agent with a stable machine-readable <see cref="Code"/>.
    /// </summary>
    public sealed class AgentException : Exception {
        public AgentException(string code, string message) : base(message) {
            Code = code;
        }

        public string Code { get; }
    }
}
