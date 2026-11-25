using System;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Builds and validates the name of an agent host's pipe, shared by the in-Revit host and the
    /// <c>pyrevit</c> CLI.
    /// </summary>
    /// <remarks>
    /// The name is <c>pyrevit-agent-&lt;pid&gt;-&lt;nonce&gt;</c>, where the nonce is 32 random hex
    /// characters, so another process can't predict it and create the pipe first. The host
    /// records it in its per-user instance file; the client reads it from there.
    /// Note: a name without a nonce, <c>pyrevit-agent-&lt;pid&gt;</c>, is still accepted so a
    /// client finds a host started before the nonce existed. Drop that form one release later.
    /// </remarks>
    internal static class AgentPipeName {
        private static readonly Regex Pattern = new Regex(@"^pyrevit-agent-[0-9]{1,10}(-[0-9a-f]{32})?\z", RegexOptions.Compiled);

        public static string Create(int processId) {
            var nonce = new byte[16];
            using (var random = RandomNumberGenerator.Create())
                random.GetBytes(nonce);
            return "pyrevit-agent-" + processId + "-" + BitConverter.ToString(nonce).Replace("-", "").ToLowerInvariant();
        }

        public static bool IsValid(string name) {
            return name != null && Pattern.IsMatch(name);
        }
    }
}
