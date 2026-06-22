using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class VersionHelperTests
{
    [TestMethod]
    public void ResolveBuildVersion_releaseTagBuild_preservesCommittedVersion()
    {
        const string baseVersion = "6.5.0.26173+1406";

        var resolved = VersionHelper.ResolveBuildVersion(baseVersion, "release", isVersionTagBuild: true);

        Assert.AreEqual(baseVersion, resolved);
    }

    [TestMethod]
    public void ResolveBuildVersion_releaseBranchBuild_rebuildsBuildNumber()
    {
        const string baseVersion = "6.5.0.26173+1406";

        var resolved = VersionHelper.ResolveBuildVersion(baseVersion, "release", isVersionTagBuild: false);

        StringAssert.StartsWith(resolved, "6.5.0.");
        Assert.AreNotEqual(baseVersion, resolved);
        StringAssert.DoesNotMatch(resolved, new System.Text.RegularExpressions.Regex("-wip$"));
    }

    [TestMethod]
    public void ResolveBuildVersion_wipChannel_addsWipSuffix()
    {
        const string baseVersion = "6.5.1";

        var resolved = VersionHelper.ResolveBuildVersion(baseVersion, "wip", isVersionTagBuild: false);

        StringAssert.EndsWith(resolved, PyRevitPaths.WipVersionExtension);
    }

    [TestMethod]
    public void IsVersionTagBuild_detectsTagRefType()
    {
        var originalRefType = Environment.GetEnvironmentVariable("GITHUB_REF_TYPE");
        var originalRef = Environment.GetEnvironmentVariable("GITHUB_REF");
        try
        {
            Environment.SetEnvironmentVariable("GITHUB_REF_TYPE", "tag");
            Environment.SetEnvironmentVariable("GITHUB_REF", "refs/heads/master");

            Assert.IsTrue(VersionHelper.IsVersionTagBuild());
        }
        finally
        {
            Environment.SetEnvironmentVariable("GITHUB_REF_TYPE", originalRefType);
            Environment.SetEnvironmentVariable("GITHUB_REF", originalRef);
        }
    }

    [TestMethod]
    public void IsVersionTagBuild_detectsVersionTagRef()
    {
        var originalRefType = Environment.GetEnvironmentVariable("GITHUB_REF_TYPE");
        var originalRef = Environment.GetEnvironmentVariable("GITHUB_REF");
        try
        {
            Environment.SetEnvironmentVariable("GITHUB_REF_TYPE", null);
            Environment.SetEnvironmentVariable("GITHUB_REF", "refs/tags/v6.5.0.26173+1406");

            Assert.IsTrue(VersionHelper.IsVersionTagBuild());
        }
        finally
        {
            Environment.SetEnvironmentVariable("GITHUB_REF_TYPE", originalRefType);
            Environment.SetEnvironmentVariable("GITHUB_REF", originalRef);
        }
    }

    [TestMethod]
    public void IsVersionTagBuild_returnsFalseForBranchRef()
    {
        var originalRefType = Environment.GetEnvironmentVariable("GITHUB_REF_TYPE");
        var originalRef = Environment.GetEnvironmentVariable("GITHUB_REF");
        try
        {
            Environment.SetEnvironmentVariable("GITHUB_REF_TYPE", "branch");
            Environment.SetEnvironmentVariable("GITHUB_REF", "refs/heads/master");

            Assert.IsFalse(VersionHelper.IsVersionTagBuild());
        }
        finally
        {
            Environment.SetEnvironmentVariable("GITHUB_REF_TYPE", originalRefType);
            Environment.SetEnvironmentVariable("GITHUB_REF", originalRef);
        }
    }
}
