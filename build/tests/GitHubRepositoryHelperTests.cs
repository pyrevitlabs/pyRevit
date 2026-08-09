using Build.Helpers;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Build.Tests;

[TestClass]
public sealed class GitHubRepositoryHelperTests
{
    [TestMethod]
    public void NormalizeRepositoryName_strips_git_suffix()
    {
        Assert.AreEqual("pyRevit", GitHubRepositoryHelper.NormalizeRepositoryName("pyRevit.git"));
    }

    [TestMethod]
    public void Resolve_prefers_github_repository_environment_variable()
    {
        var previous = Environment.GetEnvironmentVariable("GITHUB_REPOSITORY");
        try
        {
            Environment.SetEnvironmentVariable("GITHUB_REPOSITORY", "pyrevitlabs/pyRevit");

            var (owner, name) = GitHubRepositoryHelper.Resolve();

            Assert.AreEqual("pyrevitlabs", owner);
            Assert.AreEqual("pyRevit", name);
        }
        finally
        {
            Environment.SetEnvironmentVariable("GITHUB_REPOSITORY", previous);
        }
    }
}
