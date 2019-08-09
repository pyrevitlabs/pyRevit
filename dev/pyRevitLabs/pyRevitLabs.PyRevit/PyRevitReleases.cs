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
            releases.AddRange(GetReleasesFromAPI(PyRevit.APIReleasesUrl, out nextendpoint));

            while (nextendpoint != null && nextendpoint != string.Empty) {
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
