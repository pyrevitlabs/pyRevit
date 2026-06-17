using Build.Helpers;
using Build.Modules;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class RestoreStampedMetadataModuleTests
{
    [TestMethod]
    public void StampedReleaseMetadataFiles_includes_build_version_file()
    {
        CollectionAssert.Contains(
            PyRevitPaths.StampedReleaseMetadataFiles.ToList(),
            PyRevitPaths.VersionFile);
    }
}
