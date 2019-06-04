using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading.Tasks;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitLabs.TargetApps.Revit {
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
        public bool IsPyRevitRelease { get { return !tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

        // Check whether this is a CLI release
        public bool IsCLIRelease { get { return tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

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
            get { return PyRevitConsts.GetTagArchiveUrl(Tag); }
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

        public static PyRevitRelease GetLatestRelease(bool includePreRelease = false) {
            if (includePreRelease)
                return GetReleases().Where(r => r.IsPyRevitRelease)
                                          .OrderByDescending(r => r.Version).ToList().First();
            else
                return GetReleases().Where(r => r.IsPyRevitRelease && !r.PreRelease)
                                          .OrderByDescending(r => r.Version).ToList().First();
        }

        // Find releases
        public static List<PyRevitRelease> GetReleases() {
            string nextendpoint;
            var releases = new List<PyRevitRelease>();
            releases.AddRange(GetReleasesFromAPI(PyRevitConsts.APIReleasesUrl, out nextendpoint));

            while (nextendpoint != null && nextendpoint!= string.Empty) {
                releases.AddRange(GetReleasesFromAPI(nextendpoint, out nextendpoint));
            }

            return releases.OrderByDescending(r => r.CreatedTimeStamp).ToList();
        }

        public static List<PyRevitRelease> FindReleases(string searchPattern, bool includePreRelease = false) {
            return GetReleases().Where(r => r.IsPyRevitRelease && (r.Name.Contains(searchPattern) || r.Tag.Contains(searchPattern))).ToList();
        }

        // find latest release version
        public static Version GetLatestPyRevitReleaseVersion() {
            // pick the latest release and return
            // could be null
            return GetReleases().Where(r => r.IsPyRevitRelease).Select(r => r.Version).Max();
        }

        // find latest cli release version
        public static Version GetLatestCLIReleaseVersion() {
            // pick the latest release and return
            // could be null
            return GetReleases().Where(r => r.IsCLIRelease).Select(r => r.Version).Max();
        }

        // privates
        private static IEnumerable<PyRevitRelease> GetReleasesFromAPI(string endpoint, out string nextendpoint) {
            logger.Debug("Getting releases from {0}", endpoint);

            // make github api call and get a list of releases
            // https://developer.github.com/v3/repos/releases/
            HttpWebRequest request = CommonUtils.GetHttpWebRequest(endpoint);
            var response = request.GetResponse();

            // extract list of  PyRevitRelease from json
            IList<PyRevitRelease> releases;
            using (var reader = new StreamReader(response.GetResponseStream())) {
                releases = JsonConvert.DeserializeObject<IList<PyRevitRelease>>(reader.ReadToEnd());
            }

            var m = Regex.Match(response.Headers["Link"], "\\<(?<next>.+?)\\>;\\srel=\"next\"");
            if (m.Success) {
                nextendpoint = m.Groups["next"].Value;
            }
            else
                nextendpoint = null;

            logger.Debug("Next release list is at {0}", nextendpoint);

            return releases;
        }
    }

}
