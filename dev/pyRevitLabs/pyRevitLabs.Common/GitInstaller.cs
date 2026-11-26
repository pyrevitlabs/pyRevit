using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Threading.Tasks;
using LibGit2Sharp;
using pyRevitLabs.Common.Extensions;
using pyRevitLabs.NLog;

namespace pyRevitLabs.Common {
    // git exceptions
    public class pyRevitInvalidGitCloneException : PyRevitException {
        public pyRevitInvalidGitCloneException() { }

        public pyRevitInvalidGitCloneException(string invalidClonePath) { Path = invalidClonePath; }

        public string Path { get; set; }

        public override string Message {
            get {
                return String.Format("Path \"{0}\" is not a valid git clone.", Path);
            }
        }
    }

    public enum UpdateStatus {
        Error,
        Conflicts,
        NonFastForward,
        FastForward,
        UpToDate,
    }

    public abstract class GitInstallerCredentials {
        public abstract bool IsValid();
        public abstract Credentials GetCredentials();
    }

    public class GitInstallerUsernamePasswordCredentials : GitInstallerCredentials {
        public string Username { get; set; }
        public string Password { get; set; }

        public override Credentials GetCredentials() {
            return new UsernamePasswordCredentials { Username = Username, Password = Password };
        }

        public override bool IsValid() {
            return Username != null && Password != null;
        }
    }
    public class GitInstallerAccessTokenCredentials : GitInstallerCredentials {
        public string Username { get; set; } = "pyrevit-cli";
        public string AccessToken { get; set; }

        public override Credentials GetCredentials() {
            return new UsernamePasswordCredentials { Username = Username, Password = AccessToken };
        }

        public override bool IsValid() {
            return Username != null && AccessToken != null;
        }
    }

    public static class GitInstaller {
        private static readonly Logger logger = LogManager.GetCurrentClassLogger();

        // git identity defaults
        private const string commiterName = "eirannejad";
        private const string commiterEmail = "eirannejad@gmail.com";
        private static Identity commiterId = new Identity(commiterName, commiterEmail);


        // public methods
        // clone a repo to given destination
        // @handled @logs
        public static Repository Clone(string repoPath, string branchName, string destPath, GitInstallerCredentials creds, bool checkout = true) {
            // build options and clone
            var cloneOps = new CloneOptions() { Checkout = checkout, BranchName = branchName };

            // add username and password to clone options, if provided by user
            if (creds is GitInstallerCredentials && creds.IsValid())
                cloneOps.FetchOptions.CredentialsProvider = (_url, _usernameFromUrl, _credTypes) => creds.GetCredentials();
            try {
                // attempt at cloning the repo
                logger.Debug("Cloning \"{0}\" branch \"{1}\" to \"{2}\"", repoPath.RedactUrlCredentials(), branchName, destPath);
                Repository.Clone(repoPath, destPath, cloneOps);

                // make repository object and return
                return new Repository(destPath);
            }
            catch (Exception ex) {
                // .Clone method does not return any specific exceptions for authentication failures
                // so let's translate the cryptic exception messages to something meaninful for the user
                if (ex.Message.Contains("401") || ex.Message.Contains("too many redirects or authentication replays"))
                    throw new PyRevitException("Access denied to the repository. Try providing --username and --password");
                // otherwise, wrap and return the original message
                else
                    throw new PyRevitException(ex.Message, ex);
            }
        }

