using System.IO;

using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI {
    /// <summary>
    /// Implements <c>pyrevit clones delete</c> without console or UI dependencies so it can be tested in isolation.
    /// </summary>
    internal static class PyRevitCLICloneDeletion {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        internal const string ClearConfigsIgnoredWarning =
            "Warning: --clearconfigs only applies together with --all; the user configuration was kept";

        /// <summary>
        /// Deletes every clone, or the named clone after detaching any attachment that points at it.
        /// </summary>
        /// <param name="clearConfigs">
        /// Deletes the whole user config, but only together with <paramref name="allClones"/>. For a single clone the
        /// config is kept and <see cref="ClearConfigsIgnoredWarning"/> is written to <paramref name="error"/>.
        /// </param>
        internal static void Delete(bool allClones, string cloneName, bool clearConfigs, TextWriter error) {
            if (allClones)
                PyRevitClones.DeleteAllClones(clearConfigs: clearConfigs);
            else if (cloneName != null) {
                var clone = PyRevitClones.GetRegisteredClone(cloneName);
                foreach (var attachment in PyRevitAttachments.GetAttachments())
                    if (attachment.Clone.Equals(clone)) {
                        logger.Debug($"Detaching existing attachment: {attachment}");
                        PyRevitAttachments.Detach(attachment.Product.ProductYear, attachment.AllUsers);
                    }

                PyRevitClones.Delete(clone);

                if (clearConfigs)
                    error.WriteLine(ClearConfigsIgnoredWarning);
            }
        }
    }
}
