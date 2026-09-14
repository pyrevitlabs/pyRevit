using System.IO.Compression;
using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class CloneBinPayloadHelperTests
{
    [TestMethod]
    public void CreateSignedBinZip_wrapsBinDirectory()
    {
        var root = Path.Combine(Path.GetTempPath(), "pyrevit-clone-bin-" + Guid.NewGuid().ToString("N"));
        var binPath = Path.Combine(root, "bin");
        var distPath = Path.Combine(root, "dist");
        Directory.CreateDirectory(Path.Combine(binPath, "netfx"));
        File.WriteAllText(Path.Combine(binPath, "netfx", "marker.txt"), "ok");

        try
        {
            var zipPath = CloneBinPayloadHelper.CreateSignedBinZip(binPath, distPath, "6.5.3.26176+2017");

            Assert.AreEqual(Path.Combine(distPath, "bin-v6.5.3.26176+2017.zip"), zipPath);
            Assert.IsTrue(File.Exists(zipPath));

            using (var archive = ZipFile.OpenRead(zipPath))
            {
                Assert.IsTrue(archive.Entries.Any(entry =>
                    entry.FullName.Replace('\\', '/').EndsWith("bin/netfx/marker.txt", StringComparison.Ordinal)));
            }
        }
        finally
        {
            if (Directory.Exists(root))
            {
                Directory.Delete(root, recursive: true);
            }
        }
    }
}
