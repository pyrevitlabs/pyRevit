using System;
using System.Linq;
using System.Reflection;

using pyRevitLabs.Json.Linq;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Compares the commit the runtime binaries were built from with the commit of the clone the
    /// session loads.
    /// </summary>
    /// <remarks>
    /// <c>pyrevitlib/</c> loads live from the clone's working tree while the runtime DLLs only
    /// change on a rebuild, so after a checkout the two can disagree and scripts fail on types
    /// the DLLs lack. The binaries' commit is the source revision the SDK appends to the
    /// assembly's informational version (<c>version+build.sha</c>).
    /// </remarks>
    internal static class AgentBinaryCommit {
        private const int ShortLength = 7;
        private const string RebuildHint =
            "The binaries were built from another commit than the clone; rebuild with 'dotnet run -c Release -- local' in build/.";

        /// <summary>
        /// The short commit in <paramref name="informationalVersion"/>, or null when it carries none.
        /// </summary>
        public static string Parse(string informationalVersion) {
            var plus = informationalVersion?.IndexOf('+') ?? -1;
            if (plus < 0)
                return null;
            var build = informationalVersion.Substring(plus + 1);
            var revision = build.Substring(build.LastIndexOf('.') + 1);
            if (revision.Length < ShortLength || !revision.All(Uri.IsHexDigit))
                return null;
            return revision.Substring(0, ShortLength).ToLowerInvariant();
        }

        /// <summary>
        /// Adds <c>bin_commit</c> to <paramref name="identity"/>, and <c>bin_stale</c> with a hint
        /// when it differs from the clone's commit. Adds nothing when the binaries' commit is
        /// unknown, and no staleness when the clone's is.
        /// </summary>
        public static void Describe(JObject identity, string binaryInformationalVersion, string cloneCommit) {
            var binary = Parse(binaryInformationalVersion);
            if (binary == null)
                return;
            identity["bin_commit"] = binary;
            if (string.IsNullOrEmpty(cloneCommit) || cloneCommit.Length < ShortLength)
                return;
            if (string.Equals(cloneCommit.Substring(0, ShortLength), binary, StringComparison.OrdinalIgnoreCase))
                return;
            identity["bin_stale"] = true;
            identity["bin_hint"] = RebuildHint;
        }

        public static string ReadInformationalVersion(Assembly assembly) {
            return assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion;
        }
    }
}
