using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net;
using System.Text;
using System.Threading.Tasks;

using Newtonsoft.Json;

namespace pyRevitLabs.TargetApps.Revit {
    public class PyRevitRelease {
        

        // Github API JSON Properties
        public string tag_name { get; set; }

        // Check whether this is a CLI release
        public bool IsPyRevitRelease { get { return !tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }
        
        // Check whether this is a CLI release
        public bool IsCLIRelease { get { return tag_name.Contains(PyRevitConsts.CLIReleasePrefix); } }

        // Extract version object from tag_name
        public Version GetVersion() {
            // Cleanup tag_name first
            return new Version(
                // replace from larger string to smaller
                tag_name.ToLower()
                        .Replace(PyRevitConsts.CLIReleasePrefix, "")
                        .Replace(PyRevitConsts.ReleasePrefix, "")
                        );
        }

        // Find latest releases
        public static List<PyRevitRelease> GetLatestReleases() {
            // make github api call and get a list of releases
            // https://developer.github.com/v3/repos/releases/
            ServicePointManager.SecurityProtocol = SecurityProtocolType.Tls12;
            HttpWebRequest request = (HttpWebRequest)WebRequest.Create(PyRevitConsts.APIReleasesUrl);
            request.UserAgent = "pyrevit-cli";
            var response = request.GetResponse();

            // extract list of  PyRevitRelease from json
            IList<PyRevitRelease> releases;
            using (var reader = new StreamReader(response.GetResponseStream())) {
                releases = JsonConvert.DeserializeObject<IList<PyRevitRelease>>(reader.ReadToEnd());
            }

            return releases.ToList();
        }

        // find latest release version
        public static Version GetLatestPyRevitReleaseVersion() {
            // pick the latest release and return
            // could be null
            return GetLatestReleases().Where(r => r.IsPyRevitRelease).Select(r => r.GetVersion()).Max();
        }

        // find latest cli release version
        public static Version GetLatestCLIReleaseVersion() {
            // pick the latest release and return
            // could be null
            return GetLatestReleases().Where(r => r.IsCLIRelease).Select(r => r.GetVersion()).Max();
        }
    }

}
