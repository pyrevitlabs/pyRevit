using System;
using System.IO;

using pyRevitLabs.Common;
using pyRevitLabs.Json.Linq;
using pyRevitLabs.PyRevit;

namespace PyRevitLabs.PyRevit.Runtime.Agent {
    /// <summary>
    /// Which pyRevit clone and engine this Revit session runs, as published in its agent instance
    /// record so clients can tell sessions of the same Revit year apart.
    /// </summary>
    internal static class AgentSessionIdentity {
        private const string UnregisteredClonePrefix = "Unnamed-";

        /// <remarks>
        /// Reads the session's own attachment, which for a session started by <c>pyrevit launch</c> is
        /// its per-launch manifest and not the shared per-year one. Every field is null when the
        /// session has no attachment or the clone can't be read; the record is still written.
        /// </remarks>
        public static JObject Describe(int revitYear) {
            PyRevitAttachment attachment = null;
            try {
                attachment = PyRevitAttachments.GetAttachedCached(revitYear);
            }
            catch (Exception) {
            }

            var clone = attachment?.Clone;
            var engine = attachment?.Engine;
            return new JObject {
                ["attached"] = attachment != null,
                ["clone"] = clone == null ? null : DisplayName(clone),
                ["clone_path"] = clone?.ClonePath,
                ["engine"] = engine == null ? null : Path.GetFileName(engine.Path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar)),
                ["engine_version"] = engine?.Version.ToString(),
                ["commit"] = Read(() => clone?.ShortCommit),
                ["branch"] = Read(() => clone?.Branch),
                ["config_root"] = PyRevitLabsConsts.PyRevitPath,
                ["per_launch"] = attachment?.AttachmentType == PyRevitAttachmentType.PerLaunch,
            };
        }

        /// <summary>
        /// The registered name of a clone, or the name of its folder when it was never registered
        /// and would otherwise show up as a hash.
        /// </summary>
        internal static string DisplayName(PyRevitClone clone) {
            if (!clone.Name.StartsWith(UnregisteredClonePrefix, StringComparison.Ordinal))
                return clone.Name;
            return Path.GetFileName(clone.ClonePath.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
        }

        private static string Read(Func<string> read) {
            try {
                return read();
            }
            catch (Exception) {
                return null;
            }
        }
    }
}
