using System;

using pyRevitLabs.Common.Extensions;

using pyRevitLabs.NLog;
using pyRevitLabs.Json.Linq;

namespace pyRevitLabs.PyRevit {
    public enum PyRevitReleaseAssetType {
        Unknown,
        Archive,
        Installer
    }

    public class PyRevitRelease {
        // private logger and data
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public override string ToString() {
            return string.Format("{0} | Tag: {1} | Version: {2} | Url: \"{3}\"",
                                 PreRelease ? Name + " (pre-release)" : Name, Tag, Version, Url);
        }

        // Github API JSON Properties
        public string name { get; set; }
        public string tag_name { get; set; }
        public string html_url { get; set; }
        public bool prerelease { get; set; }
        public string tarball_url { get; set; }
        public string zipball_url { get; set; }
        public string body { get; set; }
        public JArray assets { get; set; }
        public string created_at { get; set; }
        public string published_at { get; set; }

        // Check whether this is a pyRevit release
        public bool IsPyRevitRelease { get { return !tag_name.Contains(PyRevit.CLIReleasePrefix); } }

        // Check whether this is a CLI release
        public bool IsCLIRelease { get { return tag_name.Contains(PyRevit.CLIReleasePrefix); } }

        // Extract version object from tag_name
        public Version Version {
            get {
                // replace from larger string to smaller
                var cleanedVersion = tag_name.ToLower().ExtractVersion();
                logger.Debug("Determined release version as \"{0}\"", cleanedVersion);
                // Cleanup tag_name first
                return cleanedVersion;
                    
            }
        }

        public string Name => name;
        public string Url => html_url;
        public string Tag => tag_name;
        public string ReleaseNotes => body.Trim();
        public bool PreRelease => prerelease;
        public string CreatedTimeStamp => created_at;
        public string PublishedTimeStamp => published_at;

        // Extract archive download url from zipball_url
        public string ArchiveUrl {
            get { return PyRevit.GetTagArchiveUrl(Tag); }
        }

        // Extract installer download url from assets.browser_download_url
        public string InstallerUrl {
            get {
                if (assets != null && assets.Count > 0) {
                    var firstAsset = assets[0];
                    return firstAsset.SelectToken("browser_download_url").Value<string>();
                }
                return string.Empty;
            }
        }
    }
}