        // checkout a repo branch. Looks up remotes for that branch if the local doesn't exist
        // @handled @logs
        public static void CheckoutBranch(string repoPath, string branchName) {
            try {
                var repo = new Repository(repoPath);

                // get local branch, or make one (and fetch from remote) if doesn't exist
                Branch targetBranch = repo.Branches[branchName];
                if (targetBranch is null) {
                    logger.Debug(string.Format("Branch \"{0}\" does not exist in local clone. " +
                                               "Attemping to checkout from remotes...", branchName));
                    // lookup remotes for the branch otherwise
                    foreach (Remote remote in repo.Network.Remotes) {
                        string remoteBranchPath = remote.Name + "/" + branchName;
                        Branch remoteBranch = repo.Branches[remoteBranchPath];
                        if (remoteBranch != null) {
                            // create a local branch, with remote branch as tracking; update; and checkout
                            Branch localBranch = repo.CreateBranch(branchName, remoteBranch.Tip);
                            repo.Branches.Update(localBranch, b => b.Remote = remote.Name);
                        }
                    }
                }

                // now checkout the branch
                logger.Debug("Checkign out branch \"{0}\"...", branchName);
                Commands.Checkout(repo, branchName);
            }
            catch (Exception ex) {
                throw new PyRevitException(ex.Message, ex);
            }
        }

        // rebase current branch and pull from master
        // @handled @logs
        public static UpdateStatus ForcedUpdate(string repoPath, GitInstallerCredentials creds) {
            logger.Debug("Force updating repo \"{0}\"...", repoPath);
            try {
                var repo = new Repository(repoPath);
                var options = new PullOptions();
                var fetchOpts = new FetchOptions();

                // add username and password to clone options, if provided by user
                if (creds is GitInstallerCredentials && creds.IsValid())
                    fetchOpts.CredentialsProvider = (_url, _usernameFromUrl, _credTypes) => creds.GetCredentials();

                options.FetchOptions = fetchOpts;

                // before updating, let's first
                // forced checkout to overwrite possible local changes
                // Re: https://github.com/pyrevitlabs/pyRevit/issues/229
                var checkoutOptions = new CheckoutOptions();
                checkoutOptions.CheckoutModifiers = CheckoutModifiers.Force;
                Commands.Checkout(repo, repo.Head, checkoutOptions);

                // now let's pull from the tracked remote
                var res = Commands.Pull(repo,
                                        new Signature("GitInstaller",
                                                      commiterEmail,
                                                      new DateTimeOffset(DateTime.Now)),
                                        options);

                // process the results and let user know
                if (res.Status == MergeStatus.FastForward) {
                    logger.Debug("Fast-Forwarded repo \"{0}\"", repoPath);
                    return UpdateStatus.FastForward;
                }
                else if (res.Status == MergeStatus.NonFastForward) {
                    logger.Debug("Non-Fast-Forwarded repo \"{0}\"", repoPath);
                    return UpdateStatus.NonFastForward;
                }
                else if (res.Status == MergeStatus.Conflicts) {
                    logger.Debug("Conflicts on updating clone \"{0}\"", repoPath);
                    return UpdateStatus.Conflicts;
                }

                logger.Debug("Repo \"{0}\" is already up to date.", repoPath);
                return UpdateStatus.UpToDate;
            }
            catch (Exception ex) {
                throw new PyRevitException(ex.Message, ex);
            }
        }

        // rebase current branch to a specific commit by commit hash
        // @handled @logs
        public static void RebaseToCommit(string repoPath, string commitHash) {
            try {
                var repo = new Repository(repoPath);

                // trying to find commit in current branch
                logger.Debug("Searching for commit \"{0}\"...", commitHash);
                foreach (Commit cmt in repo.Commits) {
                    if (cmt.Id.ToString().StartsWith(commitHash)) {
                        logger.Debug("Commit found.");
                        RebaseToCommit(repo, cmt);
                        return;
                    }
                }
            }
            catch (Exception ex) {
                throw new PyRevitException(ex.Message, ex);
            }

            // if it gets here with no errors, it means commit could not be found
            // I'm avoiding throwing an exception inside my own try:catch
            throw new PyRevitException(String.Format("Can not find commit with hash \"{0}\"", commitHash));
        }

