using System.Collections.Generic;
using System.IO;
using System.Linq;
using pyRevitLabs.Common;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;
using pyRevitLabs.PyRevit;
using Console = Colorful.Console;

namespace pyRevitCLI
{
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
                matchedRelease = PyRevitReleases.FindReleases(searchPattern, includePreRelease: listPreReleases).FirstOrDefault();
                if (matchedRelease is null)
                    throw new PyRevitException(
                        string.Format("No release matching \"{0}\" were found.", searchPattern)
                        );
            }

            CommonUtils.OpenUrl(matchedRelease.Url);
        }

        internal static void
        DownloadReleaseAsset(GithubReleaseAssetType assetType, string destPath, string searchPattern, bool latest = false, bool listPreReleases = false) {
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
                case GithubReleaseAssetType.Archive: downloadUrl = matchedRelease.ArchiveURL; break;
                case GithubReleaseAssetType.Installer:
                    {
                        var rawInstallerUrl = matchedRelease.InstallerURL;

                        downloadUrl = rawInstallerUrl.Replace(".nupkg", "_signed.exe").Replace("_CLI_", "_").Replace("-cli.", "_").Replace("_admin_signed.exe", "_signed.exe");

                    }
                    break;

                case GithubReleaseAssetType.Unknown: downloadUrl = null; break;
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
