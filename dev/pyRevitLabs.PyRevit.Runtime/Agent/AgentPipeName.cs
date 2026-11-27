using System;
using System.Security.Cryptography;
using System.Text.RegularExpressions;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Builds and validates the name of an agent host's pipe, shared by the in-Revit host and the
    /// <c>pyrevit</c> CLI.
    /// </summary>
    /// <remarks>
    /// The name is <c>pyrevit-agent-&lt;pid&gt;-&lt;nonce&gt;</c>, where the nonce is
    /// <see cref="NonceBytes"/> random bytes in lowercase hex, so another process can't predict it
    /// and create the pipe first. The host records it in its per-user instance file; the client
    /// reads it from there.
    /// Note: a host started before the nonce existed keeps the predictable name
    /// <c>pyrevit-agent-&lt;pid&gt;</c>; <see cref="IsValid"/> still accepts it for one release,
    /// and the client's owner check and the pipe's access list are what cover it. Removing
    /// <c>LegacyPattern</c> drops that form.
    /// </remarks>
    internal static class AgentPipeName {
        private const string Prefix = "pyrevit-agent-";
        private const int NonceBytes = 16;
        private const string ProcessIdDigits = "[0-9]{1,10}";

        private static readonly Regex CurrentPattern = new Regex(
            "^" + Prefix + ProcessIdDigits + "-[0-9a-f]{" + NonceBytes * 2 + @"}\z", RegexOptions.Compiled);

        private static readonly Regex LegacyPattern = new Regex(
            "^" + Prefix + ProcessIdDigits + @"\z", RegexOptions.Compiled);

        /// <summary>
        /// A new pipe name for a host process, with a fresh random nonce.
        /// </summary>
        public static string Create(int processId) {
            var nonce = new byte[NonceBytes];
            using (var random = RandomNumberGenerator.Create())
                random.GetBytes(nonce);
            return Prefix + processId + "-" + BitConverter.ToString(nonce).Replace("-", "").ToLowerInvariant();
        }

        /// <summary>
        /// Whether <paramref name="name"/> has the form a host registers: the current form or the
        /// legacy form without a nonce. Anything else, including a trailing newline, is refused.
        /// </summary>
        public static bool IsValid(string name) {
            return name != null && (CurrentPattern.IsMatch(name) || LegacyPattern.IsMatch(name));
        }
    }
}
