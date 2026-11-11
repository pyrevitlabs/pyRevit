using LibGit2Sharp;
using pyRevitLabs.PyRevit;

namespace pyRevitCLI.Tests;

/// <summary>
///     Verifies that a clone in a git worktree, whose <c>.git</c> is a file pointing at the main repository, reads its own branch (#3949).
/// </summary>
[Trait("Environment", "HostFree")]
[Trait("Level", "Integration")]
public class CloneWorktreeTests : IDisposable {
    private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-worktree-tests-" + Guid.NewGuid());
    private readonly string mainPath;
    private readonly string worktreePath;

    /// <summary>
    ///     Initializes a new instance of the <see cref="CloneWorktreeTests"/> class with a repository on <c>develop</c>
    ///     and a worktree of it on <c>feature</c>, both carrying the tracked <c>.pyrevitargs</c> that names <c>master</c>.
    /// </summary>
    public CloneWorktreeTests() {
        mainPath = Path.Combine(temp, "main");
        worktreePath = Path.Combine(temp, "feature-worktree");
        Directory.CreateDirectory(Path.Combine(mainPath, "pyrevitlib", "pyrevit"));
        File.WriteAllText(Path.Combine(mainPath, "pyrevitlib", "pyrevit", "__init__.py"), string.Empty);
        File.WriteAllText(Path.Combine(mainPath, ".pyrevitargs"), "https://example.invalid/master.zip\nmaster\nbasepublic\n");
        Repository.Init(mainPath);
        using var repo = new Repository(mainPath);
        Commands.Stage(repo, "*");
        var signature = new Signature("test", "test@example.invalid", DateTimeOffset.Now);
        repo.Commit("initial", signature, signature);
        Commands.Checkout(repo, repo.CreateBranch("develop"));
        repo.CreateBranch("feature");
        repo.Worktrees.Add("feature", "feature-worktree", worktreePath, false);
    }

    /// <inheritdoc />
    public void Dispose() {
        foreach (var file in Directory.GetFiles(temp, "*", SearchOption.AllDirectories))
            File.SetAttributes(file, FileAttributes.Normal);
        Directory.Delete(temp, true);
    }

    /// <summary>
    ///     Verifies that the worktree is recognized as a git clone and reports its checked-out branch, not the image branch.
    /// </summary>
    [Fact]
    public void AWorktreeCloneReportsItsOwnBranch() {
        Assert.True(File.Exists(Path.Combine(worktreePath, ".git")));

        var clone = new PyRevitClone(worktreePath);

        Assert.True(clone.IsRepoDeploy);
        Assert.Equal("feature", clone.Branch);
        Assert.Contains("Branch: \"feature\"", clone.ToString());
    }

    /// <summary>
    ///     Verifies that the main checkout keeps reporting its branch.
    /// </summary>
    [Fact]
    public void TheMainCheckoutReportsItsBranch() {
        Assert.Equal("develop", new PyRevitClone(mainPath).Branch);
    }

    /// <summary>
    ///     Verifies that a <c>.git</c> file that points nowhere does not make the folder a repository clone.
    /// </summary>
    [Fact]
    public void AGitFileThatPointsNowhereIsNotARepoDeploy() {
        var broken = Path.Combine(temp, "broken");
        Directory.CreateDirectory(Path.Combine(broken, "pyrevitlib", "pyrevit"));
        File.WriteAllText(Path.Combine(broken, ".git"), "gitdir: " + Path.Combine(temp, "nowhere"));

        Assert.False(PyRevitClone.IsDeployedWithRepo(broken));
    }
}
