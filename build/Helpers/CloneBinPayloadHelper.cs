using System.IO.Compression;

namespace Build.Helpers;

public static class CloneBinPayloadHelper
{
    public static string CreateSignedBinZip(string binPath, string destDirectory, string buildVersion)
    {
        if (!Directory.Exists(binPath))
        {
            throw new DirectoryNotFoundException($"Signed bin payload is missing at {binPath}.");
        }

        Directory.CreateDirectory(destDirectory);
        var zipPath = Path.Combine(destDirectory, VersionHelper.GetCloneBinAssetName(buildVersion));
        if (File.Exists(zipPath))
        {
            File.Delete(zipPath);
        }

        ZipFile.CreateFromDirectory(
            binPath,
            zipPath,
            CompressionLevel.Fastest,
            includeBaseDirectory: true);
        return zipPath;
    }
}
