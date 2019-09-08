using System;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using pyRevitLabs.NLog;
using pyRevitLabs.Json.Linq;

namespace pyRevitLabs.PyRevit {

    public class PyRevitRelease: GithubReleaseInfo {
        // Check whether this is a pyRevit release
        public bool IsPyRevitRelease { get { return !tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

        // Check whether this is a CLI release
        public bool IsCLIRelease { get { return tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

        // Extract archive download url from zipball_url
        public string ArchiveURL {
            get { return GithubAPI.GetTagArchiveUrl(PyRevitLabsConsts.OriginalRepoId, Tag); }
        }
    }
}
