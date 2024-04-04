using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using LibGit2Sharp;
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
                cloneOps.CredentialsProvider = (_url, _usernameFromUrl, _credTypes) => creds.GetCredentials();

            try
            {
                // attempt at cloning the repo
                logger.Debug("Cloning \"{0}:{1}\" to \"{2}\"", repoPath, branchName, destPath);
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
                // Re: https://github.com/eirannejad/pyRevit/issues/229
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
            if (IsValidRepo(repoPath))
                return new Repository(repoPath).Head.FriendlyName;
            logger.Debug("Can not determine head branch for \"{0}\"", repoPath);
            return null;
        }

        // get the checkedout branch from repopath
        // @handled @logs
        public static string GetHeadCommit(string repoPath) {
            string head = null;
            if (IsValidRepo(repoPath))
                head = new Repository(repoPath).Head?.Tip?.Id.ToString();
            if (head is null)
                logger.Debug("Can not determine head commit hash for \"{0}\"", repoPath);
            return head;
        }

        // get the checkedout branch from repopath
        // @handled @logs
        public static string GetRemoteUrl(string repoPath, string remoteName) {
            if (IsValidRepo(repoPath)) {
                try {
                    return new Repository(repoPath).Network.Remotes[remoteName].Url;
                }
                catch (Exception ex) {
                    logger.Debug("Can not determine remote \"{0}\" url for \"{1}\"", remoteName, repoPath);
                    throw new PyRevitException(ex.Message, ex);
                }
            }
            return null;
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
