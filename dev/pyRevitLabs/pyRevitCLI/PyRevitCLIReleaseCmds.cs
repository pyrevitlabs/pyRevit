using System;
using System.Collections.Generic;
using System.Linq;
using System.IO;
using System.Text;
using System.Threading.Tasks;
using System.Drawing;
using System.Diagnostics;

using pyRevitLabs.Common;
using pyRevitLabs.CommonCLI;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.TargetApps.Revit;
using pyRevitLabs.PyRevit;
using pyRevitLabs.Language.Properties;

using pyRevitLabs.NLog;
using pyRevitLabs.Json;
using pyRevitLabs.Json.Serialization;

using Console = Colorful.Console;

namespace pyRevitCLI {
    internal static class PyRevitCLIReleaseCmds {
        static Logger logger = LogManager.GetCurrentClassLogger();

        // handle releases
        internal static void
        PrintReleases(string searchPattern, bool latest = false, bool printReleaseNotes = false, bool listPreReleases = false) {
            PyRevitCLIAppCmds.PrintHeader("Releases");
            List<PyRevitRelease> releasesToList = new List<PyRevitRelease>();

            // determine latest release
            if (latest) {
                var latestRelease = PyRevitReleases.GetLatestRelease(includePreRelease: listPreReleases);

                if (latestRelease is null)
                    throw new PyRevitException("Can not determine latest release.");

                releasesToList.Add(latestRelease);
            }
            else {
                if (searchPattern != null)
                    releasesToList = PyRevitReleases.FindReleases(searchPattern, includePreRelease: listPreReleases);
                else
                    releasesToList = PyRevitReleases.GetReleases().Where(r => r.IsPyRevitRelease).ToList();
            }

            foreach (var prelease in releasesToList) {
                Console.WriteLine(prelease);
                if (printReleaseNotes)
                    Console.WriteLine(prelease.ReleaseNotes.Indent(1));
            }

        }

        internal static void
        OpenReleasePage(string searchPattern, bool latest = false, bool listPreReleases = false) {
            PyRevitRelease matchedRelease = null;
            // determine latest release
            if (latest) {
                matchedRelease = PyRevitReleases.GetLatestRelease(includePreRelease: listPreReleases);

                if (matchedRelease is null)
                    throw new PyRevitException("Can not determine latest release.");
            }
            // or find first release matching given pattern
            else if (searchPattern != null) {
                matchedRelease = PyRevitReleases.FindReleases(searchPattern, includePreRelease: listPreReleases).First();
                if (matchedRelease is null)
                    throw new PyRevitException(
                        string.Format("No release matching \"{0}\" were found.", searchPattern)
                        );
            }

            CommonUtils.OpenUrl(matchedRelease.Url);
        }

        internal static void
        DownloadReleaseAsset(PyRevitReleaseAssetType assetType, string destPath, string searchPattern, bool latest = false, bool listPreReleases = false) {
            // get dest path
            if (destPath is null)
                destPath = UserEnv.GetPath(KnownFolder.Downloads);

            PyRevitRelease matchedRelease = null;
            // determine latest release
            if (latest) {
                matchedRelease = PyRevitReleases.GetLatestRelease(includePreRelease: listPreReleases);

                if (matchedRelease is null)
                    throw new PyRevitException("Can not determine latest release.");

            }
            // or find first release matching given pattern
            else {
                if (searchPattern != null)
                    matchedRelease = PyRevitReleases.FindReleases(searchPattern, includePreRelease: listPreReleases).First();

                if (matchedRelease is null)
                    throw new PyRevitException(
                        string.Format("No release matching \"{0}\" were found.", searchPattern)
                        );
            }

            // grab download url
            string downloadUrl = null;
            switch (assetType) {
                case PyRevitReleaseAssetType.Archive: downloadUrl = matchedRelease.ArchiveUrl; break;
                case PyRevitReleaseAssetType.Installer: downloadUrl = matchedRelease.InstallerUrl; break;
                case PyRevitReleaseAssetType.Unknown: downloadUrl = null; break;
            }

            if (downloadUrl != null) {
                logger.Debug("Downloading release package from \"{0}\"", downloadUrl);

                // ensure destpath is to a file
                if (CommonUtils.VerifyPath(destPath))
                    destPath = Path.Combine(destPath, Path.GetFileName(downloadUrl)).NormalizeAsPath();
                logger.Debug("Saving package to \"{0}\"", destPath);

                // download file and report
                CommonUtils.DownloadFile(downloadUrl, destPath);
                Console.WriteLine(
                    string.Format("Downloaded package to \"{0}\"", destPath)
                    );
            }
        }
    }
}
