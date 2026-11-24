using System;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using pyRevitLabs.NLog;
using pyRevitLabs.Json.Linq;

namespace pyRevitLabs.PyRevit {

    public class PyRevitRelease : GithubReleaseInfo {
        // Check whether this is a pyRevit release
        public bool IsPyRevitRelease { get { return !tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

        // Check whether this is a CLI release
        public bool IsCLIRelease { get { return tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

        /// <summary>
        /// Whether <paramref name="assetName"/> is the pyRevit installer executable (not the CLI one)
        /// of the requested flavor: the per-user installer, or the all-users admin installer.
        /// </summary>
        public static bool IsInstallerAssetName(string assetName, bool admin) {
            if (!assetName.StartsWith("pyRevit_", StringComparison.OrdinalIgnoreCase)
                    || assetName.StartsWith("pyRevit_CLI_", StringComparison.OrdinalIgnoreCase))
                return false;

            var isAdminInstaller = assetName.EndsWith("_admin_signed.exe", StringComparison.OrdinalIgnoreCase);
            var isUserInstaller = !isAdminInstaller && assetName.EndsWith("_signed.exe", StringComparison.OrdinalIgnoreCase);
            return admin ? isAdminInstaller : isUserInstaller;
        }

        /// <summary>
        /// Download URL of the pyRevit installer asset, or null when the release does not ship one.
        /// </summary>
        public string GetInstallerURL(bool admin = false) =>
            FindAssetDownloadUrl(assetName => IsInstallerAssetName(assetName, admin));

        // Extract archive download url from zipball_url
        public string ArchiveURL {
            get { return GithubAPI.GetTagArchiveUrl(PyRevitLabsConsts.OriginalRepoId, Tag); }
        }
    }
}
