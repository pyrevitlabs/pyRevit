using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text.RegularExpressions;

using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Linq;

namespace pyRevitLabs.Common {
    public enum GithubReleaseAssetType {
        Unknown,
        Archive,
        Installer
    }

    public class GithubReleaseInfo {
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

        // Extract installer download url from assets.browser_download_url
        public string InstallerURL {
            get {
                if (assets != null && assets.Count > 0) {
                    var firstAsset = assets[0];
                    return firstAsset.SelectToken("browser_download_url").Value<string>();
                }
                return string.Empty;
            }
        }
    }

    public class GithubAPI {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public const string APIReleasesURL = @"https://api.github.com/repos/{0}/releases";

        public const string ArchiveFileExtension = ".zip";
        public const string ArchiveInternalBranchPath = @"{0}-{1}";
        public const string APIArchiveURL = @"https://github.com/{0}/archive/{1}" + ArchiveFileExtension;

        public static string AuthToken => Environment.GetEnvironmentVariable("GITHUBTOKEN");

        public static IEnumerable<T> GetReleasesFromAPI<T>(string endpoint, out string nextendpoint) {
            // make github api call and get a list of releases
            // https://developer.github.com/v3/repos/releases/
            HttpWebRequest request = CommonUtils.GetHttpWebRequest(endpoint);
            if (AuthToken is null)
                throw new Exception("Missing authorization token. Set on GITHUBTOKEN env var");
            
            request.Headers.Add(HttpRequestHeader.Authorization, $"token {AuthToken}");
            var response = request.GetResponse();

            // extract list of  PyRevitRelease from json
            IList<T> releases;
            using (var reader = new StreamReader(response.GetResponseStream())) {
                releases = JsonConvert.DeserializeObject<IList<T>>(reader.ReadToEnd());
            }

            var m = Regex.Match(response.Headers["Link"], "\\<(?<next>[^<>]+?)\\>;\\srel=\"next\"");
            if (m.Success)
                nextendpoint = m.Groups["next"].Value;
            else
                nextendpoint = null;

            logger.Debug("Next release list is at {0}", nextendpoint);

            return releases;
        }

        public static List<T> GetReleases<T>(string repoId) {
            string nextendpoint;
            var releases = new List<T>();

            // prepare API endpoint
            var endpoint = GetReleaseEndPoint(repoId);
            logger.Debug("Getting releases from {0}", endpoint);

            // make the first call and collect releases alongside the link to the next batch
            releases.AddRange(GetReleasesFromAPI<T>(endpoint, out nextendpoint));

            // while there is a link to the next batch, continue getting releases and adding to list
            while (nextendpoint != null && nextendpoint != string.Empty) {
                endpoint = nextendpoint;
                releases.AddRange(GetReleasesFromAPI<T>(endpoint, out nextendpoint));
            }

            return releases;
        }

        public static string GetReleaseEndPoint(string repoId) => string.Format(APIReleasesURL, repoId);

        public static string GetBranchArchiveUrl(string repoId, string branchName) => string.Format(APIArchiveURL, repoId, branchName);

        public static string GetTagArchiveUrl(string repoId, string tagName) => string.Format(APIArchiveURL, repoId, tagName);

        public static string GetZipPackageInternalBranchPath(string repoName, string branchName) {
            return string.Format(
                ArchiveInternalBranchPath,
                repoName,
                branchName.Replace("/", "-")
                );
        }

        public static string GetRawUrl(string repoId, string branchName, string filePath) => string.Format(@"https://raw.githubusercontent.com/{0}/{1}/{2}", repoId, branchName, filePath);
    }
}
