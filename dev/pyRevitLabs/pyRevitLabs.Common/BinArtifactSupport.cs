using System;
using System.Collections.Generic;
using System.IO;

using pyRevitLabs.NLog;

namespace pyRevitLabs.Common {
    public static class BinArtifactSupport {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        public static bool IsSupportedCiBinBranch(string branchName) {
            if (string.IsNullOrWhiteSpace(branchName))
                return false;

            var normalized = branchName.Trim();
            foreach (var supported in PyRevitLabsConsts.SupportedCiBinBranches) {
                if (string.Equals(normalized, supported, StringComparison.OrdinalIgnoreCase))
                    return true;
            }

            return false;
        }

        public static bool IsForkRepo(string repoId) {
            return !string.Equals(
                repoId?.Trim(),
                PyRevitLabsConsts.OriginalRepoId,
                StringComparison.OrdinalIgnoreCase);
        }

        public static IReadOnlyList<string> GetReleaseDownloadRepos(string repoId) {
            var normalized = string.IsNullOrWhiteSpace(repoId)
                ? PyRevitLabsConsts.OriginalRepoId
                : repoId.Trim();

            if (!IsForkRepo(normalized))
                return new[] { normalized };

            return new[] { normalized, PyRevitLabsConsts.OriginalRepoId };
        }

        public static string ResolveBinSourceRoot(string extractRoot) {
            var directBin = Path.Combine(extractRoot, "bin");
            if (CommonUtils.VerifyPath(directBin))
                return directBin;

            if (Directory.GetFiles(extractRoot).Length > 0 || Directory.GetDirectories(extractRoot).Length > 1)
                return extractRoot;

            var subDirs = Directory.GetDirectories(extractRoot);
            if (subDirs.Length == 1) {
                var nestedBin = Path.Combine(subDirs[0], "bin");
                if (CommonUtils.VerifyPath(nestedBin))
                    return nestedBin;
                return subDirs[0];
            }

            return extractRoot;
        }

        public static void SwapBinDirectory(string clonePath, string newBinSource) {
            var binDest = Path.Combine(clonePath, "bin");
            var binNew = Path.Combine(clonePath, "bin.new");
            var binBak = Path.Combine(clonePath, "bin.bak");

            SafeDeleteDirectory(binNew);
            SafeDeleteDirectory(binBak);

            try {
                CommonUtils.CopyDirectory(newBinSource, binNew);

                if (CommonUtils.VerifyPath(binDest))
                    Directory.Move(binDest, binBak);

                Directory.Move(binNew, binDest);
                SafeDeleteDirectory(binBak);
            }
            catch (Exception ex) {
                logger.Debug("Bin swap failed, attempting rollback | {0}", ex.Message);

                if (CommonUtils.VerifyPath(binNew))
                    SafeDeleteDirectory(binNew);

                if (CommonUtils.VerifyPath(binBak) && !CommonUtils.VerifyPath(binDest)) {
                    try {
                        Directory.Move(binBak, binDest);
                    }
                    catch (Exception rollbackEx) {
                        logger.Warn("Could not restore previous bin/ from backup | {0}", rollbackEx.Message);
                    }
                }

                throw;
            }
        }

        private static void SafeDeleteDirectory(string path) {
            try {
                if (CommonUtils.VerifyPath(path))
                    CommonUtils.DeleteDirectory(path, verbose: false);
            }
            catch (Exception ex) {
                logger.Debug("Could not delete directory \"{0}\" | {1}", path, ex.Message);
            }
        }
    }
}