        // rebase current branch to a specific tag
        // @handled @logs
        public static void RebaseToTag(string repoPath, string tagName) {
            try {
                var repo = new Repository(repoPath);

                // try to find the tag commit hash and rebase to that commit
                logger.Debug("Searching for tag \"{0}\" target commit...", tagName);
                foreach (Tag tag in repo.Tags) {
                    if (tag.FriendlyName.ToLower() == tagName.ToLower()) {
                        // rebase using commit hash
                        logger.Debug("Tag target commit found.");
                        RebaseToCommit(repoPath, tag.Target.Id.ToString());
                        return;
                    }
                }
            }
            catch (Exception ex) {
                throw new PyRevitException(ex.Message, ex);
            }

            // if it gets here with no errors, it means commit could not be found
            // I'm avoiding throwing an exception inside my own try:catch
            throw new PyRevitException(String.Format("Can not find commit targetted by tag \"{0}\"", tagName));
        }

        // change origin url to the provided url
        // @handled @logs
        public static void SetRemoteUrl(string repoPath, string remoteName, string remoteUrl) {
            try {
                var repo = new Repository(repoPath);

                logger.Debug("Setting origin to \"{0}\"...", remoteUrl);
                repo.Network.Remotes.Update(remoteName, r => r.Url = remoteUrl); ;
            }
            catch (Exception ex) {
                throw new PyRevitException(ex.Message, ex);
            }
        }

        // check to see if a directory is a git repo
        // @handled @logs
        public static bool IsValidRepo(string repoPath) {
            logger.Debug("Verifying repo validity \"{0}\"", repoPath);
            return Repository.IsValid(repoPath);
        }

        // get the checkedout branch from repopath
        // @handled @logs
        public static string GetCheckedoutBranch(string repoPath) {
            if (IsValidRepo(repoPath)) {
                using (var repo = new Repository(repoPath))
                    return repo.Head.FriendlyName;
            }
            logger.Debug("Can not determine head branch for \"{0}\"", repoPath);
            return null;
        }

        // get the checkedout branch from repopath
        // @handled @logs
        public static string GetHeadCommit(string repoPath) {
            string head = null;
            if (IsValidRepo(repoPath)) {
                using (var repo = new Repository(repoPath))
                    head = repo.Head?.Tip?.Id.ToString();
            }
            if (head is null)
                logger.Debug("Can not determine head commit hash for \"{0}\"", repoPath);
            return head;
        }

        /// <summary>
        /// Tells whether the checked-out branch has commits that are not on its tracking branch.
        /// </summary>
        /// <returns>
        /// False when the folder is not a repository or the branch has no usable tracking branch, including
        /// one whose remote ref no longer exists.
        /// </returns>
        public static bool IsLocalAheadOfTrackingBranch(string repoPath) {
            if (!IsValidRepo(repoPath))
                return false;

            using (var repo = new Repository(repoPath)) {
                if (!TryGetTrackedTip(repo, out var trackedTip))
                    return false;

                return repo.ObjectDatabase.CalculateHistoryDivergence(repo.Head.Tip, trackedTip).AheadBy > 0;
            }
        }

        /// <summary>
        /// Tells whether the checked-out branch tracks a remote branch whose ref still exists; a branch tracking
        /// another local branch does not count.
        /// </summary>
        public static bool HasTrackingBranch(string repoPath) {
            if (!IsValidRepo(repoPath))
                return false;

            using (var repo = new Repository(repoPath))
                return TryGetTrackedTip(repo, out _);
        }

        /// <summary>
        /// Tells whether the checked-out branch and its tracking branch point at the same history.
        /// </summary>
        /// <returns>
        /// True when the folder is not a repository or the branch has no usable tracking branch.
        /// </returns>
        public static bool IsSyncedWithTrackingBranch(string repoPath) {
            if (!IsValidRepo(repoPath))
                return true;

            using (var repo = new Repository(repoPath)) {
                if (!TryGetTrackedTip(repo, out var trackedTip))
                    return true;

                var divergence = repo.ObjectDatabase.CalculateHistoryDivergence(repo.Head.Tip, trackedTip);
                return divergence.AheadBy == 0 && divergence.BehindBy == 0;
            }
        }

