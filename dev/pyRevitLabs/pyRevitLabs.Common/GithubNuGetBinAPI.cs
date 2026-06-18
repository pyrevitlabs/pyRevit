using System;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Net.Http;
using System.Net.Http.Headers;

using pyRevitLabs.NLog;

namespace pyRevitLabs.Common {
    public static class GithubNuGetBinAPI {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public const string PackageId = "PyRevit.UnsignedBin";

        public static string BuildPackageVersion(string fullSha) {
            if (string.IsNullOrWhiteSpace(fullSha))
                throw new PyRevitException("Commit SHA is required to resolve NuGet package version.");

            var normalized = fullSha.Trim();
            var shortSha = normalized.Length > 7 ? normalized.Substring(0, 7) : normalized;
            return string.Format("1.0.0-ci-{0}", shortSha);
        }

        public static string BuildPackageDownloadUrl(string repoId, string packageVersion) {
            var owner = repoId.Split('/')[0];
            var packageFileName = string.Format("{0}.{1}.nupkg", PackageId, packageVersion);
            return string.Format(
                "https://nuget.pkg.github.com/{0}/download/{1}/{2}/{3}",
                owner,
                PackageId.ToLowerInvariant(),
                packageVersion,
                packageFileName);
        }

        public static bool TryDownloadPackageZip(string repoId, string fullSha, string destPath) {
            if (string.IsNullOrWhiteSpace(GithubAPI.AuthToken)) {
                logger.Debug("Skipping NuGet package fallback (GITHUBTOKEN not set).");
                return false;
            }

            if (!CommonUtils.CheckInternetConnection())
                throw new pyRevitNoInternetConnectionException();

            var packageVersion = BuildPackageVersion(fullSha);
            var url = BuildPackageDownloadUrl(repoId, packageVersion);
            var tempNupkg = Path.Combine(
                Path.GetTempPath(),
                string.Format("pyrevit-bin-nupkg-{0}.nupkg", Guid.NewGuid().ToString("N")));

            try {
                logger.Debug("Trying NuGet package \"{0}\" version \"{1}\"", PackageId, packageVersion);

                using (var request = new HttpRequestMessage(HttpMethod.Get, url)) {
                    request.Headers.UserAgent.ParseAdd("pyrevit-cli");
                    request.Headers.Authorization = new AuthenticationHeaderValue("Bearer", GithubAPI.AuthToken);

                    using (var response = CommonUtils.SendHttpRequest(request)) {
                        if (response.StatusCode == HttpStatusCode.NotFound)
                            return false;

                        if (!response.IsSuccessStatusCode) {
                            logger.Debug(
                                "NuGet package request failed ({0}) for \"{1}\"",
                                (int)response.StatusCode,
                                packageVersion);
                            return false;
                        }

                        CommonUtils.CopyHttpContentToFile(response.Content, tempNupkg);
                    }
                }

                ExtractBinZipFromNupkg(tempNupkg, fullSha.Trim(), destPath);
                return true;
            }
            catch (Exception ex) {
                logger.Debug("NuGet package download failed for \"{0}\" | {1}", packageVersion, ex.Message);
                return false;
            }
            finally {
                SafeDelete(tempNupkg);
            }
        }

        private static void ExtractBinZipFromNupkg(string nupkgPath, string fullSha, string destPath) {
            var expectedEntry = string.Format(
                "content/{0}",
                GithubReleaseBinAPI.BuildShaAssetName(fullSha));

            using (var archive = ZipFile.OpenRead(nupkgPath)) {
                var entry = archive.GetEntry(expectedEntry)
                    ?? archive.GetEntry(expectedEntry.Replace('/', '\\'));

                if (entry == null)
                    throw new PyRevitException(
                        string.Format("NuGet package does not contain expected binary zip \"{0}\".", expectedEntry));

                if (CommonUtils.VerifyFile(destPath))
                    File.Delete(destPath);

                entry.ExtractToFile(destPath);
            }
        }

        private static void SafeDelete(string path) {
            try {
                if (CommonUtils.VerifyFile(path))
                    File.Delete(path);
            }
            catch (Exception ex) {
                logger.Debug("Could not delete temp file \"{0}\" | {1}", path, ex.Message);
            }
        }
    }
}
