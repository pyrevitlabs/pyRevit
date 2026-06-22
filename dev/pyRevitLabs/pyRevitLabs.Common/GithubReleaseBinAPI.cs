using System;
using System.IO;
using System.Net;

using pyRevitLabs.NLog;

namespace pyRevitLabs.Common {
    public static class GithubReleaseBinAPI {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public const string CiBinariesReleaseTag = "ci-binaries";

        public static string BuildReleaseAssetUrl(string repoId, string assetFileName) {
            return string.Format(
                "https://github.com/{0}/releases/download/{1}/{2}",
                repoId,
                CiBinariesReleaseTag,
                assetFileName);
        }

        public static string BuildShaAssetName(string commitSha) {
            return GithubActionsAPI.UnsignedBinArtifactPrefix + commitSha.Trim() + ".zip";
        }

        public static string BuildBranchLatestAssetName(string branchName) {
            return string.Format(
                "{0}{1}-latest.zip",
                GithubActionsAPI.UnsignedBinArtifactPrefix,
                branchName);
        }

        public static bool TryDownloadReleaseAsset(string repoId, string assetFileName, string destPath) {
            if (!CommonUtils.CheckInternetConnection())
                throw new pyRevitNoInternetConnectionException();

            var url = BuildReleaseAssetUrl(repoId, assetFileName);
            logger.Debug("Trying public release asset \"{0}\"", url);

            try {
                using (var response = CommonUtils.GetHttpResponse(url)) {
                    if (response.StatusCode == HttpStatusCode.NotFound)
                        return false;

                    if (!response.IsSuccessStatusCode) {
                        logger.Debug(
                            "Release asset request failed ({0}) for \"{1}\"",
                            (int)response.StatusCode,
                            assetFileName);
                        return false;
                    }

                    CommonUtils.CopyHttpContentToFile(response.Content, destPath);
                    return CommonUtils.VerifyFile(destPath) && new FileInfo(destPath).Length > 0;
                }
            }
            catch (Exception ex) {
                logger.Debug("Release asset download failed for \"{0}\" | {1}", assetFileName, ex.Message);
                return false;
            }
        }
    }
}