        /// <summary>
        /// Tells whether HEAD points at a commit instead of a branch, as after a tag or commit checkout.
        /// </summary>
        public static bool IsHeadDetached(string repoPath) {
            if (!IsValidRepo(repoPath))
                return false;

            using (var repo = new Repository(repoPath))
                return repo.Info.IsHeadDetached;
        }

        /// <summary>
        /// Tells whether the checkout of a repository finished: the index exists and no tracked file is missing
        /// from the working tree.
        /// </summary>
        /// <remarks>
        /// Modified, staged, untracked and ignored files do not count as incomplete; only tracked files
        /// absent from disk do. A clone interrupted before its checkout completed has no index.
        /// </remarks>
        public static bool HasCompleteWorkingTree(string repoPath) {
            if (!IsValidRepo(repoPath))
                return false;

            using (var repo = new Repository(repoPath)) {
                if (!File.Exists(Path.Combine(repo.Info.Path, "index")))
                    return false;

                var options = new StatusOptions { IncludeUntracked = false, IncludeIgnored = false };
                return !repo.RetrieveStatus(options).Any(entry => entry.State.HasFlag(FileStatus.DeletedFromWorkdir));
            }
        }

        private static bool TryGetTrackedTip(Repository repo, out Commit trackedTip) {
            var tracked = repo.Head?.TrackedBranch;
            trackedTip = tracked != null && tracked.IsRemote ? tracked.Tip : null;
            return trackedTip != null && repo.Head.Tip != null;
        }

        /// <summary>
        /// Reads the url of a named remote of a git repository.
        /// </summary>
        /// <param name="repoPath">The repository folder.</param>
        /// <param name="remoteName">The remote name, such as <c>origin</c>.</param>
        /// <returns>
        /// The remote url, or null when the folder is not a valid repository or the remote does not exist.
        /// </returns>
        /// <exception cref="PyRevitException">The repository could not be read.</exception>
        public static string GetRemoteUrl(string repoPath, string remoteName) {
            if (IsValidRepo(repoPath)) {
                try {
                    using (var repo = new Repository(repoPath))
                        return repo.Network.Remotes[remoteName]?.Url;
                }
                catch (Exception ex) {
                    logger.Debug("Can not determine remote \"{0}\" url for \"{1}\"", remoteName, repoPath);
                    throw new PyRevitException(ex.Message, ex);
                }
            }
            return null;
        }

        /// <summary>
        /// Tells whether two clone sources point at the same repository.
        /// </summary>
        /// <param name="first">A remote URL, scp-style address or local path, such as a stored remote.</param>
        /// <param name="second">The source to compare with.</param>
        /// <returns>True when both resolve to the same repository; false when either is empty.</returns>
        /// <remarks>
        /// Credentials, scheme, a trailing <c>.git</c>, trailing slashes, backslash use and host case are
        /// ignored. The path case is significant for remote URLs, and a different port counts as a
        /// different remote. Local sources compare as full paths, ignoring case; relative local paths resolve
        /// against the process working directory and <c>file://</c> URLs compare as their local path. Two
        /// scp-style addresses differ when only one path starts with a slash, since that path starts at the
        /// server root instead of the remote user's home. A home-relative scp-style path also differs from an
        /// <c>ssh://</c> URL, whose path is always absolute.
        /// </remarks>
        public static bool AreSameRemote(string first, string second) {
            return RemoteAddressComparer.AreSame(first, second);
        }

        // private methods
        // rebase current branch to a specific commit
        // @handled @logs
        private static void RebaseToCommit(Repository repo, Commit commit) {
            logger.Debug("Rebasing to commit \"{0}\"", commit.Id);
            var tempBranch = repo.CreateBranch("rebasetemp", commit);
            repo.Rebase.Start(repo.Head, repo.Head, tempBranch, commiterId, new RebaseOptions());
            repo.Branches.Remove(tempBranch);
        }

    }
}
