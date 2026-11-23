using System;
using System.IO;
using LibGit2Sharp;
using NUnit.Framework;
using pyRevitLabs.PyRevit;

namespace pyRevitLabs.PyRevit.Integration.Tests {
    /// <summary>
    ///     Verifies that a clone in a git worktree, whose <c>.git</c> is a file pointing at the main repository, reads its own branch (#3949).
    /// </summary>
    [TestFixture]
    [FixtureLifeCycle(LifeCycle.InstancePerTestCase)]
    [Category("HostFree")]
    [Category("Integration")]
    public class CloneWorktreeTests {
        private readonly string temp = Path.Combine(Path.GetTempPath(), "pyRevit-worktree-tests-" + Guid.NewGuid());
        private readonly string mainPath;
        private readonly string worktreePath;

        /// <summary>
        ///     Initializes a new instance of the <see cref="CloneWorktreeTests"/> class with the main and worktree locations.
        /// </summary>
        public CloneWorktreeTests() {
            mainPath = Path.Combine(temp, "main");
            worktreePath = Path.Combine(temp, "feature-worktree");
        }

        /// <summary>
        ///     Creates a repository on <c>develop</c> and a worktree of it on <c>feature</c>, both carrying the tracked
        ///     <c>.pyrevitargs</c> that names <c>master</c>.
        /// </summary>
        [SetUp]
        public void SetUp() {
            Directory.CreateDirectory(Path.Combine(mainPath, "pyrevitlib", "pyrevit"));
            File.WriteAllText(Path.Combine(mainPath, "pyrevitlib", "pyrevit", "__init__.py"), string.Empty);
            File.WriteAllText(Path.Combine(mainPath, ".pyrevitargs"), "https://example.invalid/master.zip\nmaster\nbasepublic\n");
            Repository.Init(mainPath);
            using (var repo = new Repository(mainPath)) {
                Commands.Stage(repo, "*");
                var signature = new Signature("test", "test@example.invalid", DateTimeOffset.Now);
                repo.Commit("initial", signature, signature);
                Commands.Checkout(repo, repo.CreateBranch("develop"));
                repo.CreateBranch("feature");
                repo.Worktrees.Add("feature", "feature-worktree", worktreePath, false);
            }
        }

        /// <summary>
        ///     Deletes the repositories, including read-only git objects.
        /// </summary>
        [TearDown]
        public void TearDown() {
            FixtureDirectory.Delete(temp);
        }

        /// <summary>
        ///     Verifies that the worktree is recognized as a git clone and reports its checked-out branch, not the image branch.
        /// </summary>
        [Test]
        public void AWorktreeCloneReportsItsOwnBranch() {
            Assert.That(File.Exists(Path.Combine(worktreePath, ".git")), Is.True);

            var clone = new PyRevitClone(worktreePath);

            Assert.That(clone.IsRepoDeploy, Is.True);
            Assert.That(clone.Branch, Is.EqualTo("feature"));
            Assert.That(clone.ToString(), Does.Contain("Branch: \"feature\""));
        }

        /// <summary>
        ///     Verifies that the main checkout keeps reporting its branch.
        /// </summary>
        [Test]
        public void TheMainCheckoutReportsItsBranch() {
            Assert.That(new PyRevitClone(mainPath).Branch, Is.EqualTo("develop"));
        }

        /// <summary>
        ///     Verifies that a <c>.git</c> file that points nowhere does not make the folder a repository clone.
        /// </summary>
        [Test]
        public void AGitFileThatPointsNowhereIsNotARepoDeploy() {
            var broken = Path.Combine(temp, "broken");
            Directory.CreateDirectory(Path.Combine(broken, "pyrevitlib", "pyrevit"));
            File.WriteAllText(Path.Combine(broken, ".git"), "gitdir: " + Path.Combine(temp, "nowhere"));

            Assert.That(PyRevitClone.IsDeployedWithRepo(broken), Is.False);
        }
    }
}
