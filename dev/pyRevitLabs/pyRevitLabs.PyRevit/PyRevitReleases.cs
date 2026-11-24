using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text.RegularExpressions;

using pyRevitLabs.Common;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;

namespace pyRevitLabs.PyRevit {
    public static class PyRevitReleases {
        // private logger and data
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static PyRevitRelease GetLatestRelease(bool includePreRelease = false) =>
            FilterPyRevitReleases(GetReleases(), includePreRelease).OrderByDescending(r => r.Version).FirstOrDefault();

        /// <summary>
        /// Keeps pyRevit releases (dropping CLI releases) and, unless <paramref name="includePreRelease"/>
        /// is set, drops pre-releases such as the rolling ci-binaries one.
        /// </summary>
        public static List<PyRevitRelease> FilterPyRevitReleases(IEnumerable<PyRevitRelease> releases, bool includePreRelease) =>
            releases.Where(r => r.IsPyRevitRelease && (includePreRelease || !r.PreRelease)).ToList();

        /// <summary>
        /// Orders releases by version, newest first, and by creation time among equal versions.
        /// </summary>
        /// <remarks>
        /// The creation time alone is not a version order: GitHub dates a release from when it was created, so an old
        /// tag published late sorts among the new ones.
        /// </remarks>
        public static List<PyRevitRelease> SortNewestFirst(IEnumerable<PyRevitRelease> releases) =>
            releases.OrderByDescending(r => r.Version).ThenByDescending(r => r.CreatedTimeStamp, StringComparer.Ordinal).ToList();

        /// <summary>
        /// Every release of the repository, newest version first (see <see cref="SortNewestFirst"/>).
        /// </summary>
        public static List<PyRevitRelease> GetReleases() =>
            SortNewestFirst(GithubAPI.GetReleases<PyRevitRelease>(PyRevitLabsConsts.OriginalRepoId));

        public static List<PyRevitRelease> FindReleases(string searchPattern, bool includePreRelease = false) {
            return FilterPyRevitReleases(GetReleases(), includePreRelease)
                .Where(r => r.Name.Contains(searchPattern) || r.Tag.Contains(searchPattern)).ToList();
        }

        // find latest release version
        public static Version GetLatestPyRevitReleaseVersion() {
            // pick the latest release and return
            // could be null
            return GetReleases().Where(r => r.IsPyRevitRelease).Select(r => r.Version).Max();
        }

        /// <summary>
        /// Version of the newest stable release that ships the CLI installer, or null when GitHub lists none.
        /// </summary>
        /// <remarks>
        /// The CLI installers are assets of the regular pyRevit releases. The separate <c>cli-v</c> releases
        /// ended at 4.8.8 and must not decide whether a newer CLI exists.
        /// </remarks>
        public static Version GetLatestCLIReleaseVersion() => GetLatestRelease()?.Version;

    }
}
