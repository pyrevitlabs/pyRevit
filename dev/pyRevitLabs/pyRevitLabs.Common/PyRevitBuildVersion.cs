using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text.RegularExpressions;

namespace pyRevitLabs.Common {
    /// <summary>
    /// Resolves the version of the pyRevit build that is actually running.
    /// <para>
    /// Every assembly carries the build stamp from <c>dev/Directory.Build.props</c>
    /// (<c>&lt;Version&gt;7.0.0.26273+1554&lt;/Version&gt;</c>) in its
    /// <see cref="AssemblyInformationalVersionAttribute"/>. The clone's
    /// <c>pyrevitlib/pyrevit/version</c> file carries the stamp written by the build that last
    /// touched the checkout, which is a different thing: a clone whose <c>bin/</c> came from a
    /// release image or from CI artifacts reports the version of a source tree it is not
    /// running. Anything the user reads - About, the output window title, <c>pyrevit clones
    /// list</c> - has to answer with the loaded build, otherwise a release check is reading a
    /// string that cannot identify the code under test.
    /// </para>
    /// </summary>
    public static class PyRevitBuildVersion {
        private static readonly Regex CommitHash = new Regex(
            @"^[0-9a-f]{40}$", RegexOptions.Compiled | RegexOptions.IgnoreCase);

        /// <summary>
        /// Reduces an <see cref="AssemblyInformationalVersionAttribute"/> value to the version
        /// string pyRevit reports, i.e. <c>7.0.0.26273+1554</c>.
        /// </summary>
        /// <param name="informationalVersion">Raw informational version, or null.</param>
        /// <returns>Normalized version, or null when there is nothing usable.</returns>
        public static string NormalizeInformationalVersion(string informationalVersion) {
            if (string.IsNullOrWhiteSpace(informationalVersion))
                return null;

            var value = informationalVersion.Trim();

            var buildMetadataAt = value.IndexOf('+');
            if (buildMetadataAt < 0)
                return value;

            var head = value.Substring(0, buildMetadataAt);

            var metadata = value.Substring(buildMetadataAt + 1).Split('.')[0];
            if (metadata.Length == 0 || CommitHash.IsMatch(metadata))
                return head;

            return head + "+" + metadata;
        }

        /// <summary>
        /// Version of the build an already-loaded assembly came from.
        /// </summary>
        /// <param name="assembly">Loaded assembly, typically the pyRevit Runtime.</param>
        /// <returns>Normalized version, or null when the assembly carries no usable stamp.</returns>
        public static string FromAssembly(Assembly assembly) {
            if (assembly == null)
                return null;

            var attr = assembly.GetCustomAttribute<AssemblyInformationalVersionAttribute>();
            return NormalizeInformationalVersion(attr?.InformationalVersion);
        }

        /// <summary>
        /// Version of the build an assembly file on disk came from, without loading it.
        /// </summary>
        /// <param name="assemblyPath">Path to a managed assembly.</param>
        /// <returns>Normalized version, or null when the file is missing or carries no stamp.</returns>
        public static string FromAssemblyFile(string assemblyPath) {
            if (string.IsNullOrEmpty(assemblyPath) || !File.Exists(assemblyPath))
                return null;

            try {
                return NormalizeInformationalVersion(
                    FileVersionInfo.GetVersionInfo(assemblyPath).ProductVersion);
            }
            catch (Exception) {
                return null;
            }
        }
    }
}
